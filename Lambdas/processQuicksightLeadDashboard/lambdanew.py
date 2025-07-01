import os
import json
import boto3
import io
import csv
from botocore.client import Config
import time
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
session = boto3.session.Session()
region = session.region_name
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)

secret_name = os.environ['SecretId']
secret_json = json.loads(client_secretsmanager.get_secret_value(SecretId=secret_name)['SecretString'])
secret_arn = client_secretsmanager.get_secret_value(SecretId=secret_name)['ARN']
cluster_id = secret_json['dbClusterIdentifier']
database_name = secret_json['dbName']


def lambda_handler(event, context):
    try:
        run_lead_dashboard_refresh()
        return {'statusCode': 200, 'body': json.dumps('Lead dashboard updated successfully!')}
    except Exception as e:
        logger.error(str(e))
        return {'statusCode': 500, 'body': json.dumps(f"Error: {str(e)}")}


def execute_redshift_query(query_str, return_statement_id=False):
    try:
        response = client_redshift.execute_statement(
            Database=database_name,
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        statement_id = response['Id']
        logger.info(f"Query submitted. Statement ID: {statement_id}")

        while True:
            query_status = client_redshift.describe_statement(Id=statement_id)
            status = query_status['Status']
            if status in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            logger.info(f"Waiting for query to complete... Current status: {status}")
            time.sleep(2)

        if status == 'FINISHED':
            logger.info("Query executed successfully.")
            return (query_status, statement_id) if return_statement_id else query_status
        else:
            raise Exception(f"Query failed. Status: {status}, Error: {query_status.get('Error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise


def stream_query_results_to_s3(statement_id):
    bucket = os.environ['bucket_name']
    s3_key = f"dashboard/lead/{datetime.utcnow().strftime('%Y-%m-%d')}.csv"

    csv_buffer = io.StringIO()
    writer = None
    next_token = None

    while True:
        result = client_redshift.get_statement_result(Id=statement_id, NextToken=next_token) if next_token else client_redshift.get_statement_result(Id=statement_id)

        if writer is None:
            writer = csv.writer(csv_buffer)
            writer.writerow([col['name'] for col in result['ColumnMetadata']])

        for row in result['Records']:
            writer.writerow([list(col.values())[0] if col else '' for col in row])

        next_token = result.get('NextToken')
        if not next_token:
            break

    s3_client.put_object(Bucket=bucket, Key=s3_key, Body=csv_buffer.getvalue())
    logger.info(f"Streamed CSV to s3://{bucket}/{s3_key}")
    return s3_key


def copy_to_redshift_append(table_name, s3_key):
    bucket = os.environ['bucket_name']
    aws_credentials = json.loads(client_secretsmanager.get_secret_value(SecretId=os.environ['credentials_secret_name'])['SecretString'])
    aws_access_key = aws_credentials['AWS_ACCESS_KEY_ID']
    aws_secret_access_key = aws_credentials['AWS_SECRET_ACCESS_KEY']

    copy_query = f"""
        COPY {table_name} (
            lead_summary_id, lead_id, call_id, timestamp, lead_name, status, lead_score_by_broker,
            total_contact_attempts, lead_affiliate_level_category, audio_call_type, audio_call_type_reason,
            lead_type, lead_type_reason, lead_intrinsic_avg, concern_type, concern_type_reason, dollar_amount,
            account_type, lead_qualification, lead_qualification_reason, summary, created_datetime,
            velocify_uuid, source, lead_details_id, details_timestamp, duration, durationinsecs,
            criteria, score, reason, call_type, outcome, broker_name, broker_id, role
        )
        FROM 's3://{bucket}/{s3_key}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1;
    """
    execute_redshift_query(copy_query)


def run_lead_dashboard_refresh():
    max_date_query = "SELECT MAX(created_datetime) FROM lead_dashboard;"
    query_status, statement_id = execute_redshift_query(max_date_query, return_statement_id=True)

    result = client_redshift.get_statement_result(Id=statement_id)
    latest_timestamp = result['Records'][0][0]['stringValue'] if result['Records'] and result['Records'][0][0] else '1970-01-01 00:00:00'
    logger.info(f"Latest timestamp in lead_dashboard: {latest_timestamp}")

    main_query = f"""
        WITH lead_details_union AS (
            SELECT ld.lead_id, ld.lead_details_id, ld.lead_name, ld.call_id, ld.timestamp AS details_timestamp,
                   ld.duration, ld.durationInSecs, ld.criteria, ld.score, ld.reason, ld.call_type,
                   ld.outcome, ld.broker_name, ld.broker_id, ld.role
            FROM public.lead_details ld
        )
        SELECT ls.lead_summary_id, ls.lead_id, ls.call_id, ls.timestamp, ls.lead_name, ls.status,
               ls.lead_score_by_broker, ls.total_contact_attempts, ls.lead_affiliate_level_category,
               ls.audio_call_type, ls.audio_call_type_reason, ls.lead_type, ls.lead_type_reason,
               ls.lead_intrinsic_avg, ls.concern_type, ls.concern_type_reason, ls.dollar_amount,
               ls.account_type, ls.lead_qualification, ls.lead_qualification_reason, ls.summary,
               ls.created_datetime, ls.velocify_uuid, ls.source, ld.lead_details_id, ld.details_timestamp,
               ld.duration, ld.durationInSecs, ld.criteria, ld.score, ld.reason, ld.call_type,
               ld.outcome, ld.broker_name, ld.broker_id, ld.role
        FROM public.lead_summary ls
        LEFT JOIN lead_details_union ld ON ls.lead_id = ld.lead_id
        WHERE ls.created_datetime > '{latest_timestamp}'
        ORDER BY ls.lead_id, ls.created_datetime;
    """

    _, statement_id = execute_redshift_query(main_query, return_statement_id=True)
    logger.info("Main query finished. Streaming results to S3...")

    s3_key = stream_query_results_to_s3(statement_id)
    copy_to_redshift_append("lead_dashboard", s3_key)

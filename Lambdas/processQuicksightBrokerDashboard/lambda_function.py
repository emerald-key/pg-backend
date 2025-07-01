import os
import json
import boto3
import io
import csv
from botocore.client import Config
import time
import logging
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
session = boto3.session.Session()
region = session.region_name
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)

# Load secrets
secret_name = os.environ['SecretId']
secret_json = json.loads(client_secretsmanager.get_secret_value(SecretId=secret_name)['SecretString'])
secret_arn = client_secretsmanager.get_secret_value(SecretId=secret_name)['ARN']
cluster_id = secret_json['dbClusterIdentifier']
database_name = secret_json['dbName']

def lambda_handler(event, context):
    # return
    try:
        run_dashboard_refresh()
        return {'statusCode': 200, 'body': json.dumps('Broker dashboard updated successfully!')}
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
        logger.info(f"Query submitted successfully. Statement ID: {statement_id}")

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
            raise Exception(f"Query execution failed. Status: {status}, Error: {query_status.get('Error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise

def stream_query_results_to_s3_old(statement_id):
    bucket = os.environ['bucket_name']
    s3_key = f"dashboard/broker/{datetime.utcnow().strftime('%Y-%m-%d')}.csv"

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

def stream_query_results_to_s3(statement_id):
    bucket = os.environ['bucket_name']
    s3_key = f"dashboard/broker/{datetime.utcnow().strftime('%Y-%m-%d')}.csv"

    csv_buffer = io.StringIO()
    writer = None
    next_token = None

    while True:
        result = client_redshift.get_statement_result(Id=statement_id, NextToken=next_token) if next_token else client_redshift.get_statement_result(Id=statement_id)

        if writer is None:
            writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)
            writer.writerow([col['name'] for col in result['ColumnMetadata']])

        for row in result['Records']:
            row_data = []
            for col in row:
                val = list(col.values())[0] if col else None

                # Handle None (NULL) values
                if val is None:
                    row_data.append('')
                # Handle Redshift returning `True` for NULLs sometimes
                elif isinstance(val, bool) and val is True:
                    row_data.append('')
                else:
                    row_data.append(val)

            writer.writerow(row_data)

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
            broker_summary_id, call_id, lead_id, timestamp, broker_id, broker_name,
            role, duration, broker_talktime, customer_talktime, positives,
            opportunities, broker_overarching_summary, created_datetime,
            velocify_uuid, type, criteria, score, reason, call_type, outcome
        )
        FROM 's3://{bucket}/{s3_key}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1;
    """
    execute_redshift_query(copy_query)


def run_dashboard_refresh():
    max_date_query = "SELECT MAX(created_datetime) FROM broker_dashboard;"
    query_status, statement_id = execute_redshift_query(max_date_query, return_statement_id=True)

    result = client_redshift.get_statement_result(Id=statement_id)
    latest_timestamp = result['Records'][0][0]['stringValue'] if result['Records'] and result['Records'][0][0] else '1970-01-01 00:00:00'
    logger.info(f"Latest timestamp in dashboard: {latest_timestamp}")
    main_query = f"""
        WITH broker_details AS (
            SELECT bi.call_id, bi.lead_id, bi.broker_id, bi.broker_name, bi.role,
                bi.timestamp, 'intrinsics' AS type, bi.criteria, bi.score,
                bi.reason, bi.call_type, bi.outcome
            FROM public.broker_intrinsics bi
            UNION ALL
            SELECT ba.call_id, ba.lead_id, ba.broker_id, ba.broker_name, ba.role,
                ba.timestamp, 'adherence' AS type, ba.criteria, ba.score,
                ba.reason, ba.call_type, ba.outcome
            FROM public.broker_adherence ba
        )
        SELECT bs.broker_summary_id, bs.call_id, bs.lead_id, bs.timestamp, bs.broker_id,
            bs.broker_name, bs.role, bs.duration, bs.broker_talktime, bs.customer_talktime,
            bs.positives, bs.opportunities, bs.broker_overarching_summary, bs.created_datetime,
            bs.velocify_uuid, bd.type, bd.criteria, bd.score, bd.reason, bd.call_type, bd.outcome
        FROM public.broker_summary bs
        JOIN broker_details bd ON bs.call_id = bd.call_id AND TRIM(bs.broker_id) = TRIM(bd.broker_id)
        WHERE bs.created_datetime > '{latest_timestamp}'
        ORDER BY bs.call_id, bd.type;
    """

    _, statement_id = execute_redshift_query(main_query, return_statement_id=True)
    logger.info("Main query finished. Streaming results to S3...")

    s3_key = stream_query_results_to_s3(statement_id)
    copy_to_redshift_append("broker_dashboard", s3_key)

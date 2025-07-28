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
ses_client = boto3.client('ses')
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
        err_subject = "Error Refreshing Lead Dashboard"
        err_body = f"""
        Error : {str(e)}
        """
        send_email(err_subject, err_body)
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
    s3_key = f"dashboard/lead/{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
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
    before_count = get_table_row_count()
    logger.info(f"Row count before insert: {before_count}")
    copy_query = f"""
        COPY {table_name} (
            lead_summary_id, lead_id, call_id, timestamp, lead_name, status, lead_score_by_broker,
            total_contact_attempts, lead_affiliate_level_category, audio_call_type, audio_call_type_reason,
            lead_type, lead_type_reason, lead_intrinsic_avg, concern_type, concern_type_reason, dollar_amount,
            account_type, lead_qualification, lead_qualification_reason, summary, created_datetime,
            velocify_uuid, source, lead_details_id, details_timestamp, duration, durationinsecs,
            criteria, score, reason, call_type, outcome, broker_name, broker_id, role, actual_dollar_amount
        )
        FROM 's3://{bucket}/{s3_key}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1 BLANKSASNULL EMPTYASNULL;
    """
    execute_redshift_query(copy_query)
    after_count = get_table_row_count()
    logger.info(f"Row count after insert: {after_count}")
    # Calculate inserted rows
    inserted_rows = after_count - before_count
    logger.info(f"Rows inserted into public.call: {inserted_rows}")
    return inserted_rows

def get_table_row_count():
    try:
        # Execute the query
        query = "SELECT COUNT(*) FROM public.lead_dashboard;"
        response = client_redshift.execute_statement(
            Database=database_name,
            SecretArn=secret_arn,
            Sql=query,
            ClusterIdentifier=cluster_id
        )
        statement_id = response['Id']
        
        # Wait for the query to complete
        while True:
            status_response = client_redshift.describe_statement(Id=statement_id)
            if status_response['Status'] in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            logger.info(f"Waiting for row count query to complete... Current status: {status_response['Status']}")
            time.sleep(1)

        if status_response['Status'] == 'FINISHED':
            # Fetch the result
            result_response = client_redshift.get_statement_result(Id=statement_id)
            records = result_response['Records']
            # Extract the row count from the response
            row_count = int(records[0][0]['longValue'])
            logger.info(f"Row count: {row_count}")
            return row_count
        else:
            raise Exception(f"Query failed with status: {status_response['Status']}")

    except Exception as e:
        logger.info(f"Error getting table row count: {e}")
        raise

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
               ls.created_datetime, ls.velocify_uuid, ls.source,ld.lead_details_id, ld.details_timestamp,
               ld.duration, ld.durationInSecs, ld.criteria, ld.score, ld.reason, ld.call_type,
               ld.outcome, ld.broker_name, ld.broker_id, ld.role,ls.actual_dollar_amount
        FROM public.lead_summary ls
        LEFT JOIN lead_details_union ld ON ls.lead_id = ld.lead_id
        WHERE ls.created_datetime > '{latest_timestamp}'
        ORDER BY ls.lead_id, ls.created_datetime;
    """

    _, statement_id = execute_redshift_query(main_query, return_statement_id=True)
    logger.info("Main query finished. Streaming results to S3...")

    s3_key = stream_query_results_to_s3(statement_id)
    copied_rows = copy_to_redshift_append("lead_dashboard", s3_key)
    logger.info(f"Copy to Redshift finished: {copied_rows}")
    # Step 5: Count rows in the CSV file (excluding header)
    response = s3_client.get_object(Bucket=os.environ['bucket_name'], Key=s3_key)
    csv_content = response['Body'].read().decode('utf-8')
    csv_buffer = io.StringIO(csv_content)
    reader = csv.reader(csv_buffer)
    csv_row_count = -1  # Start with -1 to exclude header
    for _ in reader:
        csv_row_count += 1
    logger.info(f"CSV row count: {csv_row_count}")
    # if(copied_rows < csv_row_count):
        # Step 6: Send SES email
    subject = "Lead Dashboard Logs : Redshift Data Load Completed"
    body = f"""
    Bucket Name: {os.environ['bucket_name']}
    CSV File Loaded: {s3_key}
    Total Rows in CSV: {csv_row_count}
    Rows Inserted to Redshift: {copied_rows}
    """
    send_email(subject, body)

def send_email(subject, body):
    try:
        recipient_emails_env = os.environ.get('SES_RECIPIENT_EMAILS', '')
        # Split the emails into a list
        recepient_emails = [email.strip() for email in recipient_emails_env.split(',') if email.strip()]
        print(f"recepient_emails:{recepient_emails}")
        ses_client.send_email(
            Source=os.environ['SES_SOURCE_EMAIL'],
            Destination={'ToAddresses': recepient_emails},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.info(f"Error sending email: {e}")
        raise

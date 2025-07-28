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
ses_client = boto3.client('ses')
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
        err_subject = "Error Refreshing Broker Dashboard"
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

def stream_query_results_to_s3(statement_id):
    bucket = os.environ['bucket_name']
    s3_key = f"dashboard/broker/{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

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
            broker_summary_id, call_id, lead_id, timestamp, broker_id, broker_name,
            role, duration, broker_talktime, customer_talktime, positives,
            opportunities, broker_overarching_summary, created_datetime,
            velocify_uuid, type, criteria, score, reason, call_type, outcome
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
        query = "SELECT COUNT(*) FROM public.broker_dashboard;"
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
    logger.info(f"Streamed CSV to s3://{os.environ['bucket_name']}/{s3_key}")
    copied_rows = copy_to_redshift_append("broker_dashboard", s3_key)
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
    subject = "Broker Dashboard Logs : Redshift Data Load Completed"
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


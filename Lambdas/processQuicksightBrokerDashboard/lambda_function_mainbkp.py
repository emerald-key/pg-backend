import os
import json
import boto3
import io
import csv
from botocore.client import Config
import time
import logging
import uuid
from datetime import datetime

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO) 

# Initialize S3 client and Redshift client
s3_client = boto3.client('s3')
ses_client = boto3.client('ses')
session = boto3.session.Session()
region = session.region_name

# Secrets Manager client
secret_name = os.environ['SecretId']
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
get_secret_value_response = client_secretsmanager.get_secret_value(SecretId=secret_name)
secret_arn = get_secret_value_response['ARN']
secret_json = json.loads(get_secret_value_response['SecretString'])
cluster_id = secret_json['dbClusterIdentifier']
database_name = secret_json['dbName']

# Redshift client
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)

def lambda_handler(event, context):
    try:
        run_dashboard_refresh()
        return {
            'statusCode': 200,
            'body': json.dumps('Broker dashboard updated successfully!')
        }
    except Exception as e:
        logger.error(str(e))
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

def fetch_query_results(statement_id):
    """
    Fetch results from an executed Redshift Data API statement with pagination.
    """
    column_names = []
    all_data = []
    next_token = None

    while True:
        if next_token:
            result = client_redshift.get_statement_result(Id=statement_id, NextToken=next_token)
        else:
            result = client_redshift.get_statement_result(Id=statement_id)

        if not column_names:
            column_names = [col['name'] for col in result['ColumnMetadata']]

        for row in result['Records']:
            row_data = []
            for col in row:
                val = list(col.values())[0] if col else None
                if isinstance(val, bool) and val is True:
                    row_data.append('')
                elif val is None:
                    row_data.append('')
                else:
                    row_data.append(val)
            all_data.append(row_data)

        next_token = result.get('NextToken')
        if not next_token:
            break

    return column_names, all_data



def upload_to_s3_as_csv(column_names, data):
    """
    Upload the query results to S3 as a CSV.
    """
    bucket = os.environ['bucket_name']
    current_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Construct the S3 key dynamically
    key = f"dashboard/broker/{current_date}.csv"    
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(column_names)
    writer.writerows(data)

    s3_client.put_object(Bucket=bucket, Key=key, Body=csv_buffer.getvalue())
    logger.info(f"Uploaded CSV to s3://{bucket}/{key}")
    return key

def truncate_and_copy_to_redshift(table_name, s3_key):
    """
    Truncate the target table and copy new data from S3.
    """
    bucket = os.environ['bucket_name']
    full_s3_path = f"s3://{bucket}/{s3_key}"
    aws_credentials_secret_name = os.environ['credentials_secret_name']
    credentials_response = client_secretsmanager.get_secret_value(SecretId=aws_credentials_secret_name)
    aws_credentials = json.loads(credentials_response['SecretString'])
    aws_access_key = aws_credentials['AWS_ACCESS_KEY_ID']
    aws_secret_access_key = aws_credentials['AWS_SECRET_ACCESS_KEY']
    # copy_query = f"""
    #     BEGIN;
    #     TRUNCATE TABLE {table_name};
    #     COPY {table_name}
    #     FROM '{full_s3_path}'
    #     CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
    #     CSV IGNOREHEADER 1;
    #     COMMIT;
    # """
    copy_query = f"""
        BEGIN;
        TRUNCATE TABLE {table_name};
        COPY {table_name} (
            broker_summary_id,
            call_id,
            lead_id,
            timestamp,
            broker_id,
            broker_name,
            role,
            duration,
            broker_talktime,
            customer_talktime,
            positives,
            opportunities,
            broker_overarching_summary,
            created_datetime,
            velocify_uuid,
            type,
            criteria,
            score,
            reason,
            call_type,
            outcome
            
        )
        FROM '{full_s3_path}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1;
        COMMIT;
    """

    execute_redshift_query(copy_query)


def execute_redshift_query(query_str):
    # print(f"{query_str}")
    """
    Execute a query in the Redshift cluster and wait for its completion.
    """
    try:
        # Execute the query
        response = client_redshift.execute_statement(
            Database=database_name,
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        statement_id = response['Id']
        logger.info(f"Query submitted successfully. Statement ID: {statement_id}")

        # Wait for the query to complete
        while True:
            query_status = client_redshift.describe_statement(Id=statement_id)
            status = query_status['Status']
            if status in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            logger.info(f"Waiting for query to complete... Current status: {status}")
        
        if status == 'FINISHED':
            logger.info("Query executed successfully.")
            return query_status
        else:
            raise Exception(f"Query execution failed. Status: {status}, Error: {query_status.get('Error', 'Unknown error')}")

    except Exception as e:
        logger.info(f"Error executing query: {str(e)}")
        raise

def run_dashboard_refresh():
    query = """
        WITH broker_details AS (
        SELECT
            bi.call_id,
            bi.lead_id,
            bi.broker_id,
            bi.broker_name,
            bi.role,
            bi.timestamp,
            'intrinsics' AS type,
            bi.criteria,
            bi.score,
            bi.reason,
            bi.call_type,
            bi.outcome
        FROM public.broker_intrinsics bi

        UNION ALL

        SELECT
            ba.call_id,
            ba.lead_id,
            ba.broker_id,
            ba.broker_name,
            ba.role,
            ba.timestamp,
            'adherence' AS type,
            ba.criteria,
            ba.score,
            ba.reason,
            ba.call_type,
            ba.outcome
        FROM public.broker_adherence ba
    )

    SELECT
        bs.broker_summary_id,
        bs.call_id,
        bs.lead_id,
        bs.timestamp,
        bs.broker_id,
        bs.broker_name,
        bs.role,
        bs.duration,
        bs.broker_talktime,
        bs.customer_talktime,
        bs.positives,
        bs.opportunities,
        bs.broker_overarching_summary,
        bs.created_datetime,
        bs.velocify_uuid,
        bd.type,
        bd.criteria,
        bd.score,
        bd.reason,
        bd.call_type,
        bd.outcome
    FROM public.broker_summary bs
    JOIN broker_details bd 
        ON bs.call_id = bd.call_id
        AND TRIM(bs.broker_id) = TRIM(bd.broker_id)
    ORDER BY bs.call_id, bd.type;


    """

    
    response = client_redshift.execute_statement(
        Database=database_name,
        SecretArn=secret_arn,
        Sql=query,
        ClusterIdentifier=cluster_id
    )
    statement_id = response['Id']
    logger.info(f"Query started with ID: {statement_id}")

    # Wait for the query to finish
    while True:
        status_response = client_redshift.describe_statement(Id=statement_id)
        status = status_response['Status']
        if status in ['FINISHED', 'FAILED', 'ABORTED']:
            break
        time.sleep(2)

    if status != 'FINISHED':
        raise Exception(f"Query failed: {status_response.get('Error', 'Unknown')}")

    logger.info("Query finished. Fetching results...")
    columns, rows = fetch_query_results(statement_id)
    s3_key = upload_to_s3_as_csv(columns, rows)
    truncate_and_copy_to_redshift("broker_dashboard", s3_key)
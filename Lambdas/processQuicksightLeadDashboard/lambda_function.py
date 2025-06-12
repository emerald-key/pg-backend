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
            'body': json.dumps('Lead dashboard updated successfully!')
        }
    except Exception as e:
        logger.error(str(e))
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

def sanitize_value(val):
    """Sanitize the value for CSV output."""
    if isinstance(val, str):
        # Remove problematic characters or escape them
        val = val.replace('"', '""')  # Escape double quotes
        val = val.replace('{', '')      # Remove curly braces if needed
        val = val.replace('}', '')      # Remove curly braces if needed
    return val

def fetch_query_results_old(statement_id):
    """
    Fetch results from an executed Redshift Data API statement.
    Convert any NULL (NoneType) or unexpected boolean values to proper string values for CSV.
    """
    result = client_redshift.get_statement_result(Id=statement_id)
    column_names = [col['name'] for col in result['ColumnMetadata']]
    rows = result['Records']

    data = []
    for row in rows:
        row_data = []
        for col in row:
            val = list(col.values())[0] if col else None

            # Convert boolean True (which Redshift returns for NULLs in some cases) to empty string
            if isinstance(val, bool) and val is True:
                row_data.append('')
            elif val is None:
                row_data.append('')
            else:
                row_data.append(sanitize_value(str(val)))  # Sanitize and ensure all values are strings
        data.append(row_data)

    # Log the fetched results for debugging
    logger.info(f"Fetched results: {data[:5]}")  # Log first 5 rows
    return column_names, data


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
    key = f"dashboard/lead/{current_date}.csv"    
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)  # Use quoting to handle special characters
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
    copy_query = f"""
        BEGIN;
        TRUNCATE TABLE {table_name};
        COPY {table_name} (
            lead_summary_id,
            lead_id,
            call_id,
            timestamp,
            lead_name,
            status,
            lead_score_by_broker,
            total_contact_attempts,
            lead_affiliate_level_category,
            audio_call_type,
            audio_call_type_reason,
            lead_type,
            lead_type_reason,
            lead_intrinsic_avg,
            concern_type,
            concern_type_reason,
            dollar_amount,
            account_type,
            lead_qualification,
            lead_qualification_reason,
            summary,
            created_datetime,
            velocify_uuid,
            source,
            lead_details_id,
            details_timestamp,
            duration,
            durationinsecs,
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
    WITH lead_details_union AS (
    SELECT
        ld.lead_id,
        ld.lead_details_id,
        ld.lead_name,
        ld.call_id,
        ld.timestamp AS details_timestamp,
        ld.duration,
        ld.durationInSecs,
        ld.criteria,
        ld.score,
        ld.reason,
        ld.call_type,
        ld.outcome
    FROM public.lead_details ld
    )

    SELECT
        ls.lead_summary_id,
        ls.lead_id,
        ls.call_id,
        ls.timestamp,
        ls.lead_name,
        ls.status,
        ls.lead_score_by_broker,
        ls.total_contact_attempts,
        ls.lead_affiliate_level_category,
        ls.audio_call_type,
        ls.audio_call_type_reason,
        ls.lead_type,
        ls.lead_type_reason,
        ls.lead_intrinsic_avg,
        ls.concern_type,
        ls.concern_type_reason,
        ls.dollar_amount,
        ls.account_type,
        ls.lead_qualification,
        ls.lead_qualification_reason,
        ls.summary,
        ls.created_datetime,
        ls.velocify_uuid,
        ls.source,
        ld.lead_details_id,
        ld.details_timestamp,
        ld.duration,
        ld.durationInSecs,
        ld.criteria,
        ld.score,
        ld.reason,
        ld.call_type,
        ld.outcome
    FROM public.lead_summary ls
    LEFT JOIN lead_details_union ld 
        ON ls.lead_id = ld.lead_id;

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
    truncate_and_copy_to_redshift("lead_dashboard", s3_key)
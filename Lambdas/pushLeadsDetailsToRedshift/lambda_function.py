import os
import json
import boto3
import uuid
from botocore.client import Config
import logging
import csv
from io import StringIO
import re

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO) 

# Initialize AWS clients
s3_client = boto3.client('s3')
session = boto3.session.Session()
region = session.region_name

# Secrets Manager client
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
secret_name = os.environ['SecretId']
get_secret_value_response = client_secretsmanager.get_secret_value(SecretId=secret_name)
secret_arn = get_secret_value_response['ARN']
secret_json = json.loads(get_secret_value_response['SecretString'])
cluster_id = secret_json['dbClusterIdentifier']

# Redshift client
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)

from datetime import datetime

def format_timestamp(timestamp_str):
    # Check if timestamp includes seconds, if not, add ':00'
    if len(timestamp_str) == 16:  # Format: '29-11-2024 15:44' (missing seconds)
        timestamp_str = timestamp_str + ":00"
    
    try:
        # Correct format is '%d-%m-%Y %H:%M:%S' (day-month-year hour:minute:second)
        timestamp = datetime.strptime(timestamp_str.strip(), '%d-%m-%Y %H:%M:%S')
        
        # Format the timestamp to Redshift's expected format: '%Y-%m-%d %H:%M:%S'
        formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return formatted_timestamp
    except ValueError as e:
        # If parsing fails, log and return None
        logger.info(f"Error parsing timestamp: {timestamp_str} -> {e}")
        return None

  
def lambda_handler(event, context):
    # return
    bucket_name = "sample540"
    file_key = "leads_details.csv"
    database = os.environ.get('database_name')
     # 1. Read CSV from S3
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content = csv_obj['Body'].read().decode('utf-8')

    # 2. Process CSV - Cast `lead_id` and `total_contact_attempts` to integers
    input_csv = StringIO(csv_content)
    output_csv = StringIO()
    
    reader = csv.reader(input_csv)
    writer = csv.writer(output_csv)

    # Read header
    headers = next(reader)
    writer.writerow(headers)  # Write header to new CSV

    for row in reader:
        try:
            # Convert to integer safely
            if row[1].strip():
                row[1] = int(float(row[1]))  # ✅ Convert float -> int
            else:
                row[1] = ''  # Leave empty for missing values
        except ValueError:
            row[1] = ''  # Handle invalid values
        
        # Cast timestamp field (assuming timestamp is in column index 4, adjust accordingly)
        if row[4]:  # Assuming the timestamp is in column index 4 (adjust if needed)
            row[4] = format_timestamp(row[4])  # Format the timestamp

        try:
            # ✅ Convert Score to DECIMAL(5,2)
            if row[7].strip():
                row[7] = f"{float(row[7]):.2f}"  # Format to 2 decimal places
            else:
                row[7] = ''
        except ValueError:
            row[7] = ''

        writer.writerow(row)  # Write processed row

    # 3. Upload processed CSV to S3
    processed_csv_key = f"processed/{file_key}"
    s3_client.put_object(Bucket=bucket_name, Key=processed_csv_key, Body=output_csv.getvalue())

    # 4. Load Processed CSV into Redshift
    s3_path = f"s3://{bucket_name}/processed/{file_key}"
    aws_credentials_secret_name = os.environ['credentials_secret_name']
    credentials_response = client_secretsmanager.get_secret_value(SecretId=aws_credentials_secret_name)
    aws_credentials = json.loads(credentials_response['SecretString'])
    aws_access_key = aws_credentials['AWS_ACCESS_KEY_ID']
    aws_secret_access_key = aws_credentials['AWS_SECRET_ACCESS_KEY']
    copy_sql = f"""
        COPY public.leads_details(lead_details_id,lead_id,lead_name,call_id, timestamp,duration,criteria,Score,reason,summary)
        FROM 's3://sample540/processed/leads_details.csv'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1;
    """

    response = client_redshift.execute_statement(
        Database=os.environ.get('database_name'),
        SecretArn=secret_arn,
        Sql=copy_sql,
        ClusterIdentifier=cluster_id
    )

    return {
        'statusCode': 200,
        'body': json.dumps(f"File {file_key} loaded into Redshift successfully!")
    }

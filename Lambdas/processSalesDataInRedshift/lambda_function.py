import os
import json
import boto3
import uuid
from botocore.client import Config
import logging
import csv
from io import StringIO

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
session = boto3.session.Session()
region = session.region_name

# Secrets Manager
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
secret_name = os.environ['SecretId']
get_secret_value_response = client_secretsmanager.get_secret_value(SecretId=secret_name)
secret_arn = get_secret_value_response['ARN']
secret_json = json.loads(get_secret_value_response['SecretString'])
cluster_id = secret_json['dbClusterIdentifier']
database_name = secret_json['dbName']

# Redshift client
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)
bucket_name = os.environ.get('bucket_name')  # Your S3 bucket name

def clean_amount(value):
    # logger.info(f"Cleaning amount: '{value}'")
    if not value or not isinstance(value, str):
        logger.error("Invalid amount value: expected non-empty string")
        return 0
    value = value.replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except ValueError as e:
        logger.error(f"ValueError converting amount: {e} for value: '{value}'")
        return 0

def lambda_handler(event, context):
    file_key = "Sales.csv"  # Your raw file
    processed_csv_key = f"processed/{file_key}"

    # Step 1: Read raw CSV from S3
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content = csv_obj['Body'].read().decode('utf-8')

    input_csv = StringIO(csv_content)
    output_csv = StringIO()
    reader = csv.DictReader(input_csv)
    
    # Define new fieldnames with Sales_ID
    fieldnames = ['Sales_ID', 'Lead_ID', 'Date', 'Amount', 'GrossSaleAmount']
    writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        try:
            logger.info(f"row:{row}")
            lead_id = int(row['Lead_ID']) if row['Lead_ID'].strip() else None
            # logger.info(f"Processing Lead_ID: {lead_id}")  # Log Lead_ID
            amount = clean_amount(row['Amount'])
            # logger.info(f"Cleaned Amount: {amount}")
            gross = clean_amount(row['GrossSaleAmount']) if row['GrossSaleAmount'].strip() else 0

            writer.writerow({
                'Sales_ID': str(uuid.uuid4()),
                'Lead_ID': lead_id,
                'Date': row['Date'],
                # 'Amount': 1.25,
                'Amount': amount,
                # 'GrossSaleAmount': 1.35
                'GrossSaleAmount': gross
            })
        except Exception as e:
            logger.error(f"Skipping row due to error: {e}")
            continue

    # Step 2: Upload cleaned CSV to processed/
    s3_client.put_object(Bucket=bucket_name, Key=processed_csv_key, Body=output_csv.getvalue())

    # Step 3: Get AWS credentials for COPY
    aws_credentials_secret_name = os.environ['credentials_secret_name']
    credentials_response = client_secretsmanager.get_secret_value(SecretId=aws_credentials_secret_name)
    aws_credentials = json.loads(credentials_response['SecretString'])
    aws_access_key = aws_credentials['AWS_ACCESS_KEY_ID']
    aws_secret_access_key = aws_credentials['AWS_SECRET_ACCESS_KEY']

    # Step 4: Copy into Redshift
    copy_sql = f"""
        COPY public.sales(Sales_ID, Lead_ID, Date, Amount, GrossSaleAmount)
        FROM 's3://{bucket_name}/{processed_csv_key}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV
        IGNOREHEADER 1;
    """

    response = client_redshift.execute_statement(
        Database=database_name,
        SecretArn=secret_arn,
        Sql=copy_sql,
        ClusterIdentifier=cluster_id
    )

    return {
        'statusCode': 200,
        'body': json.dumps(f"Processed and loaded {file_key} into Redshift successfully.")
    }

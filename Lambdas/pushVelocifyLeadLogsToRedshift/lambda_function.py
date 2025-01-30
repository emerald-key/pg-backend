import os
import json
import boto3
import uuid
import csv
import time
from io import StringIO
from botocore.client import Config
import re

# Initialize clients
s3_client = boto3.client('s3')
ses_client = boto3.client('ses')
lambda_client = boto3.client('lambda')
session = boto3.session.Session()
region = session.region_name
secret_name = os.environ['SecretId']  # Getting SecretId from Environment variables
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
get_secret_value_response = client_secretsmanager.get_secret_value(SecretId=secret_name)
secret_arn = get_secret_value_response['ARN']
secret_json = json.loads(get_secret_value_response['SecretString'])

cluster_id = secret_json['dbClusterIdentifier']

# Redshift client
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)
# Define allowed log results
ALLOWED_LOG_RESULTS = [
    "Created", "Qualified", "Paper work out", "Paper work in",
    "Pending IRA", "Pending Cash", "Client", "Reload", "House", "Do not contact"
]
ALLOWED_LOG_TYPES = [
    "Cal. Called: Contacted","Called: Contacted","Contacted: Not Interested","Contacted: Does Not Qualify","Created","Status Change"
]

def lambda_handler(event, context):
    try:
        # bucket_name = "raw-velocify-leadlogs"
        # object_key = "Lead_logs_AI_2024 Q4.csv"
        bucket_name = os.environ.get('bucket_name')
        object_key = event['Records'][0]['s3']['object']['key']
        # Skip processing if the file is in the "processed/" folder
        if object_key.startswith('processed/'):
            print(f"Skipping file: {object_key}")
            return {
                'statusCode': 200,
                'body': f"Skipped processing for file: {object_key}"
            }
        # Mapping of input column names to desired column names
        COLUMN_MAPPING = {
            "Log Type": "Log_Type",
            "Log Actor": "Log_Actor",
            "Log Date": "Log_Date",
            "Log Result": "Log_Result",
            "Log Note": "Log_Note",
            "Log Contact": "Log_Contact",
            "Id": "Lead_ID",
            "Campaign Name": "Campaign_Name",
            "Affiliate Name": "Affiliate_Name",
            "Status": "Status",
            "Last Contact Attempt Date": "Last_Contact_Attempt_Date",
        }
        table_name = 'public.staging_Lead_Log'
        truncate_table_query = f"TRUNCATE TABLE {table_name};"
        print("Starting table truncation...-1")
        execute_redshift_query(truncate_table_query)  # Waits for completion
        print("Table truncated successfully.-1")
        # Download the CSV file
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        csv_content = response['Body'].read().decode('utf-8')

        # Read the CSV data
        csv_reader = csv.DictReader(StringIO(csv_content))
        filtered_rows = []
        # Step 4: Process each row and clean Lead_ID
        for row in csv_reader:
            if row['Log Type'] in ALLOWED_LOG_TYPES:  # Assuming ALLOWED_LOG_TYPES is defined

                # Clean Lead_ID: Ensure it contains only numeric characters
                lead_id = row['Id'].strip()  # Strip any leading/trailing spaces
                if re.match(r'^\d+$', lead_id):  # Only keep if it's a number
                    row['Id'] = int(lead_id)  # Convert valid Lead_ID to integer
                else:
                    row['Id'] = None  # Set invalid Lead_ID as None (will be NULL in Redshift)

                # Map columns based on COLUMN_MAPPING
                mapped_row = {COLUMN_MAPPING[key]: value for key, value in row.items() if key in COLUMN_MAPPING}
                mapped_row['Lead_Log_Id'] = str(uuid.uuid4())  # Generate a UUID for each row
                filtered_rows.append(mapped_row)


        if not filtered_rows:
            print("No rows matched the allowed Log Results.")
            return

        # Define new column names
        column_names = list(COLUMN_MAPPING.values()) + ["Lead_Log_Id"]

        # Create a new CSV file with filtered data
        output_csv = StringIO()
        csv_writer = csv.DictWriter(output_csv, fieldnames=column_names)
        csv_writer.writeheader()
        csv_writer.writerows(filtered_rows)

        # Save the new CSV file to the same S3 bucket
        output_key = f"processed/{object_key.split('/')[-1].replace('.csv', '_processed.csv')}"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=output_csv.getvalue().encode('utf-8')
        )
        
        print(f"Processed file saved at: {output_key}")

        # Step: Construct S3 path for the processed CSV
        s3_path = f"s3://{bucket_name}/{output_key}"

        # Step: Load data into Redshift using COPY
        column_list = list(COLUMN_MAPPING.values()) + ["Lead_Log_Id"]

        # Copy the data from S3 to Redshift
        copied_rows = copy_data_to_redshift(s3_path, table_name, column_list)
        print(f"Rows copied to Redshift: {copied_rows}")

        # Step: Remove duplicates and insert into the lead_log table
        remove_duplicates_and_insert_to_lead_log(table_name)

        return {
            "statusCode": 200,
            "body": json.dumps(f"Processed file saved at {output_key} and data loaded into Redshift successfully.")
        }

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        err_subject = "LeadLogs:Error Processing CSV To Redshift"
        err_body = f"""
        Error : {str(e)}
        """
        send_email(err_subject, err_body)
        return {
            'statusCode': 500,
            'body': f"Failed to process file: {str(e)}"
        }
        return {
            "statusCode": 500,
            "body": json.dumps(f"Error processing CSV: {str(e)}")
        }

def copy_data_to_redshift(s3_path, table_name, column_list):
    """
    COPY data from S3 to Redshift.
    :param s3_path: S3 path of the processed CSV.
    :param table_name: Target Redshift table name.
    :param column_list: List of target columns in Redshift table.
    """
    aws_credentials_secret_name = os.environ['credentials_secret_name']
    credentials_response = client_secretsmanager.get_secret_value(SecretId=aws_credentials_secret_name)
    aws_credentials = json.loads(credentials_response['SecretString'])
    aws_access_key = aws_credentials['AWS_ACCESS_KEY_ID']
    aws_secret_access_key = aws_credentials['AWS_SECRET_ACCESS_KEY']
    
    try:
        copy_query = f"""
        COPY {table_name} ({', '.join(column_list)})
        FROM '{s3_path}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1
        DELIMITER ','
        TIMEFORMAT 'auto'
        TRUNCATECOLUMNS;
        """
        execute_redshift_query(copy_query)
        print(f"Data copied successfully to Redshift.")

        # Optionally: Count the rows in Redshift before and after to verify
        before_count = get_table_row_count()
        after_count = get_table_row_count()

        inserted_rows = after_count - before_count
        print(f"Rows inserted into {table_name}: {inserted_rows}")
        return inserted_rows

    except Exception as e:
        print(f"Error copying data to Redshift: {e}")
        raise

def get_table_row_count():
    try:
        # Execute the query
        query = "SELECT COUNT(*) FROM public.lead_log;"
        response = client_redshift.execute_statement(
            Database='dev',
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
            print(f"Waiting for row count query to complete... Current status: {status_response['Status']}")
            time.sleep(1)

        if status_response['Status'] == 'FINISHED':
            # Fetch the result
            result_response = client_redshift.get_statement_result(Id=statement_id)
            records = result_response['Records']
            # Extract the row count from the response
            row_count = int(records[0][0]['longValue'])
            print(f"Row count: {row_count}")
            return row_count
        else:
            raise Exception(f"Query failed with status: {status_response['Status']}")

    except Exception as e:
        print(f"Error getting table row count: {e}")
        raise
def remove_duplicates_and_insert_to_lead_log(table_name):
    """
    Remove duplicates from the staging table and insert unique records into the lead_log table.
    """
    try:

        # Step 1: Insert unique records into lead_log table
        insert_query = f"""
        INSERT INTO public.lead_log (
        Lead_Log_Id, Log_Type, Log_Actor, Log_Date, Log_Result, Log_Note, Log_Contact, Lead_ID, Campaign_Name, Affiliate_Name,Status,Last_Contact_Attempt_Date
        )
        SELECT DISTINCT
            Lead_Log_Id,
            Log_Type,
            Log_Actor,
            CASE
                WHEN Log_Date IS NULL THEN NULL
                WHEN Log_Date = '' THEN NULL
                ELSE TO_TIMESTAMP(Log_Date, 'YYYY-MM-DD HH24:MI:SS')
            END AS Log_Date,
            Log_Result,
            Log_Note,
            Log_Contact,
            Lead_ID,
            Campaign_Name,
            Affiliate_Name,
            Status,
            CASE
                WHEN Last_Contact_Attempt_Date IS NULL THEN NULL
                WHEN Last_Contact_Attempt_Date = '' THEN NULL
                ELSE TO_TIMESTAMP(Last_Contact_Attempt_Date, 'YYYY-MM-DD HH24:MI:SS')
            END AS Last_Contact_Attempt_Date
        FROM public.staging_lead_log
        WHERE NOT EXISTS (
            SELECT 1 FROM public.Lead_Log WHERE public.Lead_Log.Lead_Log_Id = public.staging_Lead_Log.Lead_Log_Id
        );
        """
        execute_redshift_query(insert_query)
        print("Unique records inserted into lead_log.")
        truncate_table_query_end = f"TRUNCATE TABLE {table_name};"
        print("Starting table truncation...-2")
        execute_redshift_query(truncate_table_query_end)  # Waits for completion
        print("Table truncated successfully.-2")

    except Exception as e:
        print(f"Error removing duplicates and inserting into lead_log: {e}")
        raise

def execute_redshift_query(query_str):
    """
    Execute a query in the Redshift cluster and wait for its completion.
    """
    try:
        # Execute the query
        response = client_redshift.execute_statement(
            Database='dev',
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        statement_id = response['Id']
        print(f"Query submitted successfully. Statement ID: {statement_id}")

        # Wait for the query to complete
        while True:
            query_status = client_redshift.describe_statement(Id=statement_id)
            status = query_status['Status']
            if status in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            print(f"Waiting for query to complete... Current status: {status}")
        
        if status == 'FINISHED':
            print("Query executed successfully.")
            return query_status
        else:
            raise Exception(f"Query execution failed. Status: {status}, Error: {query_status.get('Error', 'Unknown error')}")

    except Exception as e:
        print(f"Error executing query: {str(e)}")
        raise
def send_email(subject, body):
    try:
        recipient_emails_env = os.environ.get('SES_RECIPIENT_EMAILS', '')
        # Split the emails into a list
        recipient_emails = [email.strip() for email in recipient_emails_env.split(',') if email.strip()]
        # recepient_emails=["sravya.v@quiddityinfotech.com","sravya.vemulapally@emeraldkey.com"]
        ses_client.send_email(
            Source=os.environ['SES_SOURCE_EMAIL'],
            Destination={'ToAddresses': recepient_emails},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise

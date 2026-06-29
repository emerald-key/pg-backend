import os
import json
import boto3
import io
import csv
from botocore.client import Config
import time
import logging
import uuid

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


def convert_to_seconds(time_str, call_id):
    """
    Converts a time duration string in the format 'hrs:min:sec' to total seconds.
    Handles invalid inputs like '(N/A)' by returning None.
    """
    try:
        print(f"Processing Call_ID: {call_id}, Time String: {time_str}")

        if not time_str or time_str in ['N/A', '(N/A)', '']:  # Handle invalid cases
            print(f"Skipping invalid time format for Call_ID: {call_id}")
            return None

        # Split into hours, minutes, and seconds
        parts = time_str.split(':')
        if len(parts) != 3:
            print(f"Incorrect time format for Call_ID: {call_id} -> {time_str}")
            return None  # If format is incorrect, return None

        # Check if all parts are valid integers
        if any(not part.isdigit() for part in parts):
            print(f"Non-integer value found in time parts for Call_ID: {call_id} -> {parts}")
            return None

        hours, minutes, seconds = map(int, parts)  # Convert to integers
        return hours * 3600 + minutes * 60 + seconds  # Convert to seconds

    except ValueError:
        print(f"Error converting time for Call_ID: {call_id}, Time String: {time_str}")
        return None  # Return None if conversion fails

def preprocess_csv(bucket_name, file_key, output_key, column_mapping):
    """
    Preprocess CSV: Rename columns based on `column_mapping` and filter unwanted columns.
    Keeps the original 'Call Duration (hrs:min:sec)' column and converts 'Talk_Time' to seconds.

    :param bucket_name: S3 bucket containing the input file.
    :param file_key: Key of the input CSV file in the bucket.
    :param output_key: Key for the processed CSV file in S3.
    :param column_mapping: Dict mapping CSV column names to Redshift table column names.
    """
    try:
        # Get the CSV file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response['Body'].read().decode('utf-8')
        csv_file = io.StringIO(file_content)

        # Read and process the CSV
        csv_reader = csv.DictReader(csv_file)
        processed_rows = []

        # Dictionary to store UUIDs for each Velocify_Recording_URL
        uuid_map = {}

        for row in csv_reader:
            processed_row = {new_col: row[old_col] for old_col, new_col in column_mapping.items() if old_col in row}
            
            # Keep original call duration and convert Talk_Time
            if 'Call Duration (hrs:min:sec)' in row:
                processed_row['Call_Duration_Original'] = row['Call Duration (hrs:min:sec)']
                processed_row['Talk_Time'] = convert_to_seconds(row['Call Duration (hrs:min:sec)'], row['Call Id'])
            if 'Conversation Duration (hrs:min:sec)' in row:
                processed_row['Conversation_Time'] = row['Conversation Duration (hrs:min:sec)']
                processed_row['Conversation_Time_In_Secs'] = convert_to_seconds(row['Conversation Duration (hrs:min:sec)'],row['Call Id'])
            # Convert Lead_ID to integer if valid
            lead_id = row.get('Lead Id', '').strip()
            if lead_id.isdigit():
                processed_row['Lead_ID'] = int(lead_id)

            # ✅ Handle velocify_uuid based on Velocify_Recording_URL
            recording_url = row.get('Recording', '').strip()
            if recording_url:
                if recording_url not in uuid_map:
                    uuid_map[recording_url] = str(uuid.uuid4())  # Generate new UUID
                processed_row['Velocify_UUID'] = uuid_map[recording_url]

            processed_rows.append(processed_row)

        # Write the processed CSV to a new S3 key
        output_csv = io.StringIO()
        fieldnames = list(column_mapping.values()) + ['Talk_Time', 'Call_Duration_Original', 'Lead_ID', 'Velocify_UUID','Conversation_Time','Conversation_Time_In_Secs']
        csv_writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(processed_rows)
        output_csv.seek(0)

        # Upload to S3
        s3_client.put_object(Bucket=bucket_name, Key=output_key, Body=output_csv.getvalue())
        logger.info(f"Processed CSV uploaded to {output_key} in {bucket_name}")

    except Exception as e:
        logger.error(f"Error preprocessing CSV: {e}")
        raise

def copy_data_to_redshift(s3_path, table_name, main_column_list):
    column_list = main_column_list + ['Talk_Time','Call_Duration_Original','Lead_ID','Velocify_UUID','Conversation_Time','Conversation_Time_In_Secs']
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
        BEGIN;
        TRUNCATE TABLE {table_name};
        COPY {table_name} ({', '.join(column_list)})
        FROM '{s3_path}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1;
        COMMIT;
        """
        execute_redshift_query(copy_query)
        # Get row count before insert
        before_count = get_table_row_count()
        logger.info(f"Row count before insert: {before_count}")
        insert_query = f"""
        BEGIN;
        -- Step 1: Insert missing leads into the lead table
        INSERT INTO public.lead (Lead_ID)
        SELECT DISTINCT staging_call.Lead_ID 
        FROM public.staging_call AS staging_call
        LEFT JOIN public.lead AS lead_table
            ON staging_call.Lead_ID = lead_table.Lead_ID
        WHERE lead_table.Lead_ID IS NULL
        AND staging_call.Lead_ID IS NOT NULL;  -- Ensure no NULL values are inserted



        -- Step 2: Insert calls into the call table
        INSERT INTO public.call (
            Call_ID, Lead_ID, Broker_Name, Outcome, Call_Segment, Call_Type, Date_Time, Talk_Time,Call_Duration_Original, Prospect_Number, Inbound_Number,Velocify_Recording_URL,Velocify_UUID,Conversation_Time,Conversation_Time_In_Secs,Source
        )
        SELECT DISTINCT
            Call_ID,
            Lead_ID,
            Broker_Name,
            Outcome,
            Call_Segment,
            Call_Type,
            CASE
                WHEN Date_Time = '' THEN NULL  -- Handle empty Date_Time
                ELSE NULLIF(Date_Time, '')::TIMESTAMP  -- Safely cast to TIMESTAMP
            END AS Date_Time,
            Talk_Time,
            Call_Duration_Original,
            Prospect_Number,
            Inbound_Number,
            Velocify_Recording_URL,
            Velocify_UUID,
            Conversation_Time,
            Conversation_Time_In_Secs,
            Source
        FROM public.staging_call
        WHERE NOT EXISTS (
            SELECT 1 FROM public.call WHERE public.call.Call_ID = public.staging_call.Call_ID
        );
        TRUNCATE TABLE {table_name};

        COMMIT;
        """
        execute_redshift_query(insert_query)
        logger.info("Data copied successfully to Redshift.")

        after_count = get_table_row_count()
        logger.info(f"Row count after insert: {after_count}")
        # Calculate inserted rows
        inserted_rows = after_count - before_count
        logger.info(f"Rows inserted into public.call: {inserted_rows}")
        return inserted_rows
       
    except Exception as e:
        logger.info(f"Error copying data to Redshift: {e}")
        raise


def get_table_row_count():
    try:
        # Execute the query
        query = "SELECT COUNT(*) FROM public.call;"
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

def lambda_handler(event, context):
    """
    Lambda function to process the CSV, preprocess, and load data into Redshift.
    """
    # event = {
    #     'bucket_name': 'raw-velocify-calllogs',
    #     'file_key': 'Lm32481_CallHistory_20250913_235943_42de708e-1591-450f-b252-ec3052e5da7f_Sep132025.csv',
    # }
    # event = {
    #     'bucket_name': 'raw-velocify-calllogs',
    #     'file_key': 'Lm32481_CallHistory_20250703_210821_03a52bfb-496b-4227-bdce-f235a5106f57_June28-302025.csv',
    # }
    
    # Input and output details
    bucket_name = event['bucket_name']
    input_file_key = event['file_key']
    output_file_key = f"processed/{input_file_key}"
    table_name = 'public.staging_call'

    # Column mapping: Map CSV column names to Redshift table column names
    column_mapping =  {
        'Call Id': 'Call_ID',
        'User': 'Broker_Name',
        'Result': 'Outcome',
        'Call Segment':'Call_Segment',
        'Origin':'Call_Type',
        'Time':'Date_Time',
        'Prospect Number':'Prospect_Number',
        'Inbound Number':'Inbound_Number',
        'Recording': 'Velocify_Recording_URL',
        'Lead Source': 'Source'
    }
    # Skip processing if the file is in the "processed/" folder
    if input_file_key.startswith('processed/'):
        logger.info(f"Skipping file: {input_file_key}")
        return {
            'statusCode': 200,
            'body': f"Skipped processing for file: {input_file_key}"
        }
    try:

        # Step 2: Preprocess the CSV
        preprocess_csv(bucket_name, input_file_key, output_file_key, column_mapping)

        # Step 3: Construct S3 path for the processed CSV
        s3_path = f"s3://{bucket_name}/{output_file_key}"
        column_list = list(column_mapping.values())

        # Step 4: Load data into Redshift
        copied_rows = copy_data_to_redshift(s3_path, table_name, column_list)

         # Step 5: Count rows in the CSV file (excluding header)
        response = s3_client.get_object(Bucket=bucket_name, Key=input_file_key)
        csv_lines = response['Body'].read().decode('utf-8').splitlines()
        csv_row_count = len(csv_lines) - 1  # Exclude header
        if(copied_rows < csv_row_count):
            # Step 6: Send SES email
            subject = "Call Logs : Redshift Data Load Completed"
            body = f"""
            Bucket Name: {bucket_name}
            CSV File Loaded: {input_file_key}
            Total Rows in CSV: {csv_row_count}
            Rows Copied to Redshift: {copied_rows}
            """
            send_email(subject, body)

        return {
            'statusCode': 200,
            'body': f'CSV {input_file_key} processed and data loaded into Redshift successfully.'
        }
    except Exception as e:
        logger.info(f"Error in lambda_handler: {e}")
        err_subject = "Error Processing CSV To Redshift"
        err_body = f"""
        Error : {str(e)}
        """
        send_email(err_subject, err_body)
        return {
            'statusCode': 500,
            'body': f"Error processing CSV: {str(e)}"
        }


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


def execute_redshift_query(query_str):
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


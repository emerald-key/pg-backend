import os
import json
import boto3
import io
import csv
from botocore.client import Config
import time
import logging

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

        for row in csv_reader:
            processed_row = {new_col: row[old_col] for old_col, new_col in column_mapping.items() if old_col in row}
            
            # Keep original call duration and convert Talk_Time
            if 'Call Duration (hrs:min:sec)' in row:
                processed_row['Call_Duration_Original'] = row['Call Duration (hrs:min:sec)']
                
                # Convert to seconds only if Talk_Time exists in the column mapping
                processed_row['Talk_Time'] = convert_to_seconds(row['Call Duration (hrs:min:sec)'],row['Call Id'])
            if 'Lead Id' in row:
                lead_id = row['Lead Id'].strip()
            
            # Check if lead_id is a valid numeric string
            if lead_id.isdigit():
                processed_row['Lead_ID'] = int(lead_id)
            processed_rows.append(processed_row)

        # Write the processed CSV to a new S3 key
        output_csv = io.StringIO()
        fieldnames = list(column_mapping.values()) + ['Talk_Time','Call_Duration_Original','Lead_ID']
        csv_writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
        csv_writer.writeheader()
        csv_writer.writerows(processed_rows)
        output_csv.seek(0)

        # Upload to S3
        s3_client.put_object(Bucket=bucket_name, Key=output_key, Body=output_csv.getvalue())
        logger.info(f"Processed CSV uploaded to {output_key} in {bucket_name}")

    except Exception as e:
        logger.error(f"Error preprocessing CSV: {e}- {file_key}")
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
def copy_data_to_redshift(s3_path, table_name, main_column_list):
    column_list = main_column_list + ['Talk_Time','Call_Duration_Original','Lead_ID']
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
        CSV IGNOREHEADER 1;
        """
        execute_redshift_query(copy_query)
        # Get row count before insert
        before_count = get_table_row_count()
        logger.info(f"Row count before insert: {before_count}")
        insert_query = f"""
        UPDATE public.call
        SET Velocify_Recording_URL = staging_call.Velocify_Recording_URL
        FROM public.staging_call
        WHERE public.call.Call_ID = staging_call.Call_ID
        AND (public.call.Velocify_Recording_URL IS NULL OR public.call.Velocify_Recording_URL = '');
        """
        execute_redshift_query(insert_query)
        logger.info("Data copied successfully to Redshift.")

        truncate_table_query_end = f"TRUNCATE TABLE {table_name};"
        logger.info("Starting table truncation...-2")
        execute_redshift_query(truncate_table_query_end)  # Waits for completion
        logger.info("Table truncated successfully.-2")
        after_count = get_table_row_count()
        logger.info(f"Row count after insert: {after_count}")
        # Calculate inserted rows
        inserted_rows = after_count - before_count
        logger.info(f"Rows inserted into public.call: {inserted_rows}")
        return inserted_rows
       
    except Exception as e:
        logger.info(f"Error copying data to Redshift: {e}")
        raise

def lambda_handler(event, context):
    """
    Lambda function to process the CSV, preprocess, and load data into Redshift.
    """
    # e
    event = {
        'bucket_name': 'raw-velocify-calllogs',
        'files': [
            "Lm32481_CallHistory_084920_b85c7cb4-abd9-45cb-aefd-a828160cb553_Apr23to242024.csv",
            "Lm32481_CallHistory_085352_6338c063-b173-466a-8671-7b2c4af81a29_Apr25to272024.csv",
            "Lm32481_CallHistory_085542_0d030329-4fcc-4955-aa28-8eeb116eac90_Apr28to302024.csv",
            "Lm32481_CallHistory_090138_3ae22172-0ef8-4d51-8329-e02174818f56_May12024.csv",
            "Lm32481_CallHistory_090211_77a30633-28a0-40e0-8c20-e696133f7798_May2to32024.csv",
            "Lm32481_CallHistory_090325_3e5946ca-6625-4b35-82e5-989302837a6f_May4to72024.csv",
            "Lm32481_CallHistory_090836_4cc1b2ae-98d2-4dd2-ae55-56047a89546e_May82024.csv",
            "Lm32481_CallHistory_090905_cd94b31d-5f51-4e2c-9a3b-ba2c2b85e4f8_May9to102024.csv",
            "Lm32481_CallHistory_091144_5837aa45-436b-460c-8d31-b47ae8cc9eb0_May11to142024.csv",
            "Lm32481_CallHistory_091401_9b557681-766b-4296-a36d-1ee2b7aa18d8_May15to162024.csv",
            "Lm32481_CallHistory_091618_d224409a-4bdb-4658-b2d3-9b3808671e55_jan62024.csv",
            "Lm32481_CallHistory_091642_7dc1d968-5305-41aa-81e4-fe4bc1e902e5_May17to202024.csv",
            "Lm32481_CallHistory_091723_bd11e570-5d6a-403d-be5a-9d478983d703_jan72025.csv",
            "Lm32481_CallHistory_091831_6d59b7fa-78fe-4f2c-9d5a-97ff7d02fa2c_May21to222024.csv",
            "Lm32481_CallHistory_092054_0c758141-f40f-4ac1-8a53-d44e808ecf7a_May23to252024.csv",
            "Lm32481_CallHistory_092533_1f85a25c-2a1e-4a0b-8ee6-4c493acc1e7d_May26to292024.csv",
            "Lm32481_CallHistory_092648_16aa717b-96bd-46d4-ab2f-92218b135ddf_May30to312024.csv",
            "Lm32481_CallHistory_092820_2e2d3fe2-0808-4903-ae35-2ab2b65c9e24_June1to42024.csv",
            "Lm32481_CallHistory_20241119_205339_b1af15ef-42cb-4b8a-b8f4-61dd443a0204.csv",
            "Lm32481_CallHistory_20241119_205520_a97b1e9a-3b3e-47fd-a3e1-7e19b2247520.csv",
            "Lm32481_CallHistory_20241119_205746_6b80c371-a30a-4933-a83e-b57a5d38c303.csv",
            "Lm32481_CallHistory_20241119_205910_368a4fe7-9536-422b-acb5-944d952de29d.csv",
            "Lm32481_CallHistory_20241119_210055_09b2e378-d20e-44be-ad4f-4205cf179159.csv",
            "Lm32481_CallHistory_20241119_210225_818899ee-0e28-4b8d-8ee1-77e170cb4623.csv",
            "Lm32481_CallHistory_20241119_210553_d0fb9404-0873-4e63-a5e0-473632d5d65a.csv",
            "Lm32481_CallHistory_20241119_210743_f9266752-44be-4298-b8c7-1363c946f4d1.csv",
            "Lm32481_CallHistory_20241119_211032_88636b0f-bece-47a5-9a5a-c2eed219a982.csv",
            "Lm32481_CallHistory__072955_dd160a56-47e8-4279-86df-9e350ea4327a_Aug16to182024.csv",
            "Lm32481_CallHistory__081121_e6cc8fdd-0414-407d-8e0f-01397599cb95_Jan312025.csv",
            "Lm32481_CallHistory__081339_f2641eb3-97d6-4b18-885f-262c13fc7b43_Feb1to32025.csv"
        ]
    }
    # Input and output details
    bucket_name = event['bucket_name']
    # input_file_key = event['file_key']
    for input_file_key in event['files']:
        logger.info(f"Processing file: {input_file_key}")
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
            'Recording': 'Velocify_Recording_URL'
        }
        # Skip processing if the file is in the "processed/" folder
        if input_file_key.startswith('processed/'):
            logger.info(f"Skipping file: {input_file_key}")
            return {
                'statusCode': 200,
                'body': f"Skipped processing for file: {input_file_key}"
            }
        try:
            # Step 1: Truncate the staging table
            truncate_table_query = f"TRUNCATE TABLE {table_name};"
            logger.info("Starting table truncation...-1")
            execute_redshift_query(truncate_table_query)  # Waits for completion
            logger.info("Table truncated successfully.-1")

            # Step 2: Preprocess the CSV
            preprocess_csv(bucket_name, input_file_key, output_file_key, column_mapping)

            # Step 3: Construct S3 path for the processed CSV
            s3_path = f"s3://{bucket_name}/{output_file_key}"
            column_list = list(column_mapping.values())

            # Step 4: Load data into Redshift
            copied_rows = copy_data_to_redshift(s3_path, table_name, column_list)

            # Step 5: Count rows in the CSV file (excluding header)
            response = s3_client.get_object(Bucket=bucket_name, Key=input_file_key)
            logger.info(f"CSV{input_file_key} processed and data loaded into Redshift successfully.")
        except Exception as e:
            logger.info(f"Error in lambda_handler: {e}")

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


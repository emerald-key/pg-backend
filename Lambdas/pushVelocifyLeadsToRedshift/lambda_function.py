import os
import json
import boto3
import botocore
import botocore.session as bc
from botocore.client import Config
import time
import io
import csv
import logging

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO) 

# Initialize S3 client and other clients
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
session = boto3.session.Session()
region = session.region_name

# Initializing Secret Manager's client    
client = session.client(
    service_name='secretsmanager',
    region_name=region
)

get_secret_value_response = client.get_secret_value(
    SecretId=secret_name
)
secret_arn = get_secret_value_response['ARN']
secret = get_secret_value_response['SecretString']
secret_json = json.loads(secret)
cluster_id = secret_json['dbClusterIdentifier']
database_name = secret_json['dbName']
# Initializing Redshift's client   
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)


def preprocess_csv(bucket_name, file_key, output_key, column_mapping):
    """
    Preprocess CSV: Rename columns based on `column_mapping` and filter unwanted columns.
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

        # Read and filter the CSV
        csv_reader = csv.DictReader(csv_file)
        processed_rows = []
        for row in csv_reader:
            processed_row = {new_col: row[old_col] for old_col, new_col in column_mapping.items() if old_col in row}
            processed_rows.append(processed_row)

        # Write the processed CSV to a new S3 key
        output_csv = io.StringIO()
        csv_writer = csv.DictWriter(output_csv, fieldnames=list(column_mapping.values()))
        csv_writer.writeheader()
        csv_writer.writerows(processed_rows)
        output_csv.seek(0)

        s3_client.put_object(Bucket=bucket_name, Key=output_key, Body=output_csv.getvalue())
        logger.info(f"Processed CSV uploaded to {output_key} in {bucket_name}")
    except Exception as e:
        logger.info(f"Error preprocessing CSV: {e}")
        raise

def execute_redshift_query(query_str):
    """
    Execute a query in the Redshift cluster.
    """
    try:
        result = client_redshift.execute_statement(
            Database=database_name,
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        # logger.info(f"Query:{query_str}")
        logger.info(f"Query executed successfully: {result}")
        return result
    except Exception as e:
        logger.info(f"Error executing query: {str(e)}")
        raise

def lambda_handler(event, context):
    logger.info(f"Entered lambda_handler: {event}")
    # event = {
    #     'bucket_name': 'raw-velocify-leads',
    #     'input_file_key': 'AI_full_download_20250121_0803279940_jan2025.csv',
    #     'output_file_key': 'processed/AI_full_download_20250121_0803279940_jan2025.csv',
    #     'table_name': 'public.staging_lead',
    #     'column_mapping': {
    #         'Id': 'Lead_ID',
    #         'Lead Source': 'Source',
    #         'Status': 'Lead_Status',
    #         'Lead Score #': 'Lead_Score',
    #         'Milestone': 'Milestone',
    #         'User':'Broker_Name',
    #         'Group': '"Group"',
    #         'Date Added': 'Date_Added',
    #         'Last Action': 'Last_Action',
    #         'First Contact Attempt Date': 'First_Contact_Attempt_Date',
    #         'Action Count': 'Action_Count',
    #         'Total Contact Attempts': 'Total_Contact_Attempts',
    #         'Last Action Date': 'Last_Action_Date',
    #         'First Assignment / Distribution Date': 'First_Assignment_Distribution_Date',
    #         'First Assignment / Distribution User': 'First_Assignment_Distribution_User',
    #         'Lead Source Group': 'Lead_Source_Group',
    #         'Creative': 'Creative',
    #         'Broker': 'Broker',
    #         'Opener': 'Opener',
    #         'IRA - Investment Dollar': 'IRA_Investment_Dollar',
    #         'Cash - Investment Dollar': 'Cash_Investment_Dollar',
    #         'Deal Type': 'Deal_Type',
    #         'Transfer Type': 'Transfer_Type',
    #         'TO Date': '"TO_Date"',
    #         'SF Lead ID': 'SF_Lead_ID',
    #         'Velocify ID': 'Velocify_ID',
    #         'Original Broker': 'Original_Broker',
    #         'SF Lead Owner': 'SF_Lead_Owner',
    #         'Junior Broker': 'Junior_Broker',
    #         'Last Activity': 'Last_Activity',
    #         'Intellect Client ID': 'Intellect_Client_ID',
    #         'Intellect Broker': 'Intellect_Broker',
    #         'First Name': 'First_Name',
    #         'Last Name': 'Last_Name',
    #         'Home Phone': 'Home_Phone',
    #         'Work Phone': 'Work_Phone',
    #         'Mobile Phone': 'Mobile_Phone',
    #         'Email': 'Email',
    #         'Secondary E-Mail': 'Secondary_Email',
    #         'Address': 'Address',
    #         'City': 'City',
    #         'State': 'State',
    #         'Zip/Postal Code': 'Zip_Postal_Code',
    #         'Source Code': 'Source_Code',
    #         'SubID': 'SubID'
    #     }

    # }
    bucket_name = os.environ.get('bucket_name')
    input_file_key = event['Records'][0]['s3']['object']['key']
    # input_file_key = "AI_full_download_20250525_110339f651_March27-May172025.csv"
    output_file_key = f"processed/{input_file_key}"
    table_name = 'public.staging_lead'
    column_mapping = {
            'Id': 'Lead_ID',
            'Lead Source': 'Source',
            'Status': 'Lead_Status',
            'Lead Score #': 'Lead_Score',
            'Milestone': 'Milestone',
            'User':'Broker_Name',
            'Group': '"Group"',
            'Date Added': 'Date_Added',
            'Last Action': 'Last_Action',
            'First Contact Attempt Date': 'First_Contact_Attempt_Date',
            'Action Count': 'Action_Count',
            'Total Contact Attempts': 'Total_Contact_Attempts',
            'Last Action Date': 'Last_Action_Date',
            'First Assignment / Distribution Date': 'First_Assignment_Distribution_Date',
            'First Assignment / Distribution User': 'First_Assignment_Distribution_User',
            'Lead Source Group': 'Lead_Source_Group',
            'Creative': 'Creative',
            'Broker': 'Broker',
            'Opener': 'Opener',
            'IRA - Investment Dollar': 'IRA_Investment_Dollar',
            'Cash - Investment Dollar': 'Cash_Investment_Dollar',
            'Deal Type': 'Deal_Type',
            'Transfer Type': 'Transfer_Type',
            'TO Date': '"TO_Date"',
            'SF Lead ID': 'SF_Lead_ID',
            'Velocify ID': 'Velocify_ID',
            'Original Broker': 'Original_Broker',
            'SF Lead Owner': 'SF_Lead_Owner',
            'Junior Broker': 'Junior_Broker',
            'Last Activity': 'Last_Activity',
            'Intellect Client ID': 'Intellect_Client_ID',
            'Intellect Broker': 'Intellect_Broker',
            'First Name': 'First_Name',
            'Last Name': 'Last_Name',
            'Home Phone': 'Home_Phone',
            'Work Phone': 'Work_Phone',
            'Mobile Phone': 'Mobile_Phone',
            'Email': 'Email',
            'Secondary E-Mail': 'Secondary_Email',
            'Address': 'Address',
            'City': 'City',
            'State': 'State',
            'Zip/Postal Code': 'Zip_Postal_Code',
            'Source Code': 'Source_Code',
            'SubID': 'SubID'
        }
    # Skip processing if the file is in the "processed/" folder
    if input_file_key.startswith('processed/'):
        logger.info(f"Skipping file: {input_file_key}")
        return {
            'statusCode': 200,
            'body': f"Skipped processing for file: {input_file_key}"
        }
    try:
        # Step 1: Preprocess the CSV
        preprocess_csv(bucket_name, input_file_key, output_file_key, column_mapping)

        # Step 2: Construct S3 path for the processed CSV
        s3_path = f"s3://{bucket_name}/{output_file_key}"
        column_list = list(column_mapping.values())
        # Step 3: Load data into Redshift
        copied_rows = copy_data_to_redshift(s3_path, table_name, column_list)

         # Step 4: Count rows in the CSV file (excluding header)
        # response = s3_client.get_object(Bucket=bucket_name, Key=input_file_key)
        # csv_lines = response['Body'].read().decode('utf-8').splitlines()
        # csv_row_count = len(csv_lines) - 1  # Exclude header
        # if(copied_rows < csv_row_count):
        #     # Step 5: Send SES email
        #     subject = "Leads : Redshift Data Load Completed"
        #     body = f"""
        #     Bucket Name: {bucket_name}
        #     CSV File Loaded: {input_file_key}
        #     Total Rows in CSV: {csv_row_count}
        #     Rows Copied to Redshift: {copied_rows}
        #     """
        #     send_email(subject, body)


        return {
            'statusCode': 200,
            'body': 'CSV processed and data loaded into Redshift successfully.'
        }

    except Exception as e:
        logger.info(f"Error: {str(e)}")
        err_subject = "Leads:Error Processing CSV To Redshift"
        err_body = f"""
        Error : {str(e)}
        """
        send_email(err_subject, err_body)
        return {
            'statusCode': 500,
            'body': f"Failed to process file: {str(e)}"
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
        BEGIN;
        TRUNCATE TABLE {table_name};
        COPY {table_name} ({', '.join(column_list)})
        FROM '{s3_path}'
        CREDENTIALS 'aws_access_key_id={aws_access_key};aws_secret_access_key={aws_secret_access_key}'
        CSV IGNOREHEADER 1;
        COMMIT;
        """
        logger.info(f'copy_query:{copy_query}')
        execute_redshift_query(copy_query)

        timezone_query = f"""
        SET timezone = 'US/Eastern';
        """
        execute_redshift_query(timezone_query)
        # Get row count before insert
        before_count = get_table_row_count()
        logger.info(f"Row count before insert: {before_count}")
        update_query = f"""
        UPDATE public.Lead
        SET 
            Source = staging.Source,
            Lead_Status = staging.Lead_Status,
            Lead_Score = staging.Lead_Score,
            Milestone = staging.Milestone,
            Broker_Name = staging.Broker_Name,
            "Group" = staging."Group",
            Date_Added = COALESCE(
                CASE 
                    WHEN NULLIF(staging.Date_Added, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.Date_Added, '')::TIMESTAMP 
                    ELSE NULL 
                END,
                public.Lead.Date_Added
            ),
            Last_Action = staging.Last_Action,
            First_Contact_Attempt_Date = COALESCE(
                CASE 
                    WHEN NULLIF(staging.First_Contact_Attempt_Date, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.First_Contact_Attempt_Date, '')::TIMESTAMP 
                    ELSE NULL 
                END,
                public.Lead.First_Contact_Attempt_Date
            ),
            Action_Count = NULLIF(staging.Action_Count, '')::INT,
            Total_Contact_Attempts = NULLIF(staging.Total_Contact_Attempts, '')::INT,
            Last_Action_Date = COALESCE(
                CASE 
                    WHEN NULLIF(staging.Last_Action_Date, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.Last_Action_Date, '')::TIMESTAMP 
                    ELSE NULL 
                END,
                public.Lead.Last_Action_Date
            ),
            First_Assignment_Distribution_Date = COALESCE(
                CASE 
                    WHEN NULLIF(staging.First_Assignment_Distribution_Date, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.First_Assignment_Distribution_Date, '')::TIMESTAMP 
                    ELSE NULL 
                END,
                public.Lead.First_Assignment_Distribution_Date
            ),
            First_Assignment_Distribution_User = staging.First_Assignment_Distribution_User,
            Lead_Source_Group = staging.Lead_Source_Group,
            Creative = staging.Creative,
            Broker = staging.Broker,
            Opener = staging.Opener,
            IRA_Investment_Dollar = staging.IRA_Investment_Dollar,
            Cash_Investment_Dollar = staging.Cash_Investment_Dollar,
            Deal_Type = staging.Deal_Type,
            Transfer_Type = staging.Transfer_Type,
            "TO_Date" = COALESCE(
                CASE 
                    WHEN NULLIF(staging."TO_Date", '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging."TO_Date", '')::TIMESTAMP 
                    ELSE NULL 
                END,
                public.Lead."TO_Date"
            ),
            SF_Lead_ID = staging.SF_Lead_ID,
            Velocify_ID = staging.Velocify_ID,
            Original_Broker = staging.Original_Broker,
            SF_Lead_Owner = staging.SF_Lead_Owner,
            Junior_Broker = staging.Junior_Broker,
            Last_Activity = COALESCE(
                CASE 
                    WHEN NULLIF(staging.Last_Activity, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.Last_Activity, '')::TIMESTAMP 
                    ELSE NULL 
                END,
                public.Lead.Last_Activity
            ),
            Intellect_Client_ID = staging.Intellect_Client_ID,
            Intellect_Broker = staging.Intellect_Broker,
            First_Name = staging.First_Name,
            Last_Name = staging.Last_Name,
            Home_Phone = staging.Home_Phone,
            Work_Phone = staging.Work_Phone,
            Mobile_Phone = staging.Mobile_Phone,
            Email = staging.Email,
            Secondary_Email = staging.Secondary_Email,
            Address = staging.Address,
            City = staging.City,
            State = staging.State,
            Zip_Postal_Code = staging.Zip_Postal_Code,
            Source_Code = staging.Source_Code,
            SubID = staging.SubID
        FROM public.staging_lead AS staging
        WHERE public.Lead.Lead_ID = NULLIF(staging.Lead_ID, '')::INT;


        """

        execute_redshift_query(update_query)

        insert_query = f"""
        BEGIN;
        INSERT INTO public.Lead (
                Lead_ID, Source, Lead_Status, Lead_Score, Milestone, Broker_Name, "Group", 
                Date_Added, Last_Action, First_Contact_Attempt_Date, Action_Count, Total_Contact_Attempts, 
                Last_Action_Date, First_Assignment_Distribution_Date, First_Assignment_Distribution_User, 
                Lead_Source_Group, Creative, Broker, Opener, IRA_Investment_Dollar, Cash_Investment_Dollar, 
                Deal_Type, Transfer_Type, "TO_Date", SF_Lead_ID, Velocify_ID, Original_Broker, SF_Lead_Owner, 
                Junior_Broker, Last_Activity, Intellect_Client_ID, Intellect_Broker, First_Name, Last_Name, 
                Home_Phone, Work_Phone, Mobile_Phone, Email, Secondary_Email, Address, City, State, 
                Zip_Postal_Code, Source_Code, SubID
            )
            SELECT DISTINCT
                NULLIF(staging.Lead_ID, '')::INT AS Lead_ID,
                staging.Source,
                staging.Lead_Status,
                staging.Lead_Score,
                staging.Milestone,
                staging.Broker_Name,
                staging."Group",
                CASE 
                    WHEN NULLIF(staging.Date_Added, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.Date_Added, '')::TIMESTAMP
                    ELSE NULL 
                END AS Date_Added,
                staging.Last_Action,
                CASE 
                    WHEN NULLIF(staging.First_Contact_Attempt_Date, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.First_Contact_Attempt_Date, '')::TIMESTAMP
                    ELSE NULL 
                END AS First_Contact_Attempt_Date,
                NULLIF(staging.Action_Count, '')::INT AS Action_Count,
                NULLIF(staging.Total_Contact_Attempts, '')::INT AS Total_Contact_Attempts,
                CASE 
                    WHEN NULLIF(staging.Last_Action_Date, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.Last_Action_Date, '')::TIMESTAMP
                    ELSE NULL 
                END AS Last_Action_Date,
                CASE 
                    WHEN NULLIF(staging.First_Assignment_Distribution_Date, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.First_Assignment_Distribution_Date, '')::TIMESTAMP
                    ELSE NULL 
                END AS First_Assignment_Distribution_Date,
                staging.First_Assignment_Distribution_User,
                staging.Lead_Source_Group,
                staging.Creative,
                staging.Broker,
                staging.Opener,
                staging.IRA_Investment_Dollar,
                staging.Cash_Investment_Dollar,
                staging.Deal_Type,
                staging.Transfer_Type,
                CASE 
                    WHEN NULLIF(staging."TO_Date", '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging."TO_Date", '')::TIMESTAMP
                    ELSE NULL 
                END AS "TO_Date",
                staging.SF_Lead_ID,
                staging.Velocify_ID,
                staging.Original_Broker,
                staging.SF_Lead_Owner,
                staging.Junior_Broker,
                CASE 
                    WHEN NULLIF(staging.Last_Activity, '') ~ '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$' 
                    THEN NULLIF(staging.Last_Activity, '')::TIMESTAMP
                    ELSE NULL 
                END AS Last_Activity,
                staging.Intellect_Client_ID,
                staging.Intellect_Broker,
                staging.First_Name,
                staging.Last_Name,
                staging.Home_Phone,
                staging.Work_Phone,
                staging.Mobile_Phone,
                staging.Email,
                staging.Secondary_Email,
                staging.Address,
                staging.City,
                staging.State,
                staging.Zip_Postal_Code,
                staging.Source_Code,
                staging.SubID
            FROM public.staging_lead AS staging
            WHERE NULLIF(staging.Lead_ID, '')::INT IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 
                FROM public.Lead 
                WHERE public.Lead.Lead_ID = NULLIF(staging.Lead_ID, '')::INT
            );
        TRUNCATE TABLE {table_name};

        COMMIT;

        """
        # logger.info(f"InsertQuery: {insert_query}")
        execute_redshift_query(insert_query)
        logger.info("Data copied successfully to Redshift.")
        after_count = get_table_row_count()
        logger.info(f"Row count after insert: {after_count}")
        # Calculate inserted rows
        inserted_rows = after_count - before_count
        logger.info(f"Rows inserted into public.lead: {inserted_rows}")
        return inserted_rows
       
    except Exception as e:
        logger.info(f"Error copying data to Redshift: {e}")
        raise

def get_table_row_count():
    try:
        # Execute the query
        query = "SELECT COUNT(*) FROM public.lead;"
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

def send_email(subject, body):
    try:
        recipient_emails_env = os.environ.get('SES_RECIPIENT_EMAILS', '')
        # Split the emails into a list
        recepient_emails = [email.strip() for email in recipient_emails_env.split(',') if email.strip()]
        # recepient_emails=["sravya.v@quiddityinfotech.com","sravya.vemulapally@emeraldkey.com"]
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
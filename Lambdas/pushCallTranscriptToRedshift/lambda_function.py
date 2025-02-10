import os
import json
import boto3
import uuid
from botocore.client import Config
import logging

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

def lambda_handler(event, context):
    try:
        # event = {
        #     'bucket_name': "raw-velocify-callrecording-transcriptions",
        #     'file_key': "0000287D-A7E1-4B37-B5B6-690344370ED9.json"
        # }
        bucket_name = os.environ.get('bucket_name')
        for record in event.get("Records", []):
            file_key = record['s3']['object']['key']
            # Read the JSON file from S3
            json_data = read_json_from_s3(bucket_name, file_key)

            # Extract data from the JSON
            transcript_id = json_data['transcript_id']
            call_id = json_data['call_id']
            transcript_url = json_data['transcript_url']

            # Construct SQL queries
            delete_sql_query = f"""
            DELETE FROM public.Transcript WHERE Call_ID = '{call_id}';
            """
            insert_sql_query = f"""
            INSERT INTO public.Transcript (Transcript_ID, Call_ID, Transcript_Url)
            VALUES ('{transcript_id}', '{call_id}', '{transcript_url}');
            """

            # Execute the queries
            execute_redshift_query(delete_sql_query)
            execute_redshift_query(insert_sql_query)

            logger.info("Data successfully inserted/updated in Redshift.")
            return {
                'statusCode': 200,
                'body': 'Data processed successfully.'
            }

        except Exception as e:
            logger.info(f"Error: {str(e)}")
            return {
                'statusCode': 500,
                'body': f"Failed to process data: {str(e)}"
            }

def read_json_from_s3(bucket_name, file_key):
    """
    Reads a JSON file from the specified S3 bucket and key.
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        logger.info(f"Error reading JSON from S3: {str(e)}")
        raise

def execute_redshift_query(query_str):
    """
    Executes a query on the Redshift cluster.
    """
    logger.info(f"Executing query: {query_str}")
    try:
        result = client_redshift.execute_statement(
            Database=os.environ.get('database_name'),
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        logger.info(f"Query executed successfully: {result}")
        return result
    except Exception as e:
        logger.info(f"Error executing query: {str(e)}")
        raise

import os
import json
import boto3
import uuid
from botocore.client import Config

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
        event = {
            'bucket_name': "raw-velocify-callrecording-transcriptions",
            'file_key': "0000287D-A7E1-4B37-B5B6-690344370ED9.json"
        }

        # Extract bucket and key from the event
        bucket_name = event['bucket_name']
        file_key = event['file_key']

        # Read the JSON file from S3
        json_data = read_json_from_s3(bucket_name, file_key)

        # Extract data from the JSON
        call_id = json_data['call_id']
        transcript = json_data['transcription']
        talk_time_percentages = json_data['talk_time_percentages']

        talk_time_a = int(talk_time_percentages.get('A', 0))
        talk_time_b = int(talk_time_percentages.get('B', 0))
        talk_time_c = int(talk_time_percentages.get('C', 0))  # Default 0 if not present

        # Generate a unique Transcript_ID
        transcript_id = str(uuid.uuid4())

        # Construct SQL queries
        delete_sql_query = f"""
        DELETE FROM public.Transcript WHERE Call_ID = '{call_id}';
        """
        insert_sql_query = f"""
        INSERT INTO public.Transcript (Transcript_ID, Call_ID, Transcript, TalkTime_Percentage_A, TalkTime_Percentage_B, TalkTime_Percentage_C)
        VALUES ('{transcript_id}', '{call_id}', $$ {transcript} $$, {talk_time_a}, {talk_time_b}, {talk_time_c});
        """

        # Execute the queries
        execute_redshift_query(delete_sql_query)
        execute_redshift_query(insert_sql_query)

        print("Data successfully inserted/updated in Redshift.")
        return {
            'statusCode': 200,
            'body': 'Data processed successfully.'
        }

    except Exception as e:
        print(f"Error: {str(e)}")
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
        print(f"Error reading JSON from S3: {str(e)}")
        raise

def execute_redshift_query(query_str):
    """
    Executes a query on the Redshift cluster.
    """
    print(f"Executing query: {query_str}")
    try:
        result = client_redshift.execute_statement(
            Database='dev',
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        print(f"Query executed successfully: {result}")
        return result
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        raise

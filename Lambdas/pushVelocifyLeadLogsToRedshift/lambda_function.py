import os
import json
import boto3
import botocore
import botocore.session as bc
from botocore.client import Config
import time
import io
import csv

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

# Initializing Redshift's client   
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)

def lambda_handler(event, context):
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

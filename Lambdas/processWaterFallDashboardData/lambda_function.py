import os
import json
import boto3
import time
import logging

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize boto3 clients
s3_client = boto3.client('s3')
session = boto3.session.Session()
region = session.region_name
redshift_client = session.client('redshift-data')

# Secrets Manager client
secret_name = os.environ['SecretId']
secrets_client = boto3.client('secretsmanager', region_name=region)
get_secret_value_response = secrets_client.get_secret_value(SecretId=secret_name)
secret_arn = get_secret_value_response['ARN']
secret_json = json.loads(get_secret_value_response['SecretString'])
cluster_id = secret_json['dbClusterIdentifier']

def lambda_handler(event, context):
    try:
        create_or_replace_view()
        return {
            'statusCode': 200,
            'body': json.dumps('Lead Funnel View created successfully!')
        }
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

def create_or_replace_view():
    """
    Submit the CREATE OR REPLACE VIEW statement to Redshift using boto3 redshift-data client.
    """
    create_view_sql ="""
-- Create summary view
CREATE OR REPLACE VIEW public.lead_funnel_summary AS
SELECT
    COUNT(DISTINCT c.lead_id) AS total_leads,
    COUNT(DISTINCT CASE WHEN c.talk_time > 60 THEN c.lead_id END) AS meaningful_convo,
    COUNT(DISTINCT CASE WHEN c.call_type ILIKE '%Transfer%' THEN c.lead_id END) AS transfer_calls,
    COUNT(DISTINCT CASE WHEN ll.status ILIKE '%out%' THEN ll.lead_id END) AS caa_out,
    COUNT(DISTINCT CASE WHEN ll.status ILIKE '%in%' THEN ll.lead_id END) AS caa_in,
    COUNT(DISTINCT CASE WHEN ll.log_result = 'Client' THEN ll.lead_id END) AS client
FROM public.call c
LEFT JOIN public.lead_log ll ON c.lead_id = ll.lead_id;

-- Create waterfall view
CREATE OR REPLACE VIEW public.lead_funnel_waterfall AS
SELECT 'Total Leads (Start)' AS stage, 
       total_leads AS value, 
       'absolute' AS measure
FROM public.lead_funnel_summary
UNION
SELECT 'Unsuccessful Leads',
       -(total_leads - meaningful_convo - transfer_calls - caa_out - caa_in - client),
       'relative'
FROM public.lead_funnel_summary
UNION
SELECT 'Meaningful Convo', -meaningful_convo, 'relative' FROM public.lead_funnel_summary
UNION
SELECT 'Transfer Call-Type', -transfer_calls, 'relative' FROM public.lead_funnel_summary
UNION
SELECT 'CAA-Out', -caa_out, 'relative' FROM public.lead_funnel_summary
UNION
SELECT 'CAA-In', -caa_in, 'relative' FROM public.lead_funnel_summary
UNION
SELECT 'Client', -client, 'relative' FROM public.lead_funnel_summary;
"""

    response = redshift_client.execute_statement(
        ClusterIdentifier=cluster_id,
        Database=os.environ.get('database_name'),
        SecretArn=secret_arn,
        Sql=create_view_sql
    )
    statement_id = response['Id']
    logger.info(f"View creation query submitted. Statement ID: {statement_id}")

    # Wait until the query is completed
    while True:
        status_response = redshift_client.describe_statement(Id=statement_id)
        status = status_response['Status']
        if status in ['FINISHED', 'FAILED', 'ABORTED']:
            break
        time.sleep(2)

    if status != 'FINISHED':
        raise Exception(f"Failed to create view: {status_response.get('Error', 'Unknown error')}")

    logger.info("View created successfully.")


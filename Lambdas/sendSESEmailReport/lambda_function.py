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

def lambda_handler(event, context):
    query = f"""
        SELECT 
            date,
            SUM(totalRecords) AS total_records,
            SUM(failed) AS total_failed
        FROM errorLog
        WHERE date >= CURRENT_DATE - INTERVAL '7 day'
        GROUP BY date
        ORDER BY date;
        """
    query_result = execute_redshift_query(query)
    # print(f"query_result:{query_result}")
    subject = "Error Log Report - Last 7 Days"
    html_body = format_query_result_as_html_table(query_result)
    send_email(subject, html_body)
    return {
        'statusCode': 200,
        'body': "Process Err Log report and email sent"
    }

def execute_redshift_query(query_str):
    """
    Execute a query in the Redshift cluster and return results as JSON.
    """
    try:
        response = client_redshift.execute_statement(
            Database=database_name,
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        statement_id = response['Id']
        logger.info(f"Query submitted. Statement ID: {statement_id}")

        # Wait until the statement is finished
        while True:
            status_response = client_redshift.describe_statement(Id=statement_id)
            status = status_response['Status']
            if status in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            logger.info(f"Waiting for query completion... Current status: {status}")
            time.sleep(1)

        if status != 'FINISHED':
            raise Exception(f"Query failed or aborted: {status_response.get('Error', 'No error message')}")

        # Fetch results
        result_response = client_redshift.get_statement_result(Id=statement_id)
        records = result_response['Records']
        column_info = result_response['ColumnMetadata']
        column_names = [col['name'] for col in column_info]

        # Format results into JSON
        result_json = []
        for row in records:
            record = {}
            for col_name, value in zip(column_names, row):
                # Redshift returns each value as a dict like {'stringValue': '...'}
                val = next(iter(value.values()))
                record[col_name] = val
            result_json.append(record)

        return result_json

    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise

def format_query_result_as_html_table(query_result):
    html = """
    <html>
    <head>
        <style>
            table {
                border-collapse: collapse;
                width: 60%;
            }
            th, td {
                border: 1px solid #dddddd;
                text-align: center;
                padding: 8px;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h3>Error Log Summary (Last 7 Days)</h3>
        <table>
            <tr>
                <th>Date</th>
                <th>Total Records</th>
                <th>Failed Records</th>
            </tr>
    """

    for row in query_result:
        html += f"""
            <tr>
                <td>{row['date']}</td>
                <td>{row['total_records']}</td>
                <td>{row['total_failed']}</td>
            </tr>
        """
    html += """
        </table>
    </body>
    </html>
    """
    return html

def send_email(subject, html_body):
    try:
        recipient_emails_env = os.environ.get('SES_RECIPIENT_EMAILS', '')
        recepient_emails = [email.strip() for email in recipient_emails_env.split(',') if email.strip()]
        print(f"recepient_emails:{recepient_emails}")
        print(f"source : {os.environ['SES_SOURCE_EMAIL']}")
        ses_client.send_email(
            Source=os.environ['SES_SOURCE_EMAIL'],
            Destination={'ToAddresses': recepient_emails},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_body},
                    'Text': {'Data': "Please view the email in HTML format to see the error log table."}
                }
            }
        )
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise

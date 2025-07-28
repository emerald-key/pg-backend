import os
import json
import boto3
import io
import csv
from botocore.client import Config
import time
import logging
from datetime import datetime
# import pandas as pd
from datetime import timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
ses_client = boto3.client('ses')
session = boto3.session.Session()
region = session.region_name
client_secretsmanager = session.client(service_name='secretsmanager', region_name=region)
config = Config(connect_timeout=5, read_timeout=5)
client_redshift = session.client("redshift-data", config=config)

secret_name = os.environ['SecretId']
secret_json = json.loads(client_secretsmanager.get_secret_value(SecretId=secret_name)['SecretString'])
secret_arn = client_secretsmanager.get_secret_value(SecretId=secret_name)['ARN']
cluster_id = secret_json['dbClusterIdentifier']
database_name = secret_json['dbName']

def lambda_handler(event, context):
    try:
        send_redflags_email_report()
        return {'statusCode': 200, 'body': json.dumps('redflags report sent successfully!')}
    except Exception as e:
        logger.error(str(e))
        err_subject = "Error sending redflags report"
        err_body = f"""
        Error : {str(e)}
        """
        send_email(err_subject, err_body)
        return {'statusCode': 500, 'body': json.dumps(f"Error: {str(e)}")}
def send_redflags_email_report():
    yesterday = (datetime.utcnow() - timedelta(days=1)).date()
    query = f"""
        SELECT ID, Lead_ID, Lead_Name, Call_ID, Broker_Name, Date,
               Original_Score_Or_Type, New_Score_Or_Type, Reason, Created_Datetime
        FROM redFlagsDataTest
        WHERE CAST(Created_Datetime AS DATE) = '{yesterday}';
    """
    records = execute_redshift_query_and_fetch_all(query)

    if not records:
        send_email("Redflags report", f"No red flags found for {yesterday}")
        return

    # Group records by Reason
    grouped = {}
    for row in records:
        # If row is a tuple, convert it using column names
        if isinstance(row, dict):
            reason = row.get("reason") or "Unknown"
        else:
            # fallback: assume column index for Reason is 8
            reason = row[8] if len(row) > 8 else "Unknown"

        grouped.setdefault(reason, []).append(row)

    # Build HTML
    html = f"<h2>Red Flags Report for {yesterday}</h2>"
    for reason, rows in grouped.items():
        html += f"<h3>Reason: {reason}</h3>"
        html += "<table border='1' cellspacing='0' cellpadding='4'><tr>"
        headers = list(rows[0].keys()) if isinstance(rows[0], dict) else [
            "ID", "Lead_ID", "Lead_Name", "Call_ID", "Broker_Name", "Date",
            "Original_Score_Or_Type", "New_Score_Or_Type", "Reason", "Created_Datetime"
        ]
        for header in headers:
            html += f"<th>{header}</th>"
        html += "</tr>"
        for row in rows:
            html += "<tr>"
            for header in headers:
                value = row.get(header, '') if isinstance(row, dict) else row[headers.index(header)]
                html += f"<td>{value}</td>"
            html += "</tr>"
        html += "</table><br>"

    send_email_html(f"Redflags Report - {yesterday}", html)


def execute_redshift_query_and_fetch_all(query):
    response = client_redshift.execute_statement(
        Database=database_name,
        SecretArn=secret_arn,
        Sql=query,
        ClusterIdentifier=cluster_id
    )
    statement_id = response['Id']
    logger.info(f"Statement ID: {statement_id}")

    while True:
        status = client_redshift.describe_statement(Id=statement_id)['Status']
        if status in ['FINISHED', 'FAILED', 'ABORTED']:
            break
        time.sleep(2)

    if status != 'FINISHED':
        raise Exception(f"Redshift query failed with status: {status}")

    result = client_redshift.get_statement_result(Id=statement_id)
    columns = [col['name'] for col in result['ColumnMetadata']]
    
    records = []
    for row in result['Records']:
        record = {}
        for col, val in zip(columns, row):
            record[col] = list(val.values())[0] if val else None
        records.append(record)

    return records

def send_email_html(subject, html_body):
    recipient_emails_env = os.environ.get('SES_RECIPIENT_EMAILS', '')
    recepient_emails = [email.strip() for email in recipient_emails_env.split(',') if email.strip()]
    # recepient_emails = ['sravya.v@quiddityinfotech.com','sravya.vemulapally@emeraldkey.com']
    ses_client.send_email(
        Source=os.environ['SES_SOURCE_EMAIL'],
        Destination={'ToAddresses': recepient_emails},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Html': {'Data': html_body},
                'Text': {'Data': 'Your email client does not support HTML.'}
            }
        }
    )

def send_email(subject, text_body):
    recipient_emails_env = os.environ.get('SES_RECIPIENT_EMAILS', '')
    # recepient_emails = [email.strip() for email in recipient_emails_env.split(',') if email.strip()]
    recepient_emails = ['sravya.v@quiddityinfotech.com','sravya.vemulapally@emeraldkey.com']
    ses_client.send_email(
        Source=os.environ['SES_SOURCE_EMAIL'],
        Destination={'ToAddresses': recepient_emails},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': text_body}
            }
        }
    )

def execute_redshift_query(query_str, return_statement_id=False):
    try:
        response = client_redshift.execute_statement(
            Database=database_name,
            SecretArn=secret_arn,
            Sql=query_str,
            ClusterIdentifier=cluster_id
        )
        statement_id = response['Id']
        logger.info(f"Query submitted. Statement ID: {statement_id}")

        while True:
            query_status = client_redshift.describe_statement(Id=statement_id)
            status = query_status['Status']
            if status in ['FINISHED', 'FAILED', 'ABORTED']:
                break
            logger.info(f"Waiting for query to complete... Current status: {status}")
            time.sleep(2)

        if status == 'FINISHED':
            logger.info("Query executed successfully.")
            return (query_status, statement_id) if return_statement_id else query_status
        else:
            raise Exception(f"Query failed. Status: {status}, Error: {query_status.get('Error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise
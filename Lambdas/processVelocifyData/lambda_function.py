import boto3
import csv
import io
import requests
import time
import json
import os
import logging
import re
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone,timedelta

dynamodb = boto3.resource('dynamodb')
recording_index_table = dynamodb.Table('velocify-recordings')
processing_times_table = dynamodb.Table('processing_times')

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client and Lambda client
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    # return
    logger.info(event)

    target_bucket_name = os.environ.get('target_bucket_name')
    source_bucket_name = os.environ.get('source_bucket_name')
    lambda_status = event.get("lambdaStatus", "s3Triggered")

    logger.info(f"lambda_status: {lambda_status}")

    if lambda_status == "invokedSelf":
        logger.info("Invoked from self")
        file_key = event.get("file_key")
        start_index = event.get("start_index")
    else:
        logger.info("Triggered from S3")
        file_key = event['Records'][0]['s3']['object']['key']
        start_index = 0

        # Skip processing if already processed
        if file_key.startswith('processed/') or file_key.startswith('cleaned/'):
            logger.info(f"Skipping file: {file_key}")
            return {
                'statusCode': 200,
                'body': f"Skipped processing for file: {file_key}"
            }
        # Invoke redshift lambda
        invoke_redshift_lambda(file_key, source_bucket_name)
        # Preprocess and create cleaned file
        file_key = preprocess_csv(file_key, source_bucket_name)
        if not file_key:
            return {
                'statusCode': 500,
                'body': 'Failed to preprocess CSV file'
            }

    logger.info(f"Processing file: {file_key}")

    # Start tracking time
    start_time = time.time()
    lambda_timeout_buffer = 840  # 14 minutes buffer

    try:
        # Get the cleaned CSV file from S3
        response = s3_client.get_object(Bucket=source_bucket_name, Key=file_key)
        file_content = response['Body'].read().decode('utf-8')

        # Use io.StringIO to treat the string content as a file
        csv_file = io.StringIO(file_content)
        csv_reader = list(csv.DictReader(csv_file))  # Read all rows into a list
        # Derive velocify_date from the first row
        if csv_reader and csv_reader[0].get("Time"):
            try:
                velocify_date = csv_reader[0]["Time"].split(" ")[0]
            except Exception:
                velocify_date = "unknown-date"
        else:
            velocify_date = "unknown-date"
        expiry_days = 30
        expdate = int((datetime.now(timezone.utc) + timedelta(days=expiry_days)).timestamp())
        for index, row in enumerate(csv_reader[start_index:], start=start_index):
            # Check remaining time
            elapsed_time = time.time() - start_time
            if elapsed_time >= lambda_timeout_buffer:
                if velocify_date != "unknown-date":
                    update_processing_time(velocify_date)
                logger.info(f"Timeout approaching. Reinvoking Lambda at row {index}")
                invoke_self(context, file_key, index)
                return {
                    'statusCode': 202,
                    'body': f'Reinvoked Lambda at row {index}'
                }

            # Process the row
            recording_url = row.get("Recording")
            if recording_url and recording_url.startswith("http"):
                call_id = row.get("Call Id", "unknown")
                call_type = row.get("Origin", "unknown")
                conversation_time = row.get("Conversation Duration (hrs:min:sec)", "unknown")
                conversation_time_in_secs = convert_to_seconds(conversation_time, call_id)
                call_duration = row.get("Call Duration (hrs:min:sec)", "unknown")
                call_duration_in_secs = convert_to_seconds(call_duration, call_id)
                timestamp = row.get("Time")
                # try:
                #     # Parse velocify_date from Time field (e.g., 04/30/2025 22:41:33 → 04/30/2025)
                #     velocify_date = timestamp.split(" ")[0] if timestamp else "unknown-date"
                # except Exception as e:
                #     logger.warning(f"Failed to parse date from Time: {timestamp}")
                #     velocify_date = "unknown-date"

                target_file_key = f"{call_id}.mp3"
                cookies = {
                    "ASP.NET_SessionId": "0xtve3frfxdhsyzugzzzyk2b",  # replace with actual session ID
                    "AWSALB": "MyD6u+CofUOATrlEvskIhRVUnHsqFD+4xkBi3/02+HDjXXKZaf9m1B08SCusTq+HRi9bYbIAXJ+pzVvKdeh/pquhNmARyKchqgnA+kB+H032U0pw0SUI9eOJLE71",
                    "AWSALBCORS": "MyD6u+CofUOATrlEvskIhRVUnHsqFD+4xkBi3/02+HDjXXKZaf9m1B08SCusTq+HRi9bYbIAXJ+pzVvKdeh/pquhNmARyKchqgnA+kB+H032U0pw0SUI9eOJLE71",
                    "LastLoginHostname": "lm.prod.velocify.com",
                    "searchTypeCookie": "0"
                }
                headers = {
                    "User-Agent": "Mozilla/5.0",
                }
                # Download and store the recording in S3
                recording_response = requests.get(recording_url, headers=headers, cookies=cookies)
                if recording_response.status_code == 200:
                    s3_client.put_object(
                        Bucket=target_bucket_name,
                        Key=target_file_key,
                        Body=recording_response.content
                    )
                    try:
                        recording_index_table.put_item(
                            Item={
                                'velocify_date': velocify_date,
                                'call_id': call_id,
                                'origin': call_type,
                                'conversation_time_in_secs': conversation_time_in_secs,
                                'call_duration_in_secs':call_duration_in_secs,
                                's3_key': target_file_key,
                                'created_at': datetime.now(timezone.utc).isoformat(),
                                'expdate':expdate
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to write to DynamoDB for {call_id}: {e}")
                else:
                    logger.info(f"Failed to download recording: {recording_url}, Status Code: {recording_response.status_code}")

        logger.info(f"Recordings processed and saved successfully")
        invoke_verification_lambda(file_key, source_bucket_name)
        return {
            'statusCode': 200,
            'body': 'Recordings processed and saved successfully!'
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f"Failed to process file: {str(e)}"
        }


def convert_to_seconds(time_str, call_id):
    try:
        # print(f"Processing Call_ID: {call_id}, Time String: {time_str}")

        if not time_str or time_str in ['N/A', '(N/A)', '']:
            print(f"Skipping invalid time format for Call_ID: {call_id}")
            return None

        parts = time_str.split(':')
        if len(parts) != 3:
            print(f"Incorrect time format for Call_ID: {call_id} -> {time_str}")
            return None

        if any(not part.isdigit() for part in parts):
            print(f"Non-integer value found in time parts for Call_ID: {call_id} -> {parts}")
            return None

        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds

    except ValueError:
        print(f"Error converting time for Call_ID: {call_id}, Time String: {time_str}")
        return None


def preprocess_csv(file_key, source_bucket):
    try:
        logger.info(f"Preprocessing CSV: {file_key}")
        response = s3_client.get_object(Bucket=source_bucket, Key=file_key)
        file_content = response['Body'].read().decode('utf-8')

        csv_file = io.StringIO(file_content)
        csv_reader = list(csv.DictReader(csv_file))

        seen_recordings = set()
        cleaned_rows = []
        for row in csv_reader:
            recording_url = row.get("Recording")
            if recording_url and recording_url not in seen_recordings:
                seen_recordings.add(recording_url)
                cleaned_rows.append(row)

        logger.info(f"Removed {len(csv_reader) - len(cleaned_rows)} duplicate rows")

        cleaned_file_key = f"cleaned/{file_key}"
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=csv_reader[0].keys())
        writer.writeheader()
        writer.writerows(cleaned_rows)

        s3_client.put_object(
            Bucket=source_bucket,
            Key=cleaned_file_key,
            Body=output.getvalue()
        )

        logger.info(f"Cleaned file saved to {cleaned_file_key}")
        return cleaned_file_key

    except Exception as e:
        logger.error(f"Failed to preprocess CSV: {e}")
        return None


def invoke_self(context, file_key, start_index):
    try:
        lambda_client.invoke(
            FunctionName=context.function_name,
            InvocationType='Event',
            Payload=json.dumps({
                "file_key": file_key,
                "start_index": start_index,
                "lambdaStatus": "invokedSelf"
            })
        )
        logger.info(f"Reinvoked Lambda at row {start_index}")

    except Exception as e:
        logger.error(f"Failed to reinvoke Lambda: {e}")


def invoke_redshift_lambda(file_key, bucket_name):
    lambda_client.invoke(
        FunctionName="pushVelocifyCallLogsToRedshift",
        InvocationType='Event',
        Payload=json.dumps({
            "file_key": file_key,
            "bucket_name": bucket_name
        })
    )
def invoke_verification_lambda(file_key, bucket_name):
    lambda_client.invoke(
        FunctionName="verifyVelocifyRecordings",
        InvocationType='Event',
        Payload=json.dumps({
            "file_key": file_key,
            "bucket_name": bucket_name
        })
    )

def update_processing_time(velocify_date, process_type="download_recordings", increment_minutes=15):
    logger.info(f"in update_processing_time {velocify_date}:{increment_minutes}")
    try:
        response = processing_times_table.get_item(
            Key={
                'velocify_date': velocify_date,
                'process_type': process_type
            }
        )
        if 'Item' in response:
            current_time = response['Item'].get('processed_time_in_mins', 0)
            new_time = current_time + increment_minutes
            processing_times_table.update_item(
                Key={
                    'velocify_date': velocify_date,
                    'process_type': process_type
                },
                UpdateExpression="SET processed_time_in_mins = :val",
                ExpressionAttributeValues={':val': new_time}
            )
            logger.info(f"Updated processing time: {new_time} mins for {velocify_date}")
        else:
            processing_times_table.put_item(
                Item={
                    'velocify_date': velocify_date,
                    'process_type': process_type,
                    'processed_time_in_mins': increment_minutes,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            )
            logger.info(f"Created processing time record: {increment_minutes} mins for {velocify_date}")

    except Exception as e:
        logger.error(f"Failed to update processing time: {e}")

import boto3
import csv
import io
import requests
import time
import json
import os
import logging
import re

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
    # lambda_status = "s3Triggered"
    logger.info(f"lambda_status: {lambda_status}")

    if lambda_status == "invokedSelf":
        logger.info("Invoking self")
        file_key = event.get("file_key")
        start_index = event.get("start_index")
        processed_recordings_key = event.get("processed_recordings_key")
        # Load processed recordings from S3 if key exists
        if processed_recordings_key:
            try:
                response = s3_client.get_object(Bucket=target_bucket_name, Key=processed_recordings_key)
                processed_recordings = set(json.loads(response['Body'].read().decode('utf-8')))
                logger.info(f"Loaded {len(processed_recordings)} processed recordings from {processed_recordings_key}")
            except Exception as e:
                logger.error(f"Failed to load processed recordings from S3: {e}")
                processed_recordings = set()
    else:
        logger.info("Triggered from s3")
        file_key  = event['Records'][0]['s3']['object']['key']
        start_index = 0
        processed_recordings = set()

        # Invoke redshift lambda
        invoke_redshift_lambda(file_key, source_bucket_name)
    
    # Skip processing if the file is in the "processed/" folder
    if file_key.startswith('processed/'):
        logger.info(f"Skipping file: {file_key}")
        return {
            'statusCode': 200,
            'body': f"Skipped processing for file: {file_key}"
        }
    file_base_name = re.sub(r'\.csv$', '', file_key)
    logger.info(f"Extracted file base name: {file_base_name}")
    # Start tracking time
    start_time = time.time()
    lambda_timeout_buffer = 840  # 14 minutes buffer
    # lambda_timeout_buffer = 10  # 2 minutes buffer

    logger.info(f"startIndex: {start_index}")
    logger.info(f"fileKey: {file_key}")
    
    try:
        # Get the CSV file from S3
        response = s3_client.get_object(Bucket=source_bucket_name, Key=file_key)
        file_content = response['Body'].read().decode('utf-8')

        # Use io.StringIO to treat the string content as a file
        csv_file = io.StringIO(file_content)
        csv_reader = list(csv.DictReader(csv_file))  # Read all rows into a list
        
        for index, row in enumerate(csv_reader[start_index:], start=start_index):
            # Check remaining time
            elapsed_time = time.time() - start_time
            if elapsed_time >= lambda_timeout_buffer:
                logger.info(f"Timeout approaching. Reinvoking Lambda at row {index}")
                invoke_self(context, file_key, index, processed_recordings,file_base_name)
                logger.info(f"Reinvoked Lambda at row {index}")
                return {
                    'statusCode': 202,
                    'body': f'Reinvoked Lambda at row {index}'
                }

            # Process the row
            recording_url = row.get("Recording")
            if recording_url and recording_url.startswith("http"):
                if recording_url in processed_recordings:
                    # logger.info(f"Skipping duplicate recording:{row.get("Call Id", "unknown")} - {recording_url}")
                    continue
                
                # Download the recording file
                recording_response = requests.get(recording_url)
                if recording_response.status_code == 200:
                    call_id = row.get("Call Id", "unknown")
                    target_file_key = f"{call_id}.mp3"
                    
                    # Save the recording to the target S3 bucket
                    s3_client.put_object(
                        Bucket=target_bucket_name,
                        Key=target_file_key,
                        Body=recording_response.content
                    )
                    
                    # Add to the processed set to prevent future downloads
                    processed_recordings.add(recording_url)
                else:
                    logger.info(f"Failed to download recording: {recording_url}, Status Code: {recording_response.status_code}")
        
        logger.info(f"Recordings processed and saved successfully : {len(processed_recordings)}")
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

def invoke_self(context, file_key, start_index, processed_recordings,file_base_name):
    """Reinvoke the same Lambda function."""
    try:
        print(f"processed_recordings length : {len(processed_recordings)}")
        # Load previous recordings if they exist
        s3_key = f"state/{file_base_name}/processed_recordings.json"
        logger.info(f"Saving processed recordings to {s3_key}")
        # Try to merge existing recordings from S3
        try:
            response = s3_client.get_object(Bucket=os.environ['target_bucket_name'], Key=s3_key)
            existing_recordings = set(json.loads(response['Body'].read().decode('utf-8')))
            logger.info(f"Existing recordings length: {len(existing_recordings)}")
            processed_recordings.update(existing_recordings)  # Merge sets
            logger.info(f"Combined processed recordings length: {len(processed_recordings)}")

        except Exception as e:
            logger.info(f"No previous state found or failed to load: {e}")
        
        # Save the merged recordings back to S3
        s3_client.put_object(
            Bucket=os.environ['target_bucket_name'],
            Key=s3_key,
            Body=json.dumps(list(processed_recordings))
        )

        # Invoke the Lambda with the updated S3 key
        lambda_client.invoke(
            FunctionName=context.function_name,
            InvocationType='Event',
            Payload=json.dumps({
                "file_key": file_key,
                "start_index": start_index,
                "lambdaStatus": "invokedSelf",
                "processed_recordings_key": s3_key
            })
        )
        logger.info(f"Saved {len(processed_recordings)} processed recordings to {s3_key}")

    except Exception as e:
        logger.error(f"Failed to save state to S3: {e}")



def invoke_redshift_lambda(file_key, bucket_name):
    """Invoke the redshift Lambda function."""
    lambda_client.invoke(
        FunctionName="pushVelocifyCallLogsToRedshift",
        InvocationType='Event',  # Async invocation
        Payload=json.dumps({
            "file_key": file_key,
            "bucket_name": bucket_name
        })
    )
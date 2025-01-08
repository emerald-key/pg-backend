import os
import boto3
import json
import time
import assemblyai as aai

# Initialize AssemblyAI and AWS clients
aai.settings.api_key = os.environ.get('ASSEMBLYAI_API_KEY')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Lambda Handler
def lambda_handler(event, context):
    try:
        # Extract environment variables
        source_bucket_name = os.environ.get('source_bucket_name')
        target_bucket_name = os.environ.get('target_bucket_name')

        if not source_bucket_name or not target_bucket_name:
            raise ValueError("Missing required environment variables: 'source_bucket_name' or 'target_bucket_name'.")

        # Extract state from the event
        lambda_status = event.get("lambdaStatus", "s3Triggered")
        start_index = event.get("start_index", 0)
        continuation_token = event.get("continuation_token", None)

        # Timeout buffer
        start_time = time.time()
        timeout_buffer = 840  # 14 minutes

        # List objects in the source bucket with pagination
        list_params = {"Bucket": source_bucket_name}
        if continuation_token:
            list_params["ContinuationToken"] = continuation_token
        response = s3_client.list_objects_v2(**list_params)

        objects = response.get("Contents", [])
        if not objects:
            print("No objects found in the source bucket.")
            return {
                'statusCode': 200,
                'body': 'No files to process.'
            }

        # Process each object
        for index, obj in enumerate(objects[start_index:], start=start_index):
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout_buffer:
                # Reinvoke Lambda before timeout
                print(f"Timeout approaching. Reinvoking Lambda at index {index}.")
                reinvoke_lambda(context, continuation_token=response.get("NextContinuationToken"), start_index=index)
                return {
                    'statusCode': 202,
                    'body': f'Reinvoked Lambda at index {index}.'
                }

            file_key = obj["Key"]
            call_id = os.path.splitext(os.path.basename(file_key))[0]

            # Check if the transcription result already exists in the target bucket
            target_file_key = f"{call_id}.json"
            if check_file_exists(target_bucket_name, target_file_key):
                print(f"File {target_file_key} already exists in the target bucket. Skipping.")
                continue

            # Download the audio file
            local_file_path = f"/tmp/{os.path.basename(file_key)}"
            try:
                s3_client.download_file(source_bucket_name, file_key, local_file_path)
                # print(f"Downloaded file: {file_key}")

                # Transcribe and save results
                transcription_result, talk_time_percentages = transcribe_and_calculate_talk_time(local_file_path)
                save_results_to_s3(
                    bucket_name=target_bucket_name,
                    file_name=target_file_key,
                    data={
                        "call_id": call_id,
                        "transcription": transcription_result,
                        "talk_time_percentages": talk_time_percentages
                    }
                )
            except Exception as e:
                print(f"Error processing file {file_key}: {e}")
            finally:
                # Clean up temporary files
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)

        # Check for more files to process
        if response.get("IsTruncated"):
            # print("More files to process. Reinvoking Lambda for the next batch.")
            reinvoke_lambda(context, continuation_token=response["NextContinuationToken"], start_index=0)
        else:
            print("Processing complete for all files.")

        return {
            'statusCode': 200,
            'body': 'All files processed successfully!'
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': f"Failed to process files: {e}"
        }
# Function to check if a file exists in the target bucket
def check_file_exists(bucket_name, file_key):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=file_key)
        return True
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            print(f"Error checking if file exists: {e}")
            raise

# Transcription function
def transcribe_and_calculate_talk_time(file_path):
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speaker_labels=True)

        transcript = transcriber.transcribe(file_path, config=config)

        text = []
        speaker_times = {}
        for utterance in transcript.utterances:
            text.append(f"Speaker {utterance.speaker}: {utterance.text}")
            start_time = float(utterance.start) / 1000  # ms to seconds
            end_time = float(utterance.end) / 1000
            duration = end_time - start_time
            speaker_times[utterance.speaker] = speaker_times.get(utterance.speaker, 0) + duration

        total_talk_time = sum(speaker_times.values())
        talk_time_percentages = {
            speaker: (time / total_talk_time) * 100 for speaker, time in speaker_times.items()
        }

        return " ".join(text), talk_time_percentages
    except Exception as e:
        return f"Error during transcription: {e}", {}

# Save results to S3
def save_results_to_s3(bucket_name, file_name, data):
    try:
        json_data = json.dumps(data, indent=4)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json_data,
            ContentType="application/json"
        )
        # print(f"Saved file {file_name} to bucket {bucket_name}.")
    except Exception as e:
        print(f"Error saving file to S3: {e}")
        raise

# Reinvoke Lambda function
def reinvoke_lambda(context, continuation_token=None, start_index=0):
    payload = {
        "lambdaStatus": "invokedSelf",
        "continuation_token": continuation_token,
        "start_index": start_index
    }
    lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType='Event',  # Async invocation
        Payload=json.dumps(payload)
    )
    # print("Lambda reinvoked successfully.")

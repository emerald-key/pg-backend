import os
import boto3
import assemblyai as aai
import json
import uuid

# Initialize S3 client
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Lambda handler
def lambda_handler(event, context):
    try:
        # Print the received event for debugging
        # print("Received event:", json.dumps(event, indent=2))
         # Retrieve API key from Secrets Manager
        assembly_ai_secret_name = os.environ.get('assemblyai_secret_name')
        aai.settings.api_key = get_secret(assembly_ai_secret_name)
        # Extract environment variables
        source_bucket_name = os.environ.get('source_bucket_name')
        target_bucket_name = os.environ.get('target_bucket_name')
        text_bucket_name = os.environ.get('text_bucket_name')

        if not source_bucket_name or not target_bucket_name:
            raise ValueError("Missing required environment variables: 'source_bucket_name' or 'target_bucket_name'.")

        # Iterate over each record in the event
        for record in event.get("Records", []):
            # Extract file key from the record
            file_key = record['s3']['object']['key']
            call_id = os.path.splitext(os.path.basename(file_key))[0]

            # Download the audio file to Lambda's /tmp directory
            local_file_path = f"/tmp/{os.path.basename(file_key)}"
            try:
                # print(f"Downloading {file_key} from bucket {source_bucket_name}...")
                s3_client.download_file(source_bucket_name, file_key, local_file_path)

                # Transcribe the audio file
                success, transcription_result = transcribe_recording(local_file_path)

                # Log the transcription result
                # print(f"Transcription Result for {file_key}:", transcription_result)
                if not success:
                    print(f"Transcription failed for {file_key}: {transcription_result}")
                    continue
                # Save the transcription result to the target bucket
                transcript_id = str(uuid.uuid4())
                # Save .txt transcription to the text bucket and get its URL
                text_file_key = f"{transcript_id}.txt"
                transcript_url = save_text_to_s3(
                    bucket_name=text_bucket_name,
                    file_name=text_file_key,
                    data=transcription_result
                )
                output_file_key = f"{call_id}.json"
                save_results_to_s3(
                    bucket_name=target_bucket_name,
                    file_name=output_file_key,
                    data={
                            "call_id": call_id,
                            "transcription": transcription_result,
                            "transcript_id": transcript_id,
                            "transcript_url": transcript_url
                    }
                )
            except Exception as e:
                print(f"Error processing file {file_key}: {e}")
            finally:
                # Clean up temporary files
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)

        return {
            'statusCode': 200,
            'body': 'All files processed successfully!'
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }

# Function to transcribe audio files
def transcribe_recording(file_path):
    """
    Transcribes an audio file, includes speaker diarization.

    Args:
        file_path (str): Path to the local audio file to transcribe.

    Returns:
        tuple: (bool, str): A flag indicating success, and either the transcribed text or an error message.
    """
    text = []
    try:
        # Initialize transcriber
        transcriber = aai.Transcriber()

        # Upload the file to AssemblyAI's temporary storage
        FILE_URL = file_path

        # Transcription configuration with speaker labels
        config = aai.TranscriptionConfig(speaker_labels=True)

        # Perform transcription
        transcript = transcriber.transcribe(FILE_URL, config=config)

        # Process the transcription results
        for utterance in transcript.utterances:
            text.append(f"Speaker {utterance.speaker}: {utterance.text}")

        # Return success with the transcription text
        return True, " ".join(text)

    except Exception as e:
        # Return failure with the error message
        return False, f"Error during transcription: {e}"


# Function to save transcription to s3
def save_results_to_s3(bucket_name, file_name, data):
    """
    Saves data as a JSON file in the specified S3 bucket.

    Args:
        bucket_name (str): Name of the S3 bucket.
        file_name (str): Name of the file to save (e.g., "call_id.json").
        data (dict): Data to save in the file.
    """
    try:
        # Serialize data to JSON
        json_data = json.dumps(data, indent=4)

        # Save JSON data to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=json_data,
            ContentType="application/json"
        )
        print(f"Successfully saved file {file_name} to bucket {bucket_name}")
    except Exception as e:
        print(f"Failed to save JSON file to S3: {e}")
        raise

# Save .txt transcription to S3 and return its URL
def save_text_to_s3(bucket_name, file_name, data):
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=data,
            ContentType="text/plain"
        )
        # print(f"Saved text file {file_name} to bucket {bucket_name}.")
        # Generate the S3 object URL
        region = "us-east-1"
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name}"
        return url
    except Exception as e:
        print(f"Error saving text file to S3: {e}")
        raise

def get_secret(secret_name):
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = response.get('SecretString')
        if secret:
            secret_data = json.loads(secret)
            return secret_data.get('ASSEMBLYAI_API_KEY')
        else:
            raise ValueError("SecretString is empty")
    except Exception as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        raise
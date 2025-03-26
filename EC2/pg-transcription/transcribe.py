import os
import boto3
import json
import time
import uuid
import assemblyai as aai

# Initialize AssemblyAI and AWS clients
aai.settings.api_key = "testapikey"
s3_client = boto3.client('s3')

# Process all files in the source bucket
def process_files():
    try:
        # Extract environment variables
        source_bucket_name = "raw-velocify-callrecordings"
        target_bucket_name = "raw-velocify-callrecording-transcriptions"
        text_bucket_name = "final-velocify-callrecording-transcriptions"

        if not source_bucket_name or not target_bucket_name:
            raise ValueError("Missing required environment variables: 'source_bucket_name' or 'target_bucket_name'.")

        # List objects in the source bucket with pagination
        continuation_token = None
        while True:
            list_params = {"Bucket": source_bucket_name}
            if continuation_token:
                list_params["ContinuationToken"] = continuation_token

            response = s3_client.list_objects_v2(**list_params)
            objects = response.get("Contents", [])

            if not objects:
                print("No objects found in the source bucket.")
                break

            for obj in objects:
                file_key = obj["Key"]
                call_id = os.path.splitext(os.path.basename(file_key))[0]

                # Check if the transcription result already exists in the target bucket
                target_file_key = f"{call_id}.json"
                if check_file_exists(target_bucket_name, target_file_key):
                    # print(f"File {target_file_key} already exists in the target bucket. Skipping.")
                    continue

                # Download the audio file
                local_file_path = f"/tmp/{os.path.basename(file_key)}"
                try:
                    s3_client.download_file(source_bucket_name, file_key, local_file_path)

                    # Transcribe and save results
                    success, transcription_result = transcribe_recording(local_file_path)
                    if not success:
                        print(f"Transcription failed for {file_key}: {transcription_result}")
                        continue

                    # Generate a unique transcript_id
                    transcript_id = str(uuid.uuid4())

                    # Save .txt transcription to the text bucket and get its URL
                    text_file_key = f"{transcript_id}.txt"
                    transcript_url = save_text_to_s3(
                        bucket_name=text_bucket_name,
                        file_name=text_file_key,
                        data=transcription_result
                    )

                    # Save JSON metadata to the target bucket
                    save_results_to_s3(
                        bucket_name=target_bucket_name,
                        file_name=target_file_key,
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

            # Check if there are more files to process
            if response.get("IsTruncated"):
                continuation_token = response["NextContinuationToken"]
            else:
                print("Processing complete for all files.")
                break

    except Exception as e:
        print(f"Error: {e}")

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
        print(f"Saved file {file_name} to bucket {bucket_name}.")
    except Exception as e:
        print(f"Error saving file to S3: {e}")
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

if __name__ == "__main__":
    process_files()

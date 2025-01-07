import os
import boto3
import assemblyai as aai
import json

aai.settings.api_key = os.environ.get('ASSEMBLYAI_API_KEY')
# Initialize S3 client
s3_client = boto3.client('s3')

# Lambda handler
def lambda_handler(event, context):
    try:
        # Extract bucket and file key from the event
        source_bucket_name = os.environ.get('source_bucket_name')
        target_bucket_name = os.environ.get('target_bucket_name')
        file_key = "0000FFA3-4093-45C4-9F7C-F4D839E6A708.mp3"
        call_id = os.path.splitext(os.path.basename(file_key))[0]

        # Download the audio file to Lambda's /tmp directory
        local_file_path = f"/tmp/{os.path.basename(file_key)}"
        s3_client.download_file(source_bucket_name, file_key, local_file_path)

        # Transcribe the audio file and calculate talk time percentages
        transcription_result, talk_time_percentages = transcribe_and_calculate_talk_time(local_file_path)

        # Log the transcription and talk time results
        print("Transcription Result:", transcription_result)
        print("Talk Time Percentages:", talk_time_percentages)

        output_file_key = f"{os.path.splitext(file_key)[0]}.json"
        try:
            save_results_to_s3(
                bucket_name=target_bucket_name,
                file_name=f"{call_id}.json",
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


        return {
            'statusCode': 200,
            'body': {
                'transcription': transcription_result,
                'talk_time_percentages': talk_time_percentages,
                'result_file': output_file_key
            }
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': str(e)
        }

# Function to transcribe audio files and calculate talk time percentage
def transcribe_and_calculate_talk_time(file_path):
    """
    Transcribes an audio file, includes speaker diarization, 
    and calculates the talk time percentage for each speaker.

    Args:
        file_path (str): Path to the local audio file to transcribe.

    Returns:
        tuple: Transcribed text with speaker labels (str) and talk time percentages (dict) or an error message.
    """
    text = []
    speaker_times = {}
    try:
        # Initialize transcriber
        transcriber = aai.Transcriber()

        # Upload the file to AssemblyAI's temporary storage
        FILE_URL = file_path

        # Transcription configuration with speaker labels
        config = aai.TranscriptionConfig(speaker_labels=True)

        # Perform transcription
        transcript = transcriber.transcribe(
            FILE_URL,
            config=config
        )

        # Process the transcription results
        for utterance in transcript.utterances:
            # Append transcription text
            text.append(f"Speaker {utterance.speaker}: {utterance.text}")
            
            # Calculate talk time for each speaker
            start_time = float(utterance.start) / 1000  # Convert milliseconds to seconds
            end_time = float(utterance.end) / 1000
            duration = end_time - start_time
            speaker_times[utterance.speaker] = speaker_times.get(utterance.speaker, 0) + duration

        # Calculate total talk time and percentages
        total_talk_time = sum(speaker_times.values())
        talk_time_percentages = {
            speaker: (time / total_talk_time) * 100 for speaker, time in speaker_times.items()
        }

        return " ".join(text), talk_time_percentages
    
    except Exception as e:
        return f"Error during transcription: {e}", {}

# Function to save transcription and talk time percentages to S3
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
# **pg-transcription** 

This directory contains the `transcribe.py` script, which uses Assembly AI to transcribe audio recordings from an S3 bucket. The transcriptions are stored in two S3 buckets: one for the structured transcription data and another for the plain text file format of the transcript.

## **Directory Structure:**
```
pg-transcription/
  └── transcribe.py          # Main script to transcribe recordings using Assembly AI
```

## **Overview:**

The `transcribe.py` script is designed to:

1. **Read Files from S3:**  
   It fetches audio files stored in the `raw-velocify-callrecordings` S3 bucket. These files are call recordings that need to be transcribed.

2. **Transcribe Using Assembly AI:**  
   The script sends each audio file to the Assembly AI service for transcription.

3. **Save Transcriptions to S3:**
   - The transcription data is saved as a structured JSON object in the `raw-velocify-callrecording-transcriptions` S3 bucket. This contains metadata about the transcription and the transcribed text.
   - The plain text transcript is saved in the `final-velocify-callrecording-transcriptions` S3 bucket as a `.txt` file.

## **Setup:**

Before running the script, ensure the following:

1. **AWS Credentials:**  
   Ensure your EC2 instance has the necessary IAM roles to access the S3 buckets (`raw-velocify-callrecordings`, `raw-velocify-callrecording-transcriptions`, and `final-velocify-callrecording-transcriptions`).

2. **Assembly AI API Key:**  
   Obtain your Assembly AI API key and set it as an environment variable in your EC2 instance, so the script can authenticate with the Assembly AI service.
   - Example: `export ASSEMBLY_API_KEY='your_api_key_here'`

3. **S3 Buckets:**  
   - `raw-velocify-callrecordings`: This is where your raw call recordings are stored.
   - `raw-velocify-callrecording-transcriptions`: This bucket stores the transcription metadata in JSON format.
   - `final-velocify-callrecording-transcriptions`: This bucket stores the plain text transcripts.

4. **Install Dependencies:**  
   You need the `requests` library for interacting with the Assembly AI API. Install it via pip:
   ```
   pip install requests
   ```

## **How It Works:**

### **1. Fetch Files from S3:**
   - The script reads the list of files from the `raw-velocify-callrecordings` S3 bucket.

### **2. Send Files to Assembly AI for Transcription:**
   - For each audio file, it sends a request to Assembly AI’s transcription API to process the file.

### **3. Save Transcription Data:**
   - Once transcription is complete, it stores the metadata and transcription text in the `raw-velocify-callrecording-transcriptions` S3 bucket as JSON.

### **4. Save Plain Text Transcript:**
   - The plain text transcription is saved in the `final-velocify-callrecording-transcriptions` S3 bucket.

## **Usage:**

To run the transcription process, simply execute the `transcribe.py` script:

```bash
python transcribe.py
```

This will:
- Fetch all audio files from the `raw-velocify-callrecordings` S3 bucket.
- Transcribe each file using Assembly AI.
- Save the results (both structured JSON and plain text) to the appropriate S3 buckets.

## **Error Handling:**

- If any error occurs during the transcription or S3 upload process, the script will log the error and skip to the next file.
- You can set up additional error notification mechanisms (e.g., Amazon SNS or SES) for real-time alerts.

## **Environment Variables:**
- `ASSEMBLY_API_KEY`: The Assembly AI API key used for authentication.

## **Logs:**
Logs are printed to the console, and you can add further logging to capture detailed events (such as successful uploads or transcription statuses) if needed.

## **Example of Transcription JSON (stored in `raw-velocify-callrecording-transcriptions`):**
```json
{
  "transcript_id": "some_unique_id",
  "call_id": "call_12345",
  "transcript":"This is the transcription of the call."
  "transcript_url": "s3 transcript url saved as  text in final bucket"
}
```

## **Example of Plain Text Transcript (stored in `final-velocify-callrecording-transcriptions`):**
```
This is the transcription of the call.
```

# **pg-llm** 
```
This EC2 Instance is used for modeling by using data from redshift
It has VPC which is used in redshift to access redshift using private subnet
```

## Navigation

- [Root README](../README.md)
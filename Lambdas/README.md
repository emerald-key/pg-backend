# Lambda Functions in Priority Gold

This document provides details about the various AWS Lambda functions used in the Priority Gold project. Each function plays a crucial role in data processing, integration with third-party services, and managing workflows between S3, Redshift, and other AWS services.

---

## 1. **processVelocifyData**

### **Description:**  
The `processVelocifyData` Lambda function is responsible for processing call log data from Velocify. It is triggered automatically whenever a new CSV file is uploaded to the `raw-velocify-calllogs` S3 bucket.

### **Workflow:**
1. **Trigger:**  
   - S3 trigger from the `raw-velocify-calllogs` bucket upon new CSV file upload.

2. **Data Processing:**  
   - Reads the uploaded CSV file from S3.
   - Iterates through each record to find the `recording_url`.
   - Downloads the corresponding call recording.

3. **Storage:**  
   - Saves the downloaded recordings to another S3 bucket: `raw-velocify-callrecordings`.

4. **Lambda Invocation:**  
   - Invokes another Lambda function, `pushVelocifyCallLogsToRedshift`, which processes the call logs further and inserts them into the respective Redshift tables.

5. **Self-Invocation:**  
   - To handle Lambda timeout issues, it re-invokes itself every 14 minutes, ensuring large datasets are processed without interruptions.

### **Key AWS Services Used:**
- **Amazon S3:** For data storage and triggering.
- **AWS Lambda:** For serverless data processing.
- **Amazon Redshift:** For storing processed call log data.

## 2. **pushBrokersToRedshift**

### **Description:**  
The `pushBrokersToRedshift` Lambda function manages the insertion of broker data into Redshift.

### **Workflow:**
1. **Redshift Connection:**  
   - Initiates a secure connection with the Redshift cluster.

2. **Data Preparation:**  
   - Creates a static JSON object, `brokers_list`, containing broker information.

3. **Broker Data Management:**  
   - Generates a unique UUID for each broker.
   - Deletes any existing broker entry in Redshift with the same name to avoid duplicates.
   - Inserts the new broker data into the Redshift database.

4. **Key AWS Services Used:**
   - **AWS Lambda:** For serverless processing.
   - **Amazon Redshift:** For storing broker information.

---

I've added it above. If you need any further changes, just let me know!
## 3. **pushCallTranscriptToRedshift**

### **Description:**  
This Lambda function processes the transcription of call recordings. It is triggered by an S3 event when a new transcription file is uploaded to the `raw-velocify-callrecording-transcriptions` bucket.

### **Workflow:**
1. **Trigger:**  
   - S3 trigger from the `raw-velocify-callrecording-transcriptions` bucket.

2. **Data Processing:**  
   - Reads the triggered JSON file from the S3 bucket.
   - Pushes the data into the `transcript` table in Redshift.

3. **Key AWS Services Used:**  
   - **Amazon S3**  
   - **AWS Lambda**  
   - **Amazon Redshift**

---

## 4. **pushVelocifyCallLogsToRedshift**

### **Description:**  
The `pushVelocifyCallLogsToRedshift` Lambda function processes and loads Velocify call log data into Redshift.

### **Workflow:**
1. **Trigger:**  
   - Triggered by `processVelocifyData` function.

2. **Data Processing:**  
   - Initiates a connection to Redshift.
   - Creates column mapping for each field.
   - Preprocesses the CSV file by renaming and removing unnecessary columns, then saves it to the `processed` folder in S3.
   
3. **Redshift Load:**  
   - Performs a `COPY` command to load data from the S3 processed folder into the `staging_call` table.
   - The data is then inserted into the main `call` table, handling any duplicates and casting the appropriate columns.
   - Truncates the staging table after the insert operation.

4. **Error Notification:**  
   - Uses Amazon SES for notifications in case of errors.

### **Key AWS Services Used:**
- **Amazon S3**  
- **AWS Lambda**  
- **Amazon Redshift**  
- **Amazon SES**

---

## 5. **pushVelocifyLeadLogsToRedshift**

### **Description:**  
This Lambda function processes and loads Velocify lead log data into Redshift.

### **Workflow:**
1. **Trigger:**  
   - Triggered by S3 events from the `raw-velocify-lead-logs` bucket.

2. **Data Processing:**  
   - Creates column mapping and preprocesses the CSV file by filtering out `logType`, then saves it to the `processed` folder in S3.

3. **Redshift Load:**  
   - Loads the preprocessed CSV into the `staging_lead_log` table and inserts it into the main `lead_log` table after handling duplicates.
   - Truncates the staging table after the insert operation.

4. **Error Notification:**  
   - Uses SES to notify errors.

### **Key AWS Services Used:**
- **Amazon S3**  
- **AWS Lambda**  
- **Amazon Redshift**  
- **Amazon SES**

---

## 6. **pushVelocifyLeadsToRedshift**

### **Description:**  
This Lambda function processes and loads Velocify lead data into Redshift.

### **Workflow:**
1. **Trigger:**  
   - Triggered by S3 events from the `raw-velocify-leads` bucket.

2. **Data Processing:**  
   - Creates column mapping and preprocesses the CSV file, then saves it to the `processed` folder in S3.

3. **Redshift Load:**  
   - Loads the processed CSV into the `staging_lead` table and performs an insert into the main `lead` table, handling duplicates (updating if already exists).
   - Truncates the staging table after the insert operation.

4. **Error Notification:**  
   - Uses SES to notify errors.

### **Key AWS Services Used:**
- **Amazon S3**  
- **AWS Lambda**  
- **Amazon Redshift**  
- **Amazon SES**

---

## 7. **transcriptVelocifyCallRecordings**

### **Description:**  
This Lambda function is triggered by S3 events from the `raw-velocify-callrecordings` bucket. It interacts with Assembly AI to transcribe call recordings.

### **Workflow:**
1. **Trigger:**  
   - S3 trigger from the `raw-velocify-callrecordings` bucket.

2. **Data Processing:**  
   - Uses Assembly AI to transcribe the audio recordings.
   - Saves the transcript in `raw-velocify-callrecording-transcriptions` and `final-velocify-callrecording-transcriptions` S3 buckets as text files.
   - Updates the `transcript_url` field in the raw table with the S3 URI.

3. **Key AWS Services Used:**
- **Amazon S3**  
- **AWS Lambda**  
- **Assembly AI**


Here's the section for the three Lambda functions:

---

## 8. **deleteVelocifyOldCallLogsFromS3**

### **Description:**  
The `deleteVelocifyOldCallLogsFromS3` Lambda function is responsible for finding and deleting old call log files from the `raw-velocify-calllogs` S3 bucket.

### **Workflow:**
1. **S3 Search:**  
   - Finds objects in the `raw-velocify-calllogs` bucket that were inserted within a configured time frame.
   
2. **Deletion:**  
   - Deletes the found objects from the S3 bucket.

3. **Self-Invocation:**  
   - If the execution time exceeds 14 minutes, the function reinvokes itself, starting from the index point where it left off.

---

## 9. **deleteVelocifyOldCallRecordingsFromS3**

### **Description:**  
The `deleteVelocifyOldCallRecordingsFromS3` Lambda function is responsible for finding and deleting old call recording files from the `raw-velocify-callrecordings` S3 bucket.

### **Workflow:**
1. **S3 Search:**  
   - Finds objects in the `raw-velocify-callrecordings` bucket that were inserted within a configured time frame.

2. **Deletion:**  
   - Deletes the found objects from the S3 bucket.

3. **Self-Invocation:**  
   - If the execution time exceeds 14 minutes, the function reinvokes itself, starting from the index point where it left off.

---

## 10. **deleteVelocifyOldLeadsFromS3**

### **Description:**  
The `deleteVelocifyOldLeadsFromS3` Lambda function is responsible for finding and deleting old lead files from the `raw-velocify-leads` S3 bucket.

### **Workflow:**
1. **S3 Search:**  
   - Finds objects in the `raw-velocify-leads` bucket that were inserted within a configured time frame.

2. **Deletion:**  
   - Deletes the found objects from the S3 bucket.

3. **Self-Invocation:**  
   - If the execution time exceeds 14 minutes, the function reinvokes itself, starting from the index point where it left off.

## Navigation

- [Root README](../README.md)
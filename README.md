# Priority Gold

Priority Gold is a backend-focused data management system designed to handle and process large volumes of data efficiently. The project leverages various AWS services to integrate, process, and manage data for advanced data modeling and AI applications.

## Overview

Priority Gold integrates with third-party services like Velocify to manage data related to calls, leads, lead logs, and brokers. Call recordings are transcribed using Assembly AI, stored in Amazon S3, and then loaded into Amazon Redshift for further data analysis and AI-driven insights.

## AWS Services Used

- **AWS EC2:** For running resource-intensive tasks like transcription processing using Assembly AI.
- **AWS IAM:** For managing secure access and permissions to AWS resources like S3, Lambda, and Redshift.
- **AWS Lambda:** For serverless data processing, transformation, and automation tasks across various services.
- **AWS Lambda Layers:** For sharing libraries and dependencies across multiple Lambda functions to reduce redundancy and streamline deployment.
- **Amazon S3:** For storing raw data, processed files, transcription text files, and other artifacts.
- **Amazon Redshift:** For data warehousing, storage, and running complex analytics on processed data.
- **Amazon EventBridge:** For implementing event-driven architecture and triggering automated tasks based on predefined schedules or events.
- **AWS Secrets Manager:** For securely storing and managing credentials, API keys, and other sensitive information.
- **Environment Variables:** For securely managing configuration settings, such as database credentials and other runtime parameters.

## Project Structure

```
Priority Gold/
├── EC2/
├── EventBridge/
├── IAM/
├── Lambdas/
├── Layers/
├── Redshift/
├── S3/
├── SecretManager/
└── README.md
```

## Folder Documentation

- [EC2](./EC2/README.md) 
- [EventBridge](./EventBridge/README.md)  
- [IAM](./IAM/README.md)  
- [Lambdas](./Lambdas/README.md)  
- [Layers](./Layers/README.md)  
- [Redshift](./Redshift/README.md)  
- [S3](./S3/README.md)  
- [SecretManager](./SecretManager/README.md)

## Data Flow

1. **Data Ingestion:** Call, lead, lead log, and broker information from Velocify.
2. **Processing:** AWS Lambda functions handle data processing and transformation.
3. **Storage:** Processed data is stored in Amazon S3.
4. **Transcription:** Call recordings are transcribed using Assembly AI.
5. **Data Loading:** Transcribed data and other processed information are loaded into Amazon Redshift.
6. **Analytics:** Data is modeled and analyzed for AI applications.

## Contact

For any questions or support, please refer to the relevant folder documentation.


# Priority Gold

Priority Gold is a backend-focused data management system designed to handle and process large volumes of data efficiently. The project leverages various AWS services to integrate, process, and manage data for advanced data modeling and AI applications.

## Overview

Priority Gold integrates with third-party services like Velocify to manage data related to calls, leads, lead logs, and brokers. Call recordings are transcribed using Assembly AI, stored in Amazon S3, and then loaded into Amazon Redshift for further data analysis and AI-driven insights.

## AWS Services Used

- **AWS Lambda:** For serverless processing, data transformation, and automation.
- **Amazon S3:** For storing raw data, processed files, and transcription text files.
- **Amazon Redshift:** For data warehousing and analytics.
- **Amazon EventBridge:** For event-driven architecture and automation triggers.
- **AWS Secrets Manager:** For secure storage of credentials and sensitive information.
- **Environment Variables:** For managing configuration settings securely.

## Project Structure

```
Priority Gold/
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

For any questions or support, please refer to the relevant folder documentation or contact the development team.


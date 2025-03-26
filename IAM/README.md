# IAM Configuration

This folder contains IAM (Identity and Access Management) configurations for the Priority Gold project. These configurations are essential for managing permissions and access control across AWS services used in the project.

## Folders and Their Purpose

### 1. `lambdaInvoke`
- **Purpose:** Defines permissions required to invoke AWS Lambda functions.
- **Details:** Grants permission to invoke any Lambda function within the specified AWS account.

### 2. `pg-dev-access-policy`
- **Purpose:** Defines broad permissions required for development within the Priority Gold environment.
- **Details:** Grants comprehensive access to key AWS services including S3, Lambda, EC2, SageMaker, Redshift, Secrets Manager, Glue, EMR, CloudWatch, KMS, and more.

## Importance
These policies ensure that the right level of access is provided for secure and efficient operation of the Priority Gold backend services. Proper IAM configuration helps in maintaining security, compliance, and operational efficiency.


## Navigation

- [Root README](../README.md)

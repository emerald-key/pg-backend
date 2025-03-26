# SecretManager

This folder contains configurations and details related to AWS Secrets Manager. Secrets Manager is used to securely store, manage, and retrieve sensitive information such as API keys, credentials, and tokens.

## Secrets Overview

### 1. **assembly-ai**
- **Purpose:** Stores API keys and authentication details required to interact with the Assembly AI service for transcription processing.
- **File:** `details.py` contains information about the encryption key, secret name, and key-value pairs for secure access.

### 2. **aws-credentials**
- **Purpose:** Manages AWS credentials securely, enabling access to AWS services without hardcoding sensitive information.
- **File:** `details.py` contains encrypted AWS keys and related credentials for secure authentication.

### 3. **pg-redshift-secret**
- **Purpose:** Stores Redshift database credentials securely, including username, password, and connection details.
- **File:** `details.py` includes encryption keys and the secret name along with database credentials.

### 4. **RingCentral-JWTToken**
- **Purpose:** Manages JWT tokens required for authenticating with RingCentral APIs.
- **File:** `details.py` holds the encryption key, secret name, and token details for secure API access.

## Security Practices
- **Encryption:** All secrets are encrypted using AWS KMS.
- **Access Control:** Access to secrets is managed via IAM policies to ensure only authorized Lambda functions and services can retrieve sensitive data.
- **Versioning:** Secrets can be versioned for secure rotation and rollback.

## Navigation
- [Root README](../README.md)


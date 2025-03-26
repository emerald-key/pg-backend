# Layers

The **Layers** folder in the Priority Gold project contains reusable packages bundled as ZIP files. These layers are utilized by multiple AWS Lambda functions to ensure modularity, reduce redundancy, and streamline the deployment process.

### Included Layers:

1. **assemblyai.zip**
   - **Purpose:** This layer includes the AssemblyAI SDK, which is used to interact with AssemblyAI's transcription services.
   - **Usage:** It helps process call recordings by transcribing audio files into text, which are then stored in S3 and later ingested into Redshift for data modeling and AI analysis.

2. **jwt.zip**
   - **Purpose:** Contains libraries for working with JSON Web Tokens (JWT).
   - **Usage:** JWTs are commonly used for secure authentication and authorization, ensuring that the Lambda functions can securely handle data exchanges with external services or APIs.

3. **requests.zip**
   - **Purpose:** This layer bundles the Requests library, a popular HTTP library for Python.
   - **Usage:** It facilitates making HTTP requests to third-party services like Velocify and AssemblyAI, handling API integrations smoothly within Lambda functions.

---

Each of these layers is designed to be lightweight and optimized for AWS Lambda's execution environment, enabling efficient and scalable data processing in the Priority Gold backend infrastructure.

## Navigation

- [Root README](../README.md)


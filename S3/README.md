# S3 Buckets

This folder contains configurations and policies for various S3 buckets used in the **Priority Gold** project. Each subfolder represents an S3 bucket and contains a `bucket-policy.json` file defining the access permissions for that specific bucket.

## List of S3 Buckets

1. **final-velocify-callrecording-transcriptions**  
   Stores the final transcriptions of Velocify call recordings after processing with Assembly AI.

2. **raw-callrail-calllogs**  
   Holds raw call logs from CallRail before any data processing.

3. **raw-callrail-callrecordings**  
   Contains raw call recordings from CallRail.

4. **raw-ringcentral-calllogs**  
   Holds raw call logs from RingCentral.

5. **raw-ringcentral-callrecordings**  
   Contains raw call recordings from RingCentral.

6. **raw-velocify-calllogs**  
   Stores raw call logs from Velocify.

7. **raw-velocify-callrecording-transcriptions**  
   Temporary storage for Velocify call recording transcriptions before final processing.

8. **raw-velocify-callrecordings**  
   Holds raw call recordings from Velocify.

9. **raw-velocify-callrecordings-inventory**  
   Maintains an inventory of Velocify call recordings for tracking and auditing purposes.

10. **raw-velocify-leadlogs**  
    Contains raw lead logs from Velocify.

11. **raw-velocify-leads**  
    Stores raw lead data from Velocify.

## Bucket Policies

Each bucket contains a `bucket-policy.json` file defining access permissions. The policies generally allow public read access (`s3:GetObject`) to the objects within the respective buckets.

## Navigation

- [Root README](../README.md)


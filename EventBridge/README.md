Here’s a README template for the **EventBridge** folder, detailing the **Schedules** and their corresponding `details.py` files:

---

# **EventBridge - Schedules**

This directory contains the configuration for various EventBridge schedules that are set to trigger specific Lambda functions for the Priority Gold project. The schedules are used to automate tasks like deleting old files from S3 buckets.

## **Directory Structure:**
```
EventBridge/
  └── Schedules/
      ├── deleteVelocifyCallLogs/
      │     └── details.py
      ├── deleteVelocifyCallRecordings/
      │     └── details.py
```

## **Overview:**

The `EventBridge/Schedules` folder contains configurations for automated scheduled tasks, such as deleting old call logs and call recordings from the corresponding S3 buckets. Each schedule configuration is specified in a `details.py` file, where you define the service to trigger, the target Lambda function, and the rate of the schedule.

## **Schedules:**

### **1. deleteVelocifyCallLogs**

This schedule triggers the deletion of old call logs from the `raw-velocify-calllogs` S3 bucket.

- **File Path:** `EventBridge/Schedules/deleteVelocifyCallLogs/details.py`
- **Service:** AWS EventBridge
- **Target:** Lambda function `deleteVelocifyOldCallLogsFromS3`
- **Schedule Rate:** (Specify the rate, e.g., `rate(1 day)`)

### **2. deleteVelocifyCallRecordings**

This schedule triggers the deletion of old call recordings from the `raw-velocify-callrecordings` S3 bucket.

- **File Path:** `EventBridge/Schedules/deleteVelocifyCallRecordings/details.py`
- **Service:** AWS EventBridge
- **Target:** Lambda function `deleteVelocifyOldCallRecordingsFromS3`
- **Schedule Rate:** (Specify the rate, e.g., `rate(1 day)`)

## **How It Works:**

Each `details.py` file defines the configuration for the EventBridge rule. These files specify the following:

- **Service:** The AWS service that will trigger the schedule (EventBridge).
- **Target:** The Lambda function that should be triggered by the schedule.
- **Schedule Rate:** The frequency at which the schedule should trigger. For example, a rate of `rate(1 day)` triggers the Lambda every day.

### **Sample `details.py` Configuration:**

```python
# deleteVelocifyCallLogs/details.py

import boto3

# Define the EventBridge client
eventbridge = boto3.client('events')

# Rule configuration
rule_name = 'deleteVelocifyCallLogsRule'
schedule_rate = 'rate(1 day)'  # This can be adjusted as per your requirement

# Define the target Lambda function
target_lambda_function = 'deleteVelocifyOldCallLogsFromS3'

# Create the EventBridge rule
eventbridge.put_rule(
    Name=rule_name,
    ScheduleExpression=schedule_rate,
    State='ENABLED'
)

# Set the target for the rule
eventbridge.put_targets(
    Rule=rule_name,
    Targets=[
        {
            'Id': '1',
            'Arn': f'arn:aws:lambda:us-east-1:{YOUR_AWS_ACCOUNT_ID}:function:{target_lambda_function}',
        },
    ]
)
```

### **Key Components:**
- **ScheduleExpression:** Specifies when the rule should run. You can use the rate or cron expressions, such as `rate(1 day)` or `cron(0 12 * * ? *)`.
- **Target:** Defines the Lambda function to trigger. You must provide the ARN of the target Lambda function.
- **State:** The state of the rule, such as `ENABLED`.

## **How to Update the Schedule:**

1. **Modify the `details.py` file**:
   - To change the schedule rate, simply edit the `schedule_rate` variable to a new rate or cron expression.
   - Example: `rate(1 hour)` or `cron(0 12 * * ? *)`.
   
2. **Deploy the updated configuration**:
   - Run the `details.py` script to update the EventBridge rule with the new configuration. This will update or create the rule based on the provided settings.

## **Error Handling:**

If there’s an error in creating the EventBridge rule or setting the target Lambda, the script will throw an exception. Ensure that:
- The AWS credentials have the necessary permissions to create EventBridge rules and targets.
- The Lambda function exists and has the appropriate permissions to be triggered by EventBridge.

## **Logs:**

EventBridge rule execution logs and any errors are available in AWS CloudWatch Logs, which you can access from the AWS console.

## Navigation

- [Root README](../README.md)
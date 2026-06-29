import boto3
import os
import json

s3 = boto3.client("s3")
ses = boto3.client("ses")
dynamodb = boto3.resource('dynamodb')
recordings_table = dynamodb.Table('velocify-recordings')

SENDER_EMAIL = "alerts@yourcompany.com"
RECIPIENT_EMAIL = "team@yourcompany.com"

def lambda_handler(event, context):
    print("Validator event:", event)

    velocify_date = event["velocify_date"]
    csv_total_recordings = int(event["csv_total_recordings"])
    bucket_name = event["bucket_name"]

    # 1️⃣ Fetch S3 keys for this date from DynamoDB
    s3_keys = fetch_s3_keys_for_date(velocify_date)
    downloaded_count = len(s3_keys)

    # 2️⃣ Compare counts
    missing_count = csv_total_recordings - downloaded_count

    if missing_count == 0:
        print("All recordings successfully downloaded.")
        return {"status": "OK"}

    # 3️⃣ Find which call_ids are missing
    missing_call_ids = find_missing_call_ids(velocify_date, s3_keys)

    # 4️⃣ Send SES notification
    send_email(
        velocify_date,
        csv_total_recordings,
        downloaded_count,
        missing_count,
        missing_call_ids
    )

    return {
        "status": "DONE",
        "csv_total": csv_total_recordings,
        "downloaded": downloaded_count,
        "missing": missing_count
    }

def fetch_s3_keys_for_date(velocify_date):
    response = recordings_table.query(
        KeyConditionExpression="#d = :date",
        ExpressionAttributeNames={"#d": "velocify_date"},
        ExpressionAttributeValues={":date": velocify_date}
    )
    return [item["call_id"] for item in response.get("Items", [])]

def find_missing_call_ids(velocify_date, s3_call_ids):
    # Get the list of recording URLs from the CSV processing table
    # (stored earlier in dynamodb)
    # If not stored → return empty 
    # But for now, assume call_ids = filenames without .mp3
    return []  # or implement full logic if needed

def send_email(date, csv_total, downloaded, missing, missing_list):
    subject = f"[ALERT] Missing Velocify Recordings for {date}"

    body = (
        f"Velocify recording download check for {date}:\n\n"
        f"Total recordings in CSV: {csv_total}\n"
        f"Recordings actually downloaded: {downloaded}\n"
        f"Missing recordings: {missing}\n\n"
        f"Missing Call IDs:\n" +
        "\n".join(missing_list)
    )

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [RECIPIENT_EMAIL]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}}
        }
    )

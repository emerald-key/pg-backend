#copy jsons to redshift
COPY public.Transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/'
CREDENTIALS 'key1=test;key2=test'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';

BEGIN;

-- Step 1: Create a temp table
CREATE TEMP TABLE temp_transcript AS 
SELECT * 
FROM public.Transcript
WHERE 1=0; -- Creates an empty table with the same structure

-- Step 2: Load data into temp table from S3
COPY temp_transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/'
CREDENTIALS 'key1=test;key2=test'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';

-- Step 3: Insert new data into main table (avoid duplicates)
INSERT INTO public.Transcript (call_id, transcript_id, transcript_url)
SELECT DISTINCT t.call_id, t.transcript_id, t.transcript_url
FROM temp_transcript t
LEFT JOIN public.Transcript main
ON t.transcript_id = main.transcript_id
WHERE main.transcript_id IS NULL;

COMMIT;




COPY public.Broker_Summary(Broker_Summary_ID,Call_ID, Timestamp,Broker_ID,Tenure, Broker_Name,Talk_Time,Positives,Opportunities,Summary)
FROM 's3://sample540/processed/broker_summary.csv'
CREDENTIALS 'key1=test;key2=test'
CSV IGNOREHEADER 1;

COPY public.Broker_Intrinsics(Broker_Intrinsics_ID,Call_ID,Broker_ID,Tenure, Broker_Name,Criteria,Score,Reason)
FROM 's3://sample540/processed/broker_intrinsics.csv'
CREDENTIALS 'key1=test;key2=test'
CSV IGNOREHEADER 1;

COPY public.Broker_Adherence(Broker_Adherence_ID,Call_ID,Broker_ID,Tenure, Broker_Name,Criteria,Score,Reason)
FROM 's3://sample540/processed/broker_adherence.csv'
CREDENTIALS 'key1=test;key2=test'
CSV IGNOREHEADER 1;


ALTER TABLE public.Call
ADD COLUMN Lead_ID VARCHAR REFERENCES public.Lead(Lead_ID) NULL;


----Update calls with recording_uuid---------------

CREATE TABLE public.call_test AS
SELECT *
FROM public.call
LIMIT 20;


-- Step 1: Add a new UUID column if it doesn’t exist
ALTER TABLE public.call_test
ADD COLUMN Recording_UUID VARCHAR;

-- Step 2: Generate UUIDs based on the Velocify_Recording_URL
UPDATE public.call_test
SET Recording_UUID = sub.Generated_UUID
FROM (
    SELECT 
        Call_ID,
        Velocify_Recording_URL,
        CASE 
            WHEN Velocify_Recording_URL IS NOT NULL THEN 
                MD5(Velocify_Recording_URL)::VARCHAR 
            ELSE 
                MD5(random()::text || GETDATE()::text)::VARCHAR
        END AS Generated_UUID
    FROM public.call_test
) AS sub
WHERE public.call_test.Call_ID = sub.Call_ID;

SELECT call_id,velocify_Recording_url,recording_uuid from public.call_test;


UPDATE public.call_test
SET Recording_UUID = (
    SELECT Recording_UUID 
    FROM public.call_test 
    WHERE Velocify_Recording_URL = 'https://lm.prod.velocify.com/web/download.aspx?url=https%3a%2f%2fapi.twilio.com%2f2010-04-01%2fAccounts%2fAC949ea5592d3485877bd8b05d86916418%2fRecordings%2fRE1f0ceeb3eb0f87aa9222151586e25821&ext=mp3'
    LIMIT 1
)
WHERE Call_ID = '0000A5C6-7611-4213-B2C6-07314DF9C769';

UPDATE public.call_test SET Velocify_Recording_URL = 'https://test.com' WHERE Call_ID = '00330044-0306-4189-81BB-EF9CF1CDE2E9';


SELECT call_id,velocify_Recording_url,recording_uuid from public.call_test;


-------------Find duplicates -----------
SELECT 
    Log_Type,
    Log_Actor,
    Log_Date,
    Log_Result,
    Log_Note,
    Log_Contact,
    Lead_ID,
    Campaign_Name,
    Affiliate_Name,
    Status,
    Last_Contact_Attempt_Date,
    COUNT(*) AS count
FROM public.Lead_Log
GROUP BY 
    Log_Type,
    Log_Actor,
    Log_Date,
    Log_Result,
    Log_Note,
    Log_Contact,
    Lead_ID,
    Campaign_Name,
    Affiliate_Name,
    Status,
    Last_Contact_Attempt_Date
HAVING COUNT(*) > 1;

 ----Remove duplicates----------------

WITH duplicates AS (
    SELECT 
        Lead_Log_Id,
        ROW_NUMBER() OVER (
            PARTITION BY 
                Log_Type,
                Log_Actor,
                Log_Date,
                Log_Result,
                Log_Note,
                Log_Contact,
                Lead_ID,
                Campaign_Name,
                Affiliate_Name,
                Status,
                Last_Contact_Attempt_Date
            ORDER BY Lead_Log_Id
        ) AS row_num
    FROM public.Lead_Log
)
DELETE FROM public.Lead_Log
WHERE Lead_Log_Id IN (
    SELECT Lead_Log_Id
    FROM duplicates
    WHERE row_num > 1
);

SELECT COUNT(*) from public.lead_log;

--find higest log date-------------
SELECT MAX(Log_Date) AS highest_log_date
FROM public.Lead_Log;
#copy jsons to redshift
COPY public.Transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/'
CREDENTIALS 'key1=test;key2=test'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';


#command to avoid duplicates insertion

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


#copy jsons to redshift by date
COPY public.Transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/03/17/2025/'
CREDENTIALS 'aws_access_key_id=your_key;aws_secret_access_key=your_secret'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';

#copy jsons to redshift by date by handling duplicates for call_id 

BEGIN;

-- 1. Create temporary staging table
CREATE TEMP TABLE transcript_stage (
  call_id VARCHAR,
  transcript_id VARCHAR,
  transcript_url VARCHAR
);

-- 2. Load only from a specific S3 folder (e.g., 03/17/2025/)
COPY transcript_stage (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/03/17/2025/'
CREDENTIALS 'aws_access_key_id=your_key;aws_secret_access_key=your_secret'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';

-- 3. Insert only new call_id records
INSERT INTO public.Transcript (call_id, transcript_id, transcript_url)
SELECT call_id, transcript_id, transcript_url
FROM transcript_stage
WHERE call_id NOT IN (
    SELECT call_id FROM public.Transcript
);

-- 4. Cleanup
DROP TABLE transcript_stage;

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

--Query to update velocify_uuid in calls table"
UPDATE public.call
SET Velocify_UUID = sub.Generated_UUID
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
    FROM public.call
) AS sub
WHERE public.call.Call_ID = sub.Call_ID;


COPY public.Lead_Summary (lead_summary_id,Created_Datetime,Velocify_UUID,lead_id,call_id,timestamp,lead_name,source,status, lead_score_by_broker,total_contact_attempts,lead_affiliate_level_category,
    audio_call_type,audio_call_type_reason,lead_type, lead_type_reason, lead_intrinsic_avg, concern_type, concern_type_reason,
    dollar_amount, account_type, lead_qualification,lead_qualification_reason,summary)
    FROM 's3://llm-model-outputs/redshift-loads/missing_lead_summary/'
    CREDENTIALS 'key1=test;key2=test'
    CSV IGNOREHEADER 1;

--query to load errors 
SELECT *
FROM stl_load_errors
ORDER BY starttime DESC;




UPDATE broker_adherence
SET reason = 'inconclusive',score = 3
WHERE reason = 'Parsing failed or response was not in valid JSON format.';

UPDATE broker_adherence
SET summary = 'inconclusive',score = 3
WHERE summary = 'Parsing failed or response was not in valid JSON format.';


UPDATE broker_intrinsics
SET reason = 'inconclusive',score = 3
WHERE reason = 'Parsing failed or response was not in valid JSON format.';

UPDATE lead_summary
SET summary = 'inconclusive'
WHERE summary = 'Parsing failed or response was not in valid JSON format.';

UPDATE lead_details
SET reason = 'inconclusive',score = 3
WHERE reason = 'Parsing failed or response was not in valid JSON format.';


ALTER TABLE public.broker_dashboard
ADD CONSTRAINT fk_call_lead
FOREIGN KEY (Lead_ID) REFERENCES public.lead(Lead_ID);

---MAIN Query to load transcripts to table Avoid duplicates by call id-----------

BEGIN;

-- Step 1: Create a temp table
CREATE TEMP TABLE temp_transcript AS 
SELECT * 
FROM public.Transcript
WHERE 1=0; -- Creates empty table with the same structure

-- Step 2: Load data into temp table from S3
COPY temp_transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/'
CREDENTIALS 'aws_access_key_id=YOUR_KEY;aws_secret_access_key=YOUR_SECRET'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';

-- Step 3: Insert only new call_ids (no duplicates)
INSERT INTO public.Transcript (call_id, transcript_id, transcript_url)
SELECT DISTINCT t.call_id, t.transcript_id, t.transcript_url
FROM temp_transcript t
LEFT JOIN public.Transcript main
ON t.call_id = main.call_id
WHERE main.call_id IS NULL;

COMMIT;


###Find and delete duplicates in transcript table:



SELECT call_id, COUNT(*) AS duplicate_count
FROM transcript
GROUP BY call_id
HAVING COUNT(*) > 1;

SELECT * from transcript where call_id = 'F4896B84-C63C-410E-B560-55F10A1298A8';

DELETE FROM transcript
USING (
    SELECT transcript_id
    FROM (
        SELECT 
            transcript_id,
            ROW_NUMBER() OVER (PARTITION BY call_id ORDER BY transcript_id) AS rn
        FROM transcript
    ) t
    WHERE t.rn > 1
) duplicates
WHERE transcript.transcript_id = duplicates.transcript_id;


-- Sample inserts for the last 7 days
INSERT INTO public.errorLog (
    id, date, type, totalRecords, failed, error,
    brokerOverarchingSummary, brokerOpportunities, brokerPositives,
    leadAudioCallType, leadConcernType, leadQualification, leadClientType
) VALUES
-- June 17
('id-2005', '2025-06-17', 'broker_adherence', 200, 5, '', 10, 5, 3, 8, 4, 2, 1),
('id-2006', '2025-06-17', 'broker_summary', 70, 2, '', 5, 2, 1, 4, 1, 1, 0),
('id-2007', '2025-06-17', 'broker_intrinsics', 40, 2, '', 5, 2, 1, 4, 1, 1, 0),
('id-2008', '2025-06-17', 'lead_details', 90, 2, '', 5, 2, 1, 4, 1, 1, 0),
('id-2009', '2025-06-17', 'lead_summary', 20, 2, '', 5, 2, 1, 4, 1, 1, 0);

SELECT 
    date,
    SUM(totalRecords) AS total_records,
    SUM(failed) AS total_failed
FROM errorLog
WHERE date >= CURRENT_DATE - INTERVAL '7 day'
GROUP BY date
ORDER BY date;

##get count of calls within date

SELECT COUNT(*) AS call_count
FROM call
JOIN transcript ON call.call_id = transcript.call_id
WHERE call.date_time >= '2025-03-21 00:00:00'
  AND call.date_time <  '2025-03-24 00:00:00'
  AND call.talk_time > 60;

##update table with other table info
UPDATE lead_summary
SET 
    broker_name = bs.broker_name,
    broker_id = bs.broker_id,
    role = bs.role
FROM broker_summary bs
WHERE lead_summary.call_id = bs.call_id;


UPDATE lead_details
SET 
    broker_name = bs.broker_name,
    broker_id = bs.broker_id,
    role = bs.role
FROM broker_summary bs
WHERE lead_details.call_id = bs.call_id;


## update reason in broker adherence based on broker role and criteria
UPDATE broker_adherence
SET reason = CASE
    WHEN role = 'Sr. Account Executive' AND criteria IN ('Ask_about_experience', 'Ask_about_concern', 'Ask_about_interest', 'Call Transfer', 'Jr_Credibility', 'Discuss funds', 'Reference_creative') 
        THEN 'This feature is related to Jr. Account Executive'
    WHEN role <> 'Sr. Account Executive' AND criteria IN ('Ask for sale', 'Consultation', 'Sr_Credibility', 'Time frame', 'How sale works', 'Introduction', 'Market update', 'Re-qualification') 
        THEN 'This feature is related Sr. Account Executive'
    ELSE NULL
END
WHERE
    (
        (role = 'Sr. Account Executive' AND criteria IN ('Ask_about_experience', 'Ask_about_concern', 'Ask_about_interest', 'Call Transfer', 'Jr_Credibility', 'Discuss funds', 'Reference_creative'))
        OR
        (role <> 'Sr. Account Executive' AND criteria IN ('Ask for sale', 'Consultation', 'Sr_Credibility', 'Time frame', 'How sale works', 'Introduction', 'Market update', 'Re-qualification'))
    )

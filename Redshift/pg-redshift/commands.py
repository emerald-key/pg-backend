#copy jsons to redshift
COPY public.Transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/'
CREDENTIALS 'key1=test;key2=test'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';


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
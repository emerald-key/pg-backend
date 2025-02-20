#copy jsons to redshift
COPY public.Transcript (call_id, transcript_id, transcript_url)
FROM 's3://raw-velocify-callrecording-transcriptions/'
CREDENTIALS 'key1=test;key2=test'
JSON 's3://velocify-json-paths/transcription.json'
REGION 'us-east-1';
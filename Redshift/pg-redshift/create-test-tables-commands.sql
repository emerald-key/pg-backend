----INSERT test_broker and test_redFlagsData tables and insert test data into them------------------
CREATE TABLE public.test_broker (
    LIKE public.Broker
);

CREATE TABLE public.test_redFlagsData
(
    LIKE public.redFlagsData
);

INSERT INTO public.test_broker (
    Broker_ID,
    Broker_Name,
    Broker_First_Name,
    Broker_Last_Name,
    Broker_Name_Original,
    phoneNumber,
    email,
    extension,
    state,
    role,
    tier
)
VALUES
(
    'TEST_SR_001',
    'Test Broker 1',
    'Sravya',
    'V',
    'Test Broker 1',
    NULL,
    'sravya.v@quiddityinfotech.com',
    NULL,
    'TX',
    'Sr. Account Executive',
    'A'
),
(
    'TEST_SR_002',
    'Test Broker 2',
    'Sravya',
    'Vemulapally',
    'Test Broker 2',
    NULL,
    'sravya.vemulapally@emeraldkey.com',
    NULL,
    'TX',
    'Sr. Account Executive',
    'A'
),
(
    'TEST_SR_003',
    'Test Broker 3',
    'Kalyan',
    'Adepu',
    'Test Broker 3',
    NULL,
    'kalyan.adepu@emeraldkey.com',
    NULL,
    'TX',
    'Sr. Account Executive',
    'B'
),
(
    'TEST_SR_004',
    'Test Broker 4',
    'Akhil',
    'K',
    'Test Broker 4',
    NULL,
    'akhil.k@emeraldkey.com',
    NULL,
    'TX',
    'Sr. Account Executive',
    'B'
);

SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'test_redflagsdata'
  AND is_nullable = 'NO'
ORDER BY ordinal_position;

INSERT INTO public.test_redFlagsData (
    id,
    Lead_ID,
    Lead_Name,
    Call_ID,
    Broker_Name,
    Date,
    Original_Score_Or_Type,
    New_Score_Or_Type,
    Reason,
    Created_Datetime,
    Criteria,
    Score,
    Lead_Type,
    Lead_Qualification,
    Dollar_amount,
    Sales_Competitor,
    Sales_Competitor_Context,
    Financial_Advisor_Context,
    reason_transcript,
    Tier,
    Competitor_Audio_Timestamp,
    Finan_Adv_Audio_Timestamp,
    Dollar_Amount_Audio_Timestamp,
    Dollar_Amount_Transcript_Snippet,
    highdollar_amount_audio_timestamp,
    broker_info,
    velocify_uuid,
    call_id_list,
    brokers_involved,
    role_tier,
    concern_score,
    interest_score,
    discuss_funds_score,
    call_type,
    call_duration_original,
    outcome,
    lead_score,
    appointment_set,
    callback,
    concern_needed
)
WITH ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.reason
            ORDER BY r.created_datetime
        ) AS rn
    FROM public.redFlagsData r
    QUALIFY rn <= 5
),
brokers AS (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY Broker_ID) AS b_rn
    FROM public.test_broker
),
broker_cycle AS (
    SELECT
        r.*,
        b.Broker_Name AS mapped_broker
    FROM ranked r
    JOIN brokers b
      ON ((r.rn - 1) % 4) + 1 = b.b_rn
)

SELECT
    r.id,
    r.lead_id,
    r.lead_name,
    r.call_id,
    r.mapped_broker AS Broker_Name,
    r.date,
    r.original_score_or_type,
    r.new_score_or_type,
    r.reason,
    r.created_datetime,
    r.criteria,

    -- safe numeric conversion
    CASE 
        WHEN r.score::VARCHAR IN ('-', '', 'null') THEN NULL
        ELSE r.score
    END AS score,

    r.lead_type,
    r.lead_qualification,
    r.dollar_amount,
    r.sales_competitor,
    r.sales_competitor_context,
    r.financial_advisor_context,
    r.reason_transcript,
    r.tier,
    r.competitor_audio_timestamp,
    r.finan_adv_audio_timestamp,
    r.dollar_amount_audio_timestamp,
    r.dollar_amount_transcript_snippet,
    r.highdollar_amount_audio_timestamp,
    r.broker_info,
    r.velocify_uuid,
    r.call_id_list,
    r.brokers_involved,
    r.role_tier,
    r.concern_score,
    r.interest_score,
    r.discuss_funds_score,
    r.call_type,
    r.call_duration_original,
    r.outcome,
    r.lead_score,
    r.appointment_set,
    r.callback,
    r.concern_needed
FROM broker_cycle r;

select * from test_broker;
select * from test_redFlagsData;

------------------------------------------------------------------------------------------------------------
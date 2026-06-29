CREATE TABLE public.staging_call (
    Call_ID VARCHAR PRIMARY KEY,
    Broker_Name VARCHAR,
    Lead_ID Int,
    Call_Type VARCHAR(255),
    Date_Time VARCHAR(255),
    Talk_Time INT,
    Call_Duration_Original VARCHAR(255),
    Outcome VARCHAR(255),
    Call_Segment VARCHAR(255),
    Inbound_Number VARCHAR(255),
    Prospect_Number VARCHAR(255),
    Velocify_Recording_URL VARCHAR(65535),
    Velocify_UUID VARCHAR(255),
    Call_Duration INT,
    Source VARCHAR(255)
);

CREATE TABLE public.call (
    Call_ID VARCHAR PRIMARY KEY,
    Broker_Name VARCHAR,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Call_Type VARCHAR(255),
    Date_Time TIMESTAMP,
    Talk_Time INT,
    Call_Duration_Original VARCHAR(255),
    Outcome VARCHAR(255),
    Call_Segment VARCHAR(255),
    Inbound_Number VARCHAR(255),
    Prospect_Number VARCHAR(255),
    Velocify_Recording_URL VARCHAR(65535),
    Velocify_UUID VARCHAR(255),
    Call_Duration INT,
    Source VARCHAR(255)
);

CREATE TABLE public.Lead (
    Lead_ID INT PRIMARY KEY,
    Source VARCHAR,
    Lead_Status VARCHAR,
    Lead_Score VARCHAR,
    Milestone VARCHAR,
    Broker_Name VARCHAR,
    "Group" VARCHAR,
    Date_Added TIMESTAMP,
    Date_Modified TIMESTAMP,
    Last_Action VARCHAR,
    First_Contact_Attempt_Date TIMESTAMP,
    Action_Count INT,
    Total_Contact_Attempts INT,
    Last_Action_Date TIMESTAMP,
    First_Assignment_Distribution_Date TIMESTAMP,
    First_Assignment_Distribution_User VARCHAR,
    Lead_Source_Group VARCHAR,
    Creative VARCHAR,
    Broker VARCHAR,
    Opener VARCHAR,
    IRA_Investment_Dollar VARCHAR,
    Cash_Investment_Dollar VARCHAR,
    Deal_Type VARCHAR,
    Transfer_Type VARCHAR,
    "TO_Date" TIMESTAMP,
    SF_Lead_ID VARCHAR,
    Velocify_ID VARCHAR,
    Original_Broker VARCHAR,
    SF_Lead_Owner VARCHAR,
    Junior_Broker VARCHAR,
    Last_Activity TIMESTAMP,
    Intellect_Client_ID VARCHAR,
    Intellect_Broker VARCHAR,
    First_Name VARCHAR,
    Last_Name VARCHAR,
    Home_Phone VARCHAR,
    Work_Phone VARCHAR,
    Mobile_Phone VARCHAR,
    Email VARCHAR,
    Secondary_Email VARCHAR,
    Address VARCHAR,
    City VARCHAR,
    State VARCHAR,
    Zip_Postal_Code VARCHAR,
    Source_Code VARCHAR,
    SubID VARCHAR
);
CREATE TABLE public.Staging_Lead (
    Lead_ID VARCHAR PRIMARY KEY,
    Source VARCHAR,
    Lead_Status VARCHAR,
    Lead_Score VARCHAR,
    Milestone VARCHAR,
    Broker_Name VARCHAR,
    "Group" VARCHAR,
    Date_Added VARCHAR,
    Date_Modified VARCHAR,
    Last_Action VARCHAR,
    First_Contact_Attempt_Date VARCHAR,
    Action_Count VARCHAR,
    Total_Contact_Attempts VARCHAR,
    Last_Action_Date VARCHAR,
    First_Assignment_Distribution_Date VARCHAR,
    First_Assignment_Distribution_User VARCHAR,
    Lead_Source_Group VARCHAR,
    Creative VARCHAR,
    Broker VARCHAR,
    Opener VARCHAR,
    IRA_Investment_Dollar VARCHAR,
    Cash_Investment_Dollar VARCHAR,
    Deal_Type VARCHAR,
    Transfer_Type VARCHAR,
    "TO_Date" VARCHAR,
    SF_Lead_ID VARCHAR,
    Velocify_ID VARCHAR,
    Original_Broker VARCHAR,
    SF_Lead_Owner VARCHAR,
    Junior_Broker VARCHAR,
    Last_Activity VARCHAR,
    Intellect_Client_ID VARCHAR,
    Intellect_Broker VARCHAR,
    First_Name VARCHAR,
    Last_Name VARCHAR,
    Home_Phone VARCHAR,
    Work_Phone VARCHAR,
    Mobile_Phone VARCHAR,
    Email VARCHAR,
    Secondary_Email VARCHAR,
    Address VARCHAR,
    City VARCHAR,
    State VARCHAR,
    Zip_Postal_Code VARCHAR,
    Source_Code VARCHAR,
    SubID VARCHAR
);

CREATE TABLE public.Transcript (
    Transcript_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Transcript_Url VARCHAR
);


CREATE TABLE public.Lead_Log ( 
    Lead_Log_Id VARCHAR PRIMARY KEY,
    Log_Type VARCHAR,
    Log_Actor VARCHAR,
    Log_Date TIMESTAMP,
    Log_Result VARCHAR,
    Log_Note VARCHAR,
    Log_Contact VARCHAR,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Campaign_Name VARCHAR,
    Affiliate_Name VARCHAR,
    Status VARCHAR,
    Last_Contact_Attempt_Date TIMESTAMP
);

CREATE TABLE public.staging_Lead_Log (
    Lead_Log_Id VARCHAR PRIMARY KEY,
    Log_Type VARCHAR,
    Log_Actor VARCHAR,
    Log_Date VARCHAR,
    Log_Result VARCHAR,
    Log_Note VARCHAR,
    Log_Contact VARCHAR,
    Lead_ID INT,
    Campaign_Name VARCHAR,
    Affiliate_Name VARCHAR,
    Status VARCHAR,
    Last_Contact_Attempt_Date VARCHAR
);


CREATE TABLE public.Broker (
    Broker_ID VARCHAR PRIMARY KEY,
    Broker_Name VARCHAR(255),
    Broker_First_Name VARCHAR(255),
    Broker_Last_Name VARCHAR(255),
    Broker_Name_Original VARCHAR(255),
    phoneNumber VARCHAR(255),
    email VARCHAR(255),
    extension VARCHAR(255),
    state VARCHAR(255),
    role VARCHAR(255),
    tier VARCHAR(255)
);

CREATE TABLE public.Broker_Scores (
    Broker_Score_ID VARCHAR PRIMARY KEY,
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(255),
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Criteria VARCHAR(255),
    Timestamp TIMESTAMP,
    Duration VARCHAR(255),
    Score INT,
    Reason VARCHAR(255)
);



CREATE TABLE public.Broker_Summary (
    Broker_Summary_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(65535),
    Role VARCHAR(65535),
    Timestamp VARCHAR(65535),
    Duration VARCHAR(65535),
    Broker_Talktime VARCHAR(255),
    Customer_Talktime VARCHAR(255),
    Positives VARCHAR(65535),
    Opportunities VARCHAR(65535),
    Broker_Overarching_Summary VARCHAR(65535),
    Created_Datetime TIMESTAMP,
    Velocify_UUID VARCHAR(255),
    Call_Type               VARCHAR(255),
    Outcome                 VARCHAR(255).
    Broker_Name
);

CREATE TABLE public.Broker_Intrinsics (
    Broker_Intrinsics_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Role VARCHAR(50),
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(255),
    Timestamp TIMESTAMP NOT NULL,
    Criteria VARCHAR(255),
    Score DECIMAL(5, 2),
    Reason VARCHAR(65535),
    Created_Datetime TIMESTAMP,
    Velocify_UUID VARCHAR(255),
    Call_Type               VARCHAR(255),
    Outcome                 VARCHAR(255)
);

CREATE TABLE public.Broker_Adherence (
    Broker_Adherence_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Role VARCHAR(50),
    Timestamp TIMESTAMP NOT NULL,
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(255),
    Criteria VARCHAR(255),
    Score DECIMAL(5, 2),
    Reason VARCHAR(65535),
    Summary VARCHAR(65535),
    Created_Datetime TIMESTAMP,
    Velocify_UUID VARCHAR(255),
    Call_Type               VARCHAR(255),
    Outcome                 VARCHAR(255)
);
CREATE TABLE public.lead_summary (
    Lead_Summary_ID VARCHAR PRIMARY KEY,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Timestamp TIMESTAMP,
    Lead_Name VARCHAR(65535),
    Status VARCHAR(65535),
    Lead_Score_By_Broker VARCHAR(65535),
    Total_Contact_Attempts INT,
    Lead_Affiliate_Level_Category VARCHAR(65535),
    Audio_Call_Type VARCHAR(65535),
    Audio_Call_Type_Reason VARCHAR(65535),
    Lead_Type VARCHAR(65535),
    Lead_Type_Reason VARCHAR(65535),
    Lead_Intrinsic_Avg VARCHAR(65535),
    Concern_Type VARCHAR(65535),
    Concern_Type_Reason VARCHAR(65535),
    Dollar_Amount VARCHAR(65535),
    Account_Type VARCHAR(65535),
    Lead_Qualification VARCHAR(65535),
    Lead_Qualification_Reason VARCHAR(65535),
    Summary VARCHAR(65535),
    Created_Datetime TIMESTAMP,
    Velocify_UUID VARCHAR(255),
    Source VARCHAR(65535),
    Call_Type               VARCHAR(255),
    Outcome                 VARCHAR(255),
    Broker_Name  VARCHAR(255),
    Broker_ID  VARCHAR(255),
    role  VARCHAR(255),
    actual_dollar_amount VARCHAR(65535),
    Financial_Advisor_Mentioned VARCHAR(65535),
    Financial_Advisor_Context VARCHAR(65535),
    Sales_Competitor VARCHAR(65535),
    Sales_Competitor_Context VARCHAR(65535),
    appointment_set VARCHAR(65535),
    appointment_evidence    VARCHAR(65535),
    callback    VARCHAR(65535),
    callback_reasoning  VARCHAR(65535),
    concern_needed  VARCHAR(65535),
    heat_level  VARCHAR(65535),
    heat_signals  VARCHAR(65535),
    heat_summary  VARCHAR(65535),
    compliance_has_issue    VARCHAR(65535),
    compliance_issues_evidences    VARCHAR(65535),
    compliance_priority    VARCHAR(65535),
    classify_ask_for_sale   VARCHAR(65535),
    classify_ask_for_sale_reason    VARCHAR(65535),
    classify_concern    VARCHAR(65535),
    classify_concern_reason VARCHAR(65535)
);

CREATE TABLE public.lead_details (
    lead_details_id VARCHAR PRIMARY KEY,
    lead_id INT REFERENCES public.Lead(Lead_ID) NULL,
    lead_name VARCHAR,
    call_id VARCHAR REFERENCES public.Call(Call_ID) NULL,
    timestamp TIMESTAMP NOT NULL,
    duration VARCHAR(255),
    durationInSecs INT,
    criteria VARCHAR(255),
    Score DECIMAL(5,2),
    reason VARCHAR(65535),
    Created_Datetime TIMESTAMP,
    Velocify_UUID VARCHAR(255),
    Call_Type    VARCHAR(255),
    Outcome      VARCHAR(255),
    Broker_Name  VARCHAR(255)
    Broker_ID  VARCHAR(255)
    role  VARCHAR(255)
);
CREATE TABLE public.broker_dashboard (
    broker_summary_id       VARCHAR PRIMARY KEY,
    call_id                 VARCHAR(50),
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    timestamp               TIMESTAMP,
    broker_id               VARCHAR(255),
    broker_name             VARCHAR(100),
    role                    VARCHAR(100),
    duration                VARCHAR(255),
    broker_talktime         DECIMAL(5,2),
    customer_talktime       DECIMAL(5,2),
    positives               VARCHAR(65535),
    opportunities           VARCHAR(65535),
    broker_overarching_summary   VARCHAR(65535),
    type                    VARCHAR(50),         -- 'intrinsics' or 'adherence'
    criteria                VARCHAR(65535),
    score                   DECIMAL(5,2),
    reason                  VARCHAR(65535),
    Created_Datetime        TIMESTAMP,
    Velocify_UUID           VARCHAR(255),
    Call_Type               VARCHAR(255),
    Outcome                 VARCHAR(255)
);

CREATE TABLE public.lead_dashboard (
    Lead_Summary_ID VARCHAR PRIMARY KEY,
    Lead_ID INT,
    Call_ID VARCHAR,
    Timestamp TIMESTAMP,
    Lead_Name VARCHAR,
    Status VARCHAR(255),
    Lead_Score_By_Broker VARCHAR(65535),
    Total_Contact_Attempts INT,
    Lead_Affiliate_Level_Category VARCHAR(255),
    Audio_Call_Type VARCHAR(65535),
    Audio_Call_Type_Reason VARCHAR(65535),
    Lead_Type VARCHAR(255),
    Lead_Type_Reason VARCHAR(65535),
    Lead_Intrinsic_Avg DECIMAL,
    Concern_Type VARCHAR(255),
    Concern_Type_Reason VARCHAR(65535),
    Dollar_Amount BIGINT,
    Account_Type VARCHAR(255),
    Lead_Qualification VARCHAR(255),
    Lead_Qualification_Reason VARCHAR(65535),
    Summary VARCHAR(65535),
    Lead_Details_ID VARCHAR,
    Details_Timestamp TIMESTAMP,
    Duration VARCHAR(255),
    DurationInSecs INT,
    Criteria VARCHAR(255),
    Score DECIMAL(5,2),
    Reason VARCHAR(65535),
    Created_Datetime TIMESTAMP,
    Velocify_UUID VARCHAR(255),
    Source  VARCHAR(65535)
    Call_Type               VARCHAR(255),
    Outcome                 VARCHAR(255),
    Broker_Name  VARCHAR(255),
    Broker_ID  VARCHAR(255),
    role  VARCHAR(255),
    actual_dollar_amount VARCHAR(65535),
    Financial_Advisor_Mentioned VARCHAR(65535),
    Financial_Advisor_Context VARCHAR(65535),
    Sales_Competitor VARCHAR(65535),
    Sales_Competitor_Context VARCHAR(65535),
    appointment_set VARCHAR(65535),
    appointment_evidence    VARCHAR(65535),
    callback    VARCHAR(65535),
    callback_reasoning  VARCHAR(65535),
    concern_needed  VARCHAR(65535),
    heat_level  VARCHAR(65535),
    heat_signals  VARCHAR(65535),
    heat_summary  VARCHAR(65535),
    compliance_has_issue    VARCHAR(65535),
    compliance_issues_evidences    VARCHAR(65535),
    compliance_priority    VARCHAR(65535),
    classify_ask_for_sale   VARCHAR(65535),
    classify_ask_for_sale_reason    VARCHAR(65535),
    classify_concern    VARCHAR(65535),
    classify_concern_reason VARCHAR(65535)
);
CREATE TABLE public.sales (
    Lead_ID         INT PRIMARY KEY,
    Date           VARCHAR(255),
    Amount         VARCHAR(255),
    GrossSaleAmount VARCHAR(255)  
);


CREATE TABLE public.errorLog (
    id                      VARCHAR PRIMARY KEY,
    date                    VARCHAR(255),
    type                    VARCHAR(255),
    totalRecords            INT,
    failed                  INT,
    error                   VARCHAR(65535),
    brokerOverarchingSummary INT,
    brokerOpportunities      INT,
    brokerPositives          INT,
    leadAudioCallType        INT,
    leadConcernType          INT,
    leadQualification        INT,
    leadClientType           INT
);


CREATE TABLE public.llmBatches (
    id                      VARCHAR PRIMARY KEY,
    call_id                 VARCHAR(255),
    date_time               TIMESTAMP,
    batch_number            VARCHAR(25),
    processed_time          VARCHAR(255),
    processing_status       VARCHAR(255)
);

CREATE TABLE public.alertMessages (
    id                      VARCHAR PRIMARY KEY,
    lead_id                 INT,
    prev_lead_type          VARCHAR(255),
    current_lead_type       VARCHAR(255),
    prev_timestamp          TIMESTAMP,
    "current_timestamp"       TIMESTAMP    
);


---create test tables with main table structure
CREATE TABLE broker_summary_test AS 
SELECT * FROM broker_summary WHERE 1=0;

CREATE TABLE broker_intrinsics_test AS 
SELECT * FROM broker_intrinsics WHERE 1=0;

CREATE TABLE broker_adherence_test AS 
SELECT * FROM broker_adherence WHERE 1=0;

CREATE TABLE lead_summary_test AS 
SELECT * FROM lead_summary WHERE 1=0;

CREATE TABLE lead_details_test AS 
SELECT * FROM lead_details WHERE 1=0;


CREATE TABLE public.dataParsingErrors (
    id                      VARCHAR PRIMARY KEY,
    date                    VARCHAR(255),
    type                    VARCHAR(255),
    totalRecords            INT,
    failed                  INT,
    brokerOverarchingSummary INT,
    brokerOpportunities      INT,
    brokerPositives          INT,
    leadAudioCallType        INT,
    leadConcernType            INT,
    leadQualification            INT,
    leadClientType            INT
);

CREATE TABLE public.redFlagsData (
    id                      VARCHAR PRIMARY KEY
    Lead_ID                      INT,
    Lead_Name                    VARCHAR(255),
    Call_ID                      VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Broker_Name            VARCHAR,
    Date                  timestamp,
    Original_Score_Or_Type VARCHAR,
    New_Score_Or_Type      VARCHAR,
    Reason          VARCHAR(65535),
    Created_Datetime  timestamp,
    Criteria VARCHAR(65535),
    Score DECIMAL(5, 2),
    Lead_Type VARCHAR(65535),
    Lead_Qualification VARCHAR(65535), 
    Dollar_amount VARCHAR(65535), 
    Sales_Competitor VARCHAR(65535), 
    Sales_Competitor_Context VARCHAR(65535),
    Financial_Advisor_Context VARCHAR(65535),
    reason_transcript    VARCHAR(65535),
    Tier                 VARCHAR(255),
    Competitor_Audio_Timestamp       VARCHAR(255),
    Finan_Adv_Audio_Timestamp        VARCHAR(255),
    Dollar_Amount_Audio_Timestamp    VARCHAR(255),
    Dollar_Amount_Transcript_Snippet  VARCHAR(255),
    highdollar_amount_audio_timestamp VARCHAR(255),
    broker_info         VARCHAR(65535),
    velocify_uuid                 VARCHAR(255),
    call_id_list                 SUPER,
    brokers_involved             SUPER,
    role_tier                 SUPER,
    concern_score VARCHAR(255),
    interest_score VARCHAR(255),
    discuss_funds_score VARCHAR(255),
    call_type VARCHAR(255),
    call_duration_original VARCHAR(255),
    outcome VARCHAR(255),
    lead_score VARCHAR(65535),le
    appointment_set VARCHAR(65535),
    callback    VARCHAR(65535),
    concern_needed  VARCHAR(65535),
    heat_level  VARCHAR(65535),
    heat_signals  VARCHAR(65535),
    heat_summary  VARCHAR(65535),
    audio_call_type_reason  VARCHAR(65535),
    audio_call_type  VARCHAR(65535),
    appointment_evidence    VARCHAR(65535),
    compliance_has_issue    VARCHAR(65535),
    compliance_issues_evidences    VARCHAR(65535),
    compliance_priority    VARCHAR(65535),
    classify_ask_for_sale   VARCHAR(65535),
    classify_ask_for_sale_reason    VARCHAR(65535),
    classify_concern    VARCHAR(65535),
    classify_concern_reason VARCHAR(65535)
);
CREATE TABLE public.callrecording_transcription_errors (
    id VARCHAR(50),
    call_id VARCHAR(50),
    velocify_date VARCHAR(20),
    error_message VARCHAR(MAX),
    created_at TIMESTAMP DEFAULT GETDATE()
);

CREATE TABLE IF NOT EXISTS public.stg_transcripts
(LIKE public.transcripts);


CREATE TABLE public.lead_source_summary (
    id                      VARCHAR PRIMARY KEY,
    source                   VARCHAR(255),

    avg_talk_time             DECIMAL(10,2),
    talk_time_high_pct        DECIMAL(5,2),

    avg_intrinsic             DECIMAL(10,2),
    intrinsic_high_pct        DECIMAL(5,2),

    lead_type_score           DECIMAL(5,2),
    lead_quality_index        DECIMAL(5,2),

    num_leads                 DECIMAL,
    num_clients               DECIMAL,
    client_conv_percent       DECIMAL(5,2),

    window                    VARCHAR(50),
    created_datetime          TIMESTAMP
);

CREATE VIEW v_lead_source_summary AS
SELECT *,
       CASE
         WHEN created_datetime = MAX(created_datetime) OVER ()
         THEN true
         ELSE false
       END AS is_latest_run
FROM lead_source_summary;



CREATE OR REPLACE VIEW redflagsdata_qs AS
SELECT
    *,
    CASE
        WHEN Reason IN ('At-risk lead(Gold Competitor)', 'Another gold dealer mentioned')
            THEN 'Another gold dealer mentioned'
        WHEN Reason IN ('At-risk lead(Financial Advisor)', 'Financial advisor mentioned')
            THEN 'Financial advisor mentioned'
        WHEN Reason IN (
            'Large change in Lead type',
            'Large change in lead type',
            'Large drop in lead type'
        )
            THEN 'Large drop in lead type'
        WHEN Reason IN (
            'Potentially qualified but not transferred',
            'Potentially missed transfer'
        )
            THEN 'Potentially missed transfer'
        WHEN Reason IN (
            'Qualified/partially qualified and trust < 3, Qualified/partially qualified and hesitation < 3.',
            'Low trust or hesitation for a qualified/partially qualified lead'
        )
            THEN 'Low trust or hesitation for a qualified/partially qualified lead'
        WHEN Reason IN (
            'Qualified/partially qualified and trust drops by 2, Qualified/partially qualified and hesitation drops by 2.',
            'Trust or hesitation dropped significantly'
        )
            THEN 'Trust or hesitation dropped significantly'
        ELSE Reason
    END AS Reason_normalized
FROM redFlagsData;



CREATE OR REPLACE VIEW v_lead_source_trends AS
SELECT
    t.*,
    'Week-' || t.week_index AS week_label
FROM (
    SELECT
        source,
        window,
        DATE_TRUNC('week', run_date) AS run_week,

        AVG(lead_quality_index)     AS avg_lqi,
        AVG(client_conv_percent)    AS avg_client_conv,

        COUNT(DISTINCT run_date)    AS runs_in_week,

        DENSE_RANK() OVER (
            PARTITION BY window
            ORDER BY DATE_TRUNC('week', run_date) DESC
        ) AS week_index
    FROM lead_source_summary
    GROUP BY
        source,
        window,
        DATE_TRUNC('week', run_date)
) t;
CREATE TABLE alertsData (
    alert_date            TIMESTAMP,
    lead_id               VARCHAR(255),
    lead_name             VARCHAR(255),
    broker_name           VARCHAR(255),
    call_id               VARCHAR(100),
    reason_for_flag       VARCHAR(500),
    original_flagged_value VARCHAR(100),
    new_flagged_value     VARCHAR(100),
    context               VARCHAR(500),
    created_datetime      TIMESTAMP
)
DISTSTYLE AUTO;


CREATE TABLE source_lqi_metrics (
    source                    VARCHAR(255) PRIMARY KEY,
    run_week                  DATE,
    rank_type                 VARCHAR(50),
    avg_lqi                   DECIMAL(10,4),
    lqi_wow                   DECIMAL(10,4),
    lqi_rolling_3w            DECIMAL(10,4),
    lqi_wow_rolling_3w        DECIMAL(10,4),
    avg_client_conv           DECIMAL(10,4),
    runs_in_week              INTEGER,
    wow_anomaly               BOOLEAN
)
DISTSTYLE AUTO;

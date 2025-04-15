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
    Velocify_UUID VARCHAR(255)
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
    Velocify_UUID VARCHAR(255)
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
    Broker_Name_Original VARCHAR(255),
    phoneNumber VARCHAR(255),
    email VARCHAR(255),
    extension VARCHAR(255),
    state VARCHAR(255),
    role VARCHAR(255)
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
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(65535),
    Role VARCHAR(65535),
    Timestamp VARCHAR(65535),
    Duration VARCHAR(65535),
    Broker_Talktime VARCHAR(255),
    Customer_Talktime VARCHAR(255),
    Positives VARCHAR(65535),
    Opportunities VARCHAR(65535),
    Broker_Overarching_Summary VARCHAR(65535)
);

CREATE TABLE public.Broker_Intrinsics (
    Broker_Intrinsics_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Role VARCHAR(50),
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(255),
    Timestamp TIMESTAMP NOT NULL,
    Criteria VARCHAR(255),
    Score DECIMAL(5, 2),
    Reason VARCHAR(65535)
);

CREATE TABLE public.Broker_Adherence (
    Broker_Adherence_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Role VARCHAR(50),
    Timestamp TIMESTAMP NOT NULL,
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Broker_Name VARCHAR(255),
    Criteria VARCHAR(255),
    Score DECIMAL(5, 2),
    Reason VARCHAR(65535),
    Summary VARCHAR(65535)
);

CREATE TABLE public.lead_summary (
    Lead_Summary_ID VARCHAR PRIMARY KEY,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Timestamp VARCHAR(65535),
    Lead_Name VARCHAR,
    Status VARCHAR(255),
    Lead_Score_By_Broker VARCHAR(255),
    Total_Contact_Attempts INT,
    Lead_Affiliate_Level_Category VARCHAR(255),
    Audio_Call_Type VARCHAR(255),
    Audio_Call_Type_Reason VARCHAR(255),
    Lead_Type VARCHAR(255),
    Lead_Type_Reason VARCHAR(65535),
    Lead_Intrinsic_Avg VARCHAR(255),
    Concern_Type VARCHAR(255),
    Concern_Type_Reason VARCHAR(65535),
    Dollar_Amount VARCHAR(255),
    Account_Type VARCHAR(255),
    Lead_Qualification VARCHAR(255),
    Lead_Qualification_Reason VARCHAR(65535),
    Summary VARCHAR(65535)
);

CREATE TABLE public.lead_details (
    lead_details_id VARCHAR PRIMARY KEY,
    lead_id INT REFERENCES public.Lead(Lead_ID) NULL,
    lead_name VARCHAR,
    call_id VARCHAR REFERENCES public.Call(Call_ID) NULL,
    timestamp TIMESTAMP NOT NULL,
    duration VARCHAR(255),
    criteria VARCHAR(255),
    score VARCHAR(65535),
    reason VARCHAR(65535)
);
CREATE TABLE public.broker_dashboard (
    broker_summary_id VARCHAR PRIMARY KEY,
    call_id                 VARCHAR(50),
    timestamp               TIMESTAMP,
    broker_name             VARCHAR(100),
    role                    VARCHAR(100),
    talk_time               INTEGER,
    positives               VARCHAR(65535),
    opportunities           VARCHAR(65535),
    summary                 VARCHAR(65535),
    type                    VARCHAR(50),  -- 'intrinsics' or 'adherence'
    criteria                VARCHAR(65535),
    score                   DECIMAL(5, 2),
    reason                  VARCHAR(65535)
);
CREATE TABLE public.Stage (
    Stage_ID INT PRIMARY KEY,
    Stage_Name VARCHAR(255),
    Description TEXT
);

CREATE TABLE public.Lead (
    Lead_ID INT PRIMARY KEY,
    Source VARCHAR(255),
    Lead_Status VARCHAR(255),
    Lead_Score VARCHAR(255),
    Stage_ID INT REFERENCES public.Stage(Stage_ID),
    Creation_Date TIMESTAMP,
    Notes TEXT
);


CREATE TABLE public.Customer (
    Customer_ID INT PRIMARY KEY,
    Lead_ID INT REFERENCES public.Lead(Lead_ID),
    Name VARCHAR(255),
    Contact_Info VARCHAR(255),
    Region VARCHAR(255),
    Last_Purchase TIMESTAMP,
    Revenue INT,
    Investment_Type VARCHAR(255)
);

CREATE TABLE public.Call (
    Call_ID VARCHAR PRIMARY KEY,
    Call_Platform VARCHAR(255),
    Broker_ID VARCHAR REFERENCES public.Broker(Broker_ID) NULL,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Call_Type VARCHAR(255),
    Call_Forwarded BOOLEAN,
    Date_Time TIMESTAMP,
    Talk_Time INT,
    Outcome VARCHAR(255),
    Transcript TEXT
);

CREATE TABLE public.Broker (
    Broker_ID VARCHAR PRIMARY KEY,
    Broker_Name VARCHAR(255),
    phoneNumber VARCHAR(255),
    email VARCHAR(255),
    extension VARCHAR(255),
    state VARCHAR(255),
    role VARCHAR(255)
);

CREATE TABLE public.Lead (
    Lead_ID INT PRIMARY KEY,
    Source VARCHAR(255),
    Lead_Status VARCHAR(255),
    Lead_Score VARCHAR(255),
    Stage_ID INT REFERENCES public.Stage(Stage_ID),
    Creation_Date TIMESTAMP,
    Notes TEXT
);

DROP TABLE public.Call CASCADE;
DROP TABLE public.Lead CASCADE;
DROP TABLE public.staging_lead CASCADE;

CREATE TABLE public.Lead (
    Lead_ID INT PRIMARY KEY,
    Source VARCHAR,
    Lead_Status VARCHAR,
    Lead_Score VARCHAR,
    Stage_ID INT REFERENCES public.Stage(Stage_ID),
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
    Stage_ID VARCHAR,
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

DROP TABLE public.Call CASCADE;
DROP TABLE public.Lead CASCADE;

CREATE TABLE public.call (
    Call_ID VARCHAR PRIMARY KEY,
    Broker_Name VARCHAR,
    Lead_ID INT REFERENCES public.Lead(Lead_ID) NULL,
    Call_Type VARCHAR(255),
    Date_Time TIMESTAMP,
    Talk_Time INT,
    Outcome VARCHAR(255),
    Call_Segment VARCHAR(255),
    Inbound_Number VARCHAR(255),
    Prospect_Number VARCHAR(255)
);

CREATE TABLE public.staging_call (
    Call_ID VARCHAR PRIMARY KEY,
    Broker_Name VARCHAR,
    Lead_ID VARCHAR,
    Call_Type VARCHAR(255),
    Date_Time VARCHAR(255),
    Talk_Time VARCHAR(255),
    Outcome VARCHAR(255),
    Call_Segment VARCHAR(255),
    Inbound_Number VARCHAR(255),
    Prospect_Number VARCHAR(255)
);

ALTER TABLE public.Call
DROP COLUMN Lead_ID;

ALTER TABLE public.Call
ADD COLUMN Lead_ID VARCHAR REFERENCES public.Lead(Lead_ID) NULL;

TRUNCATE TABLE public.call;

TRUNCATE TABLE public.staging_call;

DROP TABLE public.staging_lead CASCADE;
DROP TABLE public.Lead CASCADE;

DROP TABLE public.Transcript CASCADE;

CREATE TABLE public.Staging_Transcript (
    Transcript_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR,
    Transcript VARCHAR,
    TalkTime_Percentage_A VARCHAR,
    TalkTime_Percentage_B VARCHAR,
    TalkTime_Percentage_C VARCHAR
);

CREATE TABLE public.Transcript (
    Transcript_ID VARCHAR PRIMARY KEY,
    Call_ID VARCHAR REFERENCES public.Call(Call_ID) NULL,
    Transcript_Url VARCHAR
);


TRUNCATE TABLE public.lead;

TRUNCATE TABLE public.staging_lead;


CREATE TABLE public.lead_log (
    Lead_Log_Id VARCHAR PRIMARY KEY,
    Log_Type VARCHAR(255),
    Log_Actor VARCHAR(255),
    Log_Date TIMESTAMP,
    Log_Result VARCHAR(255),
    Log_Note VARCHAR(255),
    Log_Contact VARCHAR(255),
    Lead_ID INT REFERENCES public.Lead(Lead_ID),
    Date_Added TIMESTAMP,
    Email VARCHAR(255),
    Lead_Source VARCHAR(255),
    Campaign_Name VARCHAR(255),
    Affiliate_Name VARCHAR(255),
    Source_Code VARCHAR(255),
    Total_Contact_Attempts INT,
    Creative VARCHAR(255),
    Status VARCHAR(255),
    "User" VARCHAR(255),
    Lead_Score INT,
    Last_Action VARCHAR(255),
    Last_Action_Date TIMESTAMP,
    Last_Contact_Attempt_Date TIMESTAMP,
    IRA_Investment_Dollar FLOAT,
    Cash_Investment_Dollar FLOAT,
    First_Assignment_Distribution_User VARCHAR(255),
    "TO_Date" TIMESTAMP
);

CREATE TABLE public.staging_lead_log (
    Lead_Log_Id VARCHAR PRIMARY KEY,
    Log_Type VARCHAR(255),
    Log_Actor VARCHAR(255),
    Log_Date VARCHAR(255),
    Log_Result VARCHAR(255),
    Log_Note VARCHAR(255),
    Log_Contact VARCHAR(255),
    Lead_ID VARCHAR(255),
    Date_Added VARCHAR(255),
    Email VARCHAR(255),
    Lead_Source VARCHAR(255),
    Campaign_Name VARCHAR(255),
    Affiliate_Name VARCHAR(255),
    Source_Code VARCHAR(255),
    Total_Contact_Attempts VARCHAR(255),
    Creative VARCHAR(255),
    Status VARCHAR(255),
    "User" VARCHAR(255),
    Lead_Score VARCHAR(255),
    Last_Action VARCHAR(255),
    Last_Action_Date VARCHAR(255),
    Last_Contact_Attempt_Date VARCHAR(255),
    IRA_Investment_Dollar VARCHAR(255),
    Cash_Investment_Dollar VARCHAR(255),
    First_Assignment_Distribution_User VARCHAR(255),
    "TO_Date" VARCHAR(255)
);

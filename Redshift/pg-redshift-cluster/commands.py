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

CREATE TABLE public.Lead (
    Lead_ID INT PRIMARY KEY,
    Source VARCHAR(255),
    Lead_Status VARCHAR(255),
    Lead_Score VARCHAR(255),
    Stage_ID INT REFERENCES public.Stage(Stage_ID),
    Milestone VARCHAR(100),
    Broker_Name VARCHAR(255),
    "Group" VARCHAR(100),
    Date_Added TIMESTAMP,
    Last_Action VARCHAR(255),
    First_Contact_Attempt_Date TIMESTAMP,
    Action_Count INT,
    Total_Contact_Attempts INT,
    Last_Action_Date TIMESTAMP,
    First_Assignment_Distribution_Date TIMESTAMP,
    First_Assignment_Distribution_User VARCHAR(100),
    Lead_Source_Group VARCHAR(255),
    Creative VARCHAR(255),
    Broker VARCHAR(100),
    Opener VARCHAR(100),
    IRA_Investment_Dollar VARCHAR(255),
    Cash_Investment_Dollar VARCHAR(255),
    Deal_Type VARCHAR(50),
    Transfer_Type VARCHAR(50),
    "TO_Date" TIMESTAMP,
    SF_Lead_ID VARCHAR(50),
    Velocify_ID VARCHAR(50),
    Original_Broker VARCHAR(100),
    SF_Lead_Owner VARCHAR(100),
    Junior_Broker VARCHAR(100),
    Last_Activity TIMESTAMP,
    Intellect_Client_ID VARCHAR(50),
    Intellect_Broker VARCHAR(100),
    First_Name VARCHAR(100),
    Last_Name VARCHAR(100),
    Home_Phone VARCHAR(50),
    Work_Phone VARCHAR(50),
    Mobile_Phone VARCHAR(50),
    Email VARCHAR(255),
    Secondary_Email VARCHAR(255),
    Address VARCHAR(255),
    City VARCHAR(100),
    State VARCHAR(100),
    Zip_Postal_Code VARCHAR(20),
    Source_Code VARCHAR(50),
    SubID VARCHAR(50)
);
CREATE TABLE public.Staging_Lead (
    Lead_ID VARCHAR PRIMARY KEY,
    Source VARCHAR(255),
    Lead_Status VARCHAR(255),
    Lead_Score VARCHAR(255),
    Stage_ID VARCHAR(255),
    Milestone VARCHAR(100),
    Broker_Name VARCHAR(100),
    "Group" VARCHAR(100),
    Date_Added VARCHAR(255),
    Last_Action VARCHAR(255),
    First_Contact_Attempt_Date VARCHAR(255),
    Action_Count VARCHAR(255),
    Total_Contact_Attempts VARCHAR(255),
    Last_Action_Date VARCHAR(255),
    First_Assignment_Distribution_Date VARCHAR(255),
    First_Assignment_Distribution_User VARCHAR(100),
    Lead_Source_Group VARCHAR(255),
    Creative VARCHAR(255),
    Broker VARCHAR(100),
    Opener VARCHAR(100),
    IRA_Investment_Dollar VARCHAR(255),
    Cash_Investment_Dollar VARCHAR(255),
    Deal_Type VARCHAR(50),
    Transfer_Type VARCHAR(50),
    "TO_Date" VARCHAR(255),
    SF_Lead_ID VARCHAR(50),
    Velocify_ID VARCHAR(50),
    Original_Broker VARCHAR(100),
    SF_Lead_Owner VARCHAR(100),
    Junior_Broker VARCHAR(100),
    Last_Activity VARCHAR(255),
    Intellect_Client_ID VARCHAR(50),
    Intellect_Broker VARCHAR(100),
    First_Name VARCHAR(100),
    Last_Name VARCHAR(100),
    Home_Phone VARCHAR(50),
    Work_Phone VARCHAR(50),
    Mobile_Phone VARCHAR(50),
    Email VARCHAR(255),
    Secondary_Email VARCHAR(255),
    Address VARCHAR(255),
    City VARCHAR(100),
    State VARCHAR(100),
    Zip_Postal_Code VARCHAR(20),
    Source_Code VARCHAR(50),
    SubID VARCHAR(50)
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
    Transcript TEXT,
    TalkTime_Percentage_A INT,
    TalkTime_Percentage_B INT,
    TalkTime_Percentage_C INT
);

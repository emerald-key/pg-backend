// Database schema for Priority Gold

Table call {
  Call_ID varchar [primary key]
  Broker_Name varchar
  Lead_ID int 
  Call_Type varchar(255)
  Date_Time timestamp
  Talk_Time int
  Outcome varchar(255)
  Call_Segment varchar(255)
  Inbound_Number varchar(255)
  Prospect_Number varchar(255)
}

Table Transcript {
  Transcript_ID varchar [primary key]
  Call_ID varchar 
  Transcript_Url varchar
}

Table Lead {
  Lead_ID int [primary key]
  Source varchar
  Lead_Status varchar
  Lead_Score varchar
  Milestone varchar
  Broker_Name varchar
  "Group" varchar
  Date_Added timestamp
  Last_Action varchar
  First_Contact_Attempt_Date timestamp
  Action_Count int
  Total_Contact_Attempts int
  Last_Action_Date timestamp
  First_Assignment_Distribution_Date timestamp
  First_Assignment_Distribution_User varchar
  Lead_Source_Group varchar
  Creative varchar
  Broker varchar
  Opener varchar
  IRA_Investment_Dollar varchar
  Cash_Investment_Dollar varchar
  Deal_Type varchar
  Transfer_Type varchar
  "TO_Date" timestamp
  SF_Lead_ID varchar
  Velocify_ID varchar
  Original_Broker varchar
  SF_Lead_Owner varchar
  Junior_Broker varchar
  Last_Activity timestamp
  Intellect_Client_ID varchar
  Intellect_Broker varchar
  First_Name varchar
  Last_Name varchar
  Home_Phone varchar
  Work_Phone varchar
  Mobile_Phone varchar
  Email varchar
  Secondary_Email varchar
  Address varchar
  City varchar
  State varchar
  Zip_Postal_Code varchar
  Source_Code varchar
  SubID varchar
}



Table Lead_Log {
  Lead_Log_Id varchar [primary key]
  Log_Type varchar
  Log_Actor varchar
  Log_Date timestamp
  Log_Result varchar
  Log_Note varchar
  Log_Contact varchar
  Lead_ID int 
  Campaign_Name varchar
  Affiliate_Name varchar
  Status varchar
  Last_Contact_Attempt_Date timestamp
}

Table Broker {
  Broker_ID varchar [primary key]
  Broker_Name varchar(255)
  phoneNumber varchar(255)
  email varchar(255)
  extension varchar(255)
  state varchar(255)
  role varchar(255)
}

// Relationships
Ref: call.Lead_ID > Lead.Lead_ID // Call-to-Lead Relationship
Ref: Lead_Log.Lead_ID > Lead.Lead_ID // LeadLog-to-Lead Relationship
Ref: Transcript.Call_ID > call.Call_ID

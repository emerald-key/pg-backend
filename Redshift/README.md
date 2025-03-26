# Redshift

This folder contains all the necessary scripts and resources related to Amazon Redshift for managing and modeling data in the **Priority Gold** project.

## Contents

1. **create-tables-commands.sql**  
   Contains SQL commands to create the required tables in Redshift, including:
   - `call`
   - `staging_call`
   - `lead`
   - `staging_lead`
   - `lead_log`
   - `staging_lead_log`
   - `transcript`
   - `broker`

2. **details.py**  
   Holds Redshift cluster configuration details:
   - **Cluster Identifier:** `pg-redshift-cluster`
   - **Node Type:** `dc2.large`
   - **Number of Nodes:** `2`

3. **ERD-Diagram.png**  
   An Entity Relationship Diagram (ERD) visualizing the schema structure.  
   **[View ERD Diagram](./pg-redshift-cluster/ERD-Diagram.png)**

4. **erd-schema.py**  
   A Python script that assists in generating the ERD for dbdiagram.io based on the schema design.

## Purpose

This folder centralizes all resources related to Redshift database management, ensuring seamless data modeling, table creation, and schema visualization for effective data handling in Priority Gold.

- [Root README](../README.md)
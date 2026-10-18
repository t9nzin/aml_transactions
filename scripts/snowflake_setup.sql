-- One-time Snowflake setup for the AML project. Run in a Snowsight worksheet as ACCOUNTADMIN.
-- Replace <your_user> before running.

use role accountadmin;

-- Cap spend: the trial has limited credits. Suspend the warehouse at 20 credits per month.
create resource monitor if not exists aml_monitor
    with credit_quota = 20
    frequency = monthly
    start_timestamp = immediately
    triggers
        on 75 percent do notify
        on 100 percent do suspend;

create warehouse if not exists aml_wh
    warehouse_size = xsmall
    auto_suspend = 60
    auto_resume = true
    initially_suspended = true
    resource_monitor = aml_monitor;

create role if not exists aml_role;
grant role aml_role to user <your_user>;
grant usage, operate on warehouse aml_wh to role aml_role;

create database if not exists aml;
grant ownership on database aml to role aml_role;

use role aml_role;
use database aml;
create schema if not exists raw;

create file format if not exists raw.parquet_format
    type = parquet
    use_logical_type = true;

create stage if not exists raw.partitions_stage
    file_format = raw.parquet_format;

-- Lets the README report credits per pipeline run.
use role accountadmin;
grant imported privileges on database snowflake to role aml_role;

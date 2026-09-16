Project 1 — Beginner: Ecommerce Star Schema with dbt
Problem Statement

A small ecommerce company has raw order, customer, product, and payment data. Analysts need reliable tables for revenue, customer behavior, and product performance.

Motivation

Most companies need clean marts like:

Revenue by month
Top products
Repeat customers
Average order value
Refund rate
Tools
dbt Core
DuckDB
Python
CSV seed data
GitHub
GitHub Actions
Evidence.dev / Metabase optional
Architecture
CSV Seeds
  ↓
dbt Sources
  ↓
Staging
  ↓
Intermediate joins
  ↓
Dimensional Marts
  ↓
Dashboard
Build Steps
Create repo:
mkdir ecommerce-dbt-star-schema
cd ecommerce-dbt-star-schema
python -m venv .venv
pip install dbt-duckdb
dbt init ecommerce_analytics
Add seed files:
seeds/raw_customers.csv
seeds/raw_orders.csv
seeds/raw_order_items.csv
seeds/raw_products.csv
seeds/raw_payments.csv
Create staging models:
stg_customers
stg_orders
stg_order_items
stg_products
stg_payments
Create dimensions:
dim_customers
dim_products
dim_dates
Create facts:
fact_orders
fact_order_items
fact_payments
Add tests:
not_null
unique
relationships
accepted_values
custom revenue >= 0
Generate docs:
dbt docs generate
dbt docs serve
Add CI:
dbt seed
dbt run
dbt test
Skills Demonstrated
Dimensional modeling
dbt project structure
Testing
Documentation
CI/CD basics
Business metric thinking
Stretch Goals
Add SCD Type 2 customer dimension
Add incremental fact table
Add dbt exposures for dashboards
Add semantic metrics
README Outline
# Ecommerce dbt Star Schema

## Problem
## Architecture
## Dataset
## Data Model
## dbt Layers
## Tests
## How to Run
## Dashboard Screenshots
## Key Business Metrics
## Tradeoffs
## Future Improvements
Project 2 — Intermediate: Subscription Analytics with SCD and dbt Semantic Layer
Problem Statement

A SaaS company wants to track subscriptions, upgrades, downgrades, churn, MRR, ARR, and customer lifetime value.

Motivation

Subscription analytics is common in real companies and forces you to handle time, changing customer states, and metric consistency.

Tools
dbt Core
DuckDB or PostgreSQL
Python synthetic data generator
GitHub Actions
Metabase / Superset
Optional: dbt Semantic Layer
Architecture
Synthetic app data
  ↓
Raw schema
  ↓
Staging
  ↓
Snapshots for SCD Type 2
  ↓
Intermediate subscription events
  ↓
Facts and dimensions
  ↓
Metric definitions
  ↓
BI dashboard
Build Steps
Generate synthetic data:
customers
plans
subscriptions
subscription_events
invoices
payments
usage_events
Load to DuckDB/Postgres.
Build staging models:
stg_customers
stg_plans
stg_subscriptions
stg_invoices
stg_usage_events
Add dbt snapshot for customer/plan changes:
{% snapshot customers_snapshot %}

{{
  config(
    target_schema='snapshots',
    unique_key='customer_id',
    strategy='timestamp',
    updated_at='updated_at'
  )
}}

select * from {{ source('raw', 'customers') }}

{% endsnapshot %}
Build marts:
dim_customers_scd
dim_plans
fact_subscription_events
fact_invoices
fact_usage_daily
mart_mrr_monthly
Define metrics:
MRR
ARR
churn_rate
net_revenue_retention
gross_revenue_retention
active_accounts
Add tests:
No duplicate active subscription per customer
Invoice amount >= 0
Subscription status accepted values
MRR reconciliation
Deploy docs and CI.
Skills Demonstrated
SCD Type 2
Temporal modeling
Metric design
dbt snapshots
Incremental thinking
Business-facing analytics
Stretch Goals
Add semantic layer definitions
Add anomaly checks for MRR drops
Add incremental models
Add dbt selectors
Add slim CI
README Outline
# SaaS Subscription Analytics with dbt

## Business Context
## Data Sources
## Architecture
## Modeling Decisions
## SCD Strategy
## Metrics
## Tests and Quality Gates
## Dashboard
## Local Setup
## CI/CD
## Lessons Learned
Project 3 — Advanced: Data Vault to Dimensional Marts with dbt
Problem Statement

A growing company has multiple source systems: CRM, ecommerce, billing, and support. The business wants both auditability and user-friendly analytics.

Motivation

This project shows you understand enterprise-grade modeling: raw history, multiple systems, changing business rules, and downstream marts.

Tools
dbt Core
DuckDB / PostgreSQL
AutomateDV optional
Python synthetic data generator
GitHub Actions
Metabase / Superset
Docker optional
Architecture
CRM / Orders / Billing / Support
  ↓
Raw tables
  ↓
Staging
  ↓
Raw Vault
    Hubs
    Links
    Satellites
  ↓
Business Vault
    PIT tables
    Bridge tables
    Derived satellites
  ↓
Dimensional Marts
    Facts
    Dimensions
  ↓
BI / Semantic Layer
Build Steps
Generate multi-source data:
crm_customers
crm_accounts
orders
order_items
billing_invoices
billing_payments
support_tickets
product_catalog
Define business keys:
customer_id
account_id
order_id
invoice_id
ticket_id
product_id
Build staging models with standard columns:
load_datetime
record_source
hash_key
hashdiff
Build hubs:
hub_customer
hub_account
hub_order
hub_invoice
hub_ticket
hub_product
Build links:
link_customer_account
link_order_customer
link_order_product
link_invoice_customer
link_ticket_customer
Build satellites:
sat_customer_details
sat_account_details
sat_order_status
sat_invoice_status
sat_ticket_status
sat_product_details
Build business vault:
pit_customer
bridge_customer_account
sat_customer_lifecycle
Build dimensional marts:
dim_customers
dim_accounts
dim_products
fact_orders
fact_invoices
fact_support_tickets
mart_customer_360
Add quality checks:
Hash key uniqueness
Satellite hashdiff change detection
No orphan links
Business key not null
Record source populated
Add CI and docs.
Skills Demonstrated
Enterprise modeling
Data Vault
Dimensional marts
dbt automation
History tracking
Auditability
Source-system integration
Architecture tradeoffs
Stretch Goals
Use AutomateDV
Add PIT and bridge tables
Add late-arriving data handling
Add dbt exposures
Add Docker Compose
Add dashboard
Add synthetic CDC events
README Outline
# Data Vault to Dimensional Marts with dbt

## Executive Summary
## Business Problem
## Source Systems
## Architecture Diagram
## Why Data Vault?
## Why Dimensional Marts?
## Model Layers
## Hash Key Strategy
## Testing Strategy
## CI/CD
## Dashboard
## Tradeoffs
## Future Work
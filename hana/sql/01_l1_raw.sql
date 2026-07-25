-- ===========================================================================
-- L1 - RAW / inbound layer
--
-- BW/4HANA analogue: staging ADSO, inbound layer.
--
-- 1:1 with the loaded tables. Projection and explicit typing only: no joins,
-- no filters, no derived columns, no business logic. That restraint is the
-- whole point of the layer - when a number is wrong, L1 is the place you can
-- rule out without reading anything, because there is nothing in it to be
-- wrong. Every transformation lives in L2.
--
-- The one thing L1 does add is a stable column contract. Downstream views bind
-- to these names, so a change in the inbound file shape is absorbed here rather
-- than rippling through the reporting layer.
-- ===========================================================================

CREATE SCHEMA "NOVASPACE_L1";

-- --- dimensions ------------------------------------------------------------

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_COMPANY_CODE" AS
SELECT
  "company_code",
  "company_name",
  "country_key",
  "local_currency",
  "group_currency",
  "soft_close_working_day",
  "hard_close_target_wd"
FROM "NOVASPACE_RAW"."DIM_COMPANY_CODE";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_COST_CENTER" AS
SELECT
  "cost_center",
  "cost_center_name",
  "company_code",
  "division_id",
  "division_name",
  "department_id",
  "department_name",
  "parent_id",
  "hierarchy_level",
  "is_overhead",
  "valid_from",
  "valid_to",
  "manager_user_id"
FROM "NOVASPACE_RAW"."DIM_COST_CENTER";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_PROGRAMME" AS
SELECT
  "programme_id",
  "programme_name",
  "programme_type",
  "lead_company_code",
  "start_date",
  "end_date",
  "total_budget_eur",
  "status"
FROM "NOVASPACE_RAW"."DIM_PROGRAMME";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_GL_ACCOUNT" AS
SELECT
  "gl_account",
  "gl_account_name",
  "account_group",
  "account_group_name",
  "pl_section",
  "is_pl_account",
  "normal_balance"
FROM "NOVASPACE_RAW"."DIM_GL_ACCOUNT";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_DATE" AS
SELECT
  "date_id",
  "calendar_year",
  "calendar_quarter",
  "calendar_month",
  "day_of_month",
  "day_of_week",
  "day_name",
  "is_weekend",
  "is_working_day",
  "fiscal_year",
  "fiscal_period",
  "period_end_date",
  "working_days_after_period_end",
  "working_day_of_period"
FROM "NOVASPACE_RAW"."DIM_DATE";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_CLOSE_TASK" AS
SELECT
  "task_id",
  "task_name",
  "task_sequence",
  "target_working_day",
  "is_milestone"
FROM "NOVASPACE_RAW"."DIM_CLOSE_TASK";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_RATES" AS
SELECT
  "from_currency",
  "to_currency",
  "fiscal_year",
  "fiscal_period",
  "rate_type",
  "exchange_rate"
FROM "NOVASPACE_RAW"."RATES";

-- --- facts -----------------------------------------------------------------

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_JOURNAL" AS
SELECT
  "journal_id",
  "company_code",
  "document_number",
  "document_line",
  "document_type",
  "posting_date",
  "document_date",
  "entry_date",
  "fiscal_year",
  "fiscal_period",
  "gl_account",
  "cost_center",
  "programme_id",
  "debit_credit_ind",
  "amount_doc_currency",
  "doc_currency",
  "amount_local_currency",
  "local_currency",
  "amount_group_currency",
  "group_currency",
  "is_intercompany",
  "ic_partner_company",
  "posting_user_id",
  "is_reversal",
  "reversed_document"
FROM "NOVASPACE_RAW"."FACT_JOURNAL";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_BUDGET" AS
SELECT
  "budget_id",
  "company_code",
  "fiscal_year",
  "cost_center",
  "account_group",
  "programme_id",
  "version",
  "amount_group_currency"
FROM "NOVASPACE_RAW"."FACT_BUDGET";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_FORECAST" AS
SELECT
  "forecast_id",
  "company_code",
  "cost_center",
  "programme_id",
  "fiscal_year",
  "fiscal_period",
  "version",
  "snapshot_date",
  "horizon_periods",
  "amount_group_currency"
FROM "NOVASPACE_RAW"."FACT_FORECAST";

CREATE OR REPLACE VIEW "NOVASPACE_L1"."V_CLOSE_TASKS" AS
SELECT
  "close_task_id",
  "company_code",
  "fiscal_year",
  "fiscal_period",
  "task_id",
  "period_end_date",
  "due_date",
  "actual_completion_date",
  "completed_by_user_id",
  "delay_working_days"
FROM "NOVASPACE_RAW"."FACT_CLOSE_TASKS";

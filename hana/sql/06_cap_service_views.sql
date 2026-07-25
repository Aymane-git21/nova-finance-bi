-- ===========================================================================
-- Service views for the CAP OData layer
--
-- CAP compiles every service entity to a database view and queries *that*, not
-- the entity it projects from. Confirmed from the generated SQL:
--
--   FROM AnalyticsService_ProgrammeBurn as "$P"
--
-- In the normal CAP flow `cds deploy` creates those views inside an HDI
-- container. This project binds to a plain schema instead - the model was built
-- in SQL first and verified against a Python reference, so CAP is the consumer
-- here, not the owner - which means the service views have to exist explicitly.
-- That is what this file is.
--
-- Naming is dictated by CAP, not chosen: <ServiceName>_<EntityName>, unquoted,
-- which HANA folds to upper case. Change a service entity name in
-- cap/srv/analytics-service.cds and the matching view here has to change with
-- it. The pairing is checked by cap/verify_service.py.
--
-- These are pure aliases. Any logic appearing here would mean the layering has
-- broken down: L2 harmonises, L3 reports, API publishes, this republishes under
-- the name CAP insists on.
-- ===========================================================================

CREATE OR REPLACE VIEW NOVASPACE_API.ANALYTICSSERVICE_BUDGETVARIANCE AS
  SELECT * FROM NOVASPACE_API.V_BUDGET_VARIANCE;

CREATE OR REPLACE VIEW NOVASPACE_API.ANALYTICSSERVICE_PROGRAMMEBURN AS
  SELECT * FROM NOVASPACE_API.V_PROGRAMME_BURN;

CREATE OR REPLACE VIEW NOVASPACE_API.ANALYTICSSERVICE_CLOSEMONITOR AS
  SELECT * FROM NOVASPACE_API.V_CLOSE_MONITOR;

CREATE OR REPLACE VIEW NOVASPACE_API.ANALYTICSSERVICE_PLACTUALS AS
  SELECT * FROM NOVASPACE_API.V_PL_ACTUALS;

CREATE OR REPLACE VIEW NOVASPACE_API.ANALYTICSSERVICE_ICRECONCILIATION AS
  SELECT * FROM NOVASPACE_API.V_IC_RECONCILIATION;

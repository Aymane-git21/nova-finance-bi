"""Static configuration for the NovaSpace synthetic dataset.

Everything that the data dictionary states as fact lives here, so that
``docs/data-dictionary.md`` and the generator cannot drift apart silently:
the tests import these constants and assert the generated data matches them.

No randomness in this module. Nothing here depends on the seed.
"""

from __future__ import annotations

import datetime as dt

# --------------------------------------------------------------------------
# Scope
# --------------------------------------------------------------------------

SEED = 42

FIRST_FISCAL_YEAR = 2023
LAST_FISCAL_YEAR = 2026
LAST_CLOSED_PERIOD_IN_FINAL_YEAR = 6  # FY2026 is closed through P6 only

CALENDAR_START = dt.date(FIRST_FISCAL_YEAR, 1, 1)
CALENDAR_END = dt.date(LAST_FISCAL_YEAR, 12, 31)

GROUP_CURRENCY = "EUR"

# Special periods carry year-end adjustments. Only complete fiscal years have
# them: FY2026 has not reached its year-end.
SPECIAL_PERIODS = (13, 14)
YEARS_WITH_SPECIAL_PERIODS = (2023, 2024, 2025)

# Base journal lines per month across all entities, before entity weighting.
# The published figure of ~25k/month is what comes *out*: intercompany mirror
# lines and accrual reversals are generated on top of this base, adding roughly
# 7.5%, and special-period adjustments add a little more again.
TARGET_LINES_PER_MONTH_TOTAL = 23_000

#: Posting volume grows year on year as the group ramps up.
VOLUME_GROWTH = {2023: 1.00, 2024: 1.05, 2025: 1.10, 2026: 1.14}

#: Period-to-period noise on line volume.
VOLUME_NOISE_SIGMA = 0.06

# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------

COMPANY_CODES = [
    {
        "company_code": "NS10",
        "company_name": "NovaSpace España S.A.",
        "country_key": "ES",
        "local_currency": "EUR",
        "group_currency": GROUP_CURRENCY,
        "soft_close_working_day": 4,
        "hard_close_target_wd": 5,
        # Relative posting volume. Not a data-dictionary fact, a generator knob.
        "size_weight": 1.00,
    },
    {
        "company_code": "NS20",
        "company_name": "NovaSpace France S.A.S.",
        "country_key": "FR",
        "local_currency": "EUR",
        "group_currency": GROUP_CURRENCY,
        "soft_close_working_day": 4,
        "hard_close_target_wd": 5,
        "size_weight": 1.25,
    },
    {
        "company_code": "NS30",
        "company_name": "NovaSpace Deutschland GmbH",
        "country_key": "DE",
        "local_currency": "EUR",
        "group_currency": GROUP_CURRENCY,
        "soft_close_working_day": 4,
        "hard_close_target_wd": 5,
        "size_weight": 1.05,
    },
    {
        "company_code": "NS40",
        "company_name": "NovaSpace UK Ltd.",
        "country_key": "GB",
        "local_currency": "GBP",
        "group_currency": GROUP_CURRENCY,
        "soft_close_working_day": 4,
        "hard_close_target_wd": 5,
        "size_weight": 0.85,
    },
]

#: The chronically slow closer. Story #1.
SLOW_CLOSE_ENTITY = "NS30"

#: The only non-EUR entity, and therefore the only source of FX impact. Story #3.
FX_ENTITY = "NS40"

# --------------------------------------------------------------------------
# Cost centre hierarchy
# --------------------------------------------------------------------------

DIVISIONS = [
    ("ENG", "Engineering", False),
    ("MFG", "Manufacturing", False),
    ("PRG", "Programmes & Projects", False),
    ("OPS", "Operations & Ground", False),
    ("COR", "Corporate Functions", True),  # overhead: allocated out at close
]

DEPARTMENTS = {
    "ENG": ["Systems Engineering", "Avionics & Software", "Structures & Thermal"],
    "MFG": ["Assembly Integration & Test", "Machining & Composites"],
    "PRG": ["Programme Management", "Configuration & Quality", "Supply Chain"],
    "OPS": ["Ground Segment Operations", "Launch Campaign Support"],
    "COR": ["Finance & Controlling", "Human Resources", "IT & Digital"],
}

COST_CENTER_NAMES = {
    "ENG": [
        "Systems Design", "Requirements & V&V", "Mission Analysis",
        "Avionics Integration", "Onboard Software", "Simulation & Test Bench",
        "Structural Analysis", "Thermal Control", "Mechanisms",
    ],
    "MFG": [
        "Cleanroom AIT", "Environmental Test", "Harness Manufacturing",
        "CNC Machining", "Composite Layup", "Surface Treatment",
    ],
    "PRG": [
        "Programme Office", "Planning & Scheduling", "Risk Management",
        "Configuration Control", "Product Assurance", "Quality Inspection",
        "Procurement", "Supplier Development", "Logistics",
    ],
    "OPS": [
        "Mission Control", "Ground Station Network", "Flight Dynamics",
        "Launch Site Support", "Transport & Handling",
    ],
    "COR": [
        "Financial Accounting", "Management Control", "Treasury",
        "HR Operations", "Talent & Training",
        "IT Infrastructure", "Business Applications", "Cyber Security",
    ],
}

# --------------------------------------------------------------------------
# Programmes
# --------------------------------------------------------------------------
# All names invented. No real space programme, past or present, is referenced.

PROGRAMMES = [
    {
        "programme_id": "PRG-HELIOS", "programme_name": "Helios-3 Earth Observation Constellation",
        "programme_type": "SATELLITE", "lead_company_code": "NS10",
        "start_date": dt.date(2023, 1, 1), "end_date": dt.date(2027, 12, 31),
        "total_budget_eur": 210_000_000.00, "status": "ACTIVE",
    },
    {
        "programme_id": "PRG-KESTREL", "programme_name": "Kestrel Launcher Development",
        "programme_type": "LAUNCHER", "lead_company_code": "NS20",
        "start_date": dt.date(2023, 1, 1), "end_date": dt.date(2027, 12, 31),
        "total_budget_eur": 184_500_000.00, "status": "ACTIVE",
    },
    {
        "programme_id": "PRG-AURORA", "programme_name": "Aurora Deep-Space Relay",
        "programme_type": "SATELLITE", "lead_company_code": "NS30",
        "start_date": dt.date(2023, 4, 1), "end_date": dt.date(2028, 6, 30),
        "total_budget_eur": 96_000_000.00, "status": "ACTIVE",
    },
    {
        "programme_id": "PRG-TERRA", "programme_name": "TerraScan Ground Segment",
        "programme_type": "GROUND_SEGMENT", "lead_company_code": "NS40",
        "start_date": dt.date(2023, 1, 1), "end_date": dt.date(2026, 12, 31),
        "total_budget_eur": 58_000_000.00, "status": "CLOSING",
    },
    {
        "programme_id": "PRG-MERIDIAN", "programme_name": "Meridian Navigation Payload",
        "programme_type": "SATELLITE", "lead_company_code": "NS20",
        "start_date": dt.date(2023, 7, 1), "end_date": dt.date(2027, 6, 30),
        "total_budget_eur": 74_000_000.00, "status": "ACTIVE",
    },
    {
        "programme_id": "PRG-CASTOR", "programme_name": "Castor Smallsat Platform",
        "programme_type": "SATELLITE", "lead_company_code": "NS10",
        "start_date": dt.date(2024, 1, 1), "end_date": dt.date(2027, 12, 31),
        "total_budget_eur": 42_000_000.00, "status": "ACTIVE",
    },
    {
        "programme_id": "PRG-PHAROS", "programme_name": "Pharos Optical Comms Demonstrator",
        "programme_type": "TECHNOLOGY", "lead_company_code": "NS30",
        "start_date": dt.date(2023, 1, 1), "end_date": dt.date(2025, 12, 31),
        "total_budget_eur": 19_500_000.00, "status": "COMPLETED",
    },
    {
        "programme_id": "PRG-VESTA", "programme_name": "Vesta Propulsion Test Bench",
        "programme_type": "TECHNOLOGY", "lead_company_code": "NS20",
        "start_date": dt.date(2023, 1, 1), "end_date": dt.date(2026, 6, 30),
        "total_budget_eur": 27_000_000.00, "status": "CLOSING",
    },
    {
        "programme_id": "PRG-LYRA", "programme_name": "Lyra Constellation Operations",
        "programme_type": "GROUND_SEGMENT", "lead_company_code": "NS40",
        "start_date": dt.date(2024, 7, 1), "end_date": dt.date(2029, 12, 31),
        "total_budget_eur": 88_000_000.00, "status": "ACTIVE",
    },
    {
        "programme_id": "PRG-BOREAS", "programme_name": "Boreas Polar Weather Satellite",
        "programme_type": "SATELLITE", "lead_company_code": "NS30",
        "start_date": dt.date(2025, 1, 1), "end_date": dt.date(2029, 12, 31),
        "total_budget_eur": 130_000_000.00, "status": "ACTIVE",
    },
]

# The programme that runs away. Story #2.
#
# A 65% overrun ramping in over nine months is squarely in the range real
# launcher development programmes manage. An earlier calibration used 40% over
# twelve months, which averaged out to roughly +9% across the first fiscal year
# - inside the budget noise, so the programme did not actually breach its budget
# and the story existed only in the generator's intent.
OVERSPEND_PROGRAMME = "PRG-KESTREL"
OVERSPEND_START = (2025, 7)
OVERSPEND_PEAK_MULTIPLIER = 1.65
OVERSPEND_RAMP_MONTHS = 9

# Share of cost lines that carry a programme at all.
PROGRAMME_ASSIGNMENT_RATE = 0.70

# A cost centre works on a handful of programmes, not on all of them. Sampling
# programmes freely across the whole portfolio produces a cost centre booking to
# ten programmes in one month, which no engineering team does and which quietly
# multiplies the plan-data grain by an order of magnitude.
PROGRAMMES_PER_COST_CENTER = 3

# --------------------------------------------------------------------------
# G/L accounts
# --------------------------------------------------------------------------

ACCOUNT_GROUPS = [
    # code, name, pl_section, account range start, count, normal balance
    ("REV", "Revenue", "REVENUE", 400000, 15, "H"),
    ("MAT", "Material", "COST_OF_SALES", 500000, 25, "S"),
    ("PER", "Personnel", "COST_OF_SALES", 600000, 30, "S"),
    ("SUB", "Subcontracting", "COST_OF_SALES", 610000, 20, "S"),
    ("OVH", "Overhead", "OPERATING_EXPENSES", 650000, 30, "S"),
    ("DEP", "Depreciation", "OPERATING_EXPENSES", 680000, 15, "S"),
    ("OTH", "Other operating", "OTHER", 690000, 15, "S"),
]

ACCOUNT_NAME_PARTS = {
    "REV": ["Contract revenue", "Milestone revenue", "Service revenue", "Licence income",
            "Study revenue", "Spare parts revenue", "Maintenance revenue"],
    "MAT": ["Raw materials", "Electronic components", "Structural parts", "Propellant",
            "Consumables", "Test equipment", "Packaging"],
    "PER": ["Salaries", "Social charges", "Bonus provision", "Pension cost",
            "Travel allowance", "Training cost", "Temporary staff"],
    "SUB": ["Engineering subcontracting", "Manufacturing subcontracting", "Test services",
            "Consultancy", "Software development services", "Launch services"],
    "OVH": ["Facility cost", "Utilities", "Insurance", "IT services", "Telecom",
            "Maintenance & repair", "Office supplies", "Professional fees"],
    "DEP": ["Depreciation buildings", "Depreciation machinery", "Depreciation test rigs",
            "Depreciation IT hardware", "Amortisation software"],
    "OTH": ["Other operating expense", "Currency loss", "Write-off", "Provision movement",
            "Miscellaneous cost"],
}

ACCOUNT_QUALIFIERS = [
    "Engineering", "Manufacturing", "Programmes", "Operations", "Corporate",
    "Ground segment", "Payload", "Structures", "Avionics", "Quality",
]

# Median line amount in group currency, by account group. Lognormal centre.
#
# Calibrated so the group's financials are internally coherent at this posting
# volume. Two constraints bind:
#
#   1. ~320k journal lines a year describes a company of roughly €1bn revenue,
#      not €14bn. An initial calibration put the average line at €17.5k, which
#      implied a group far too large for its own ledger, cost-centre count and
#      programme portfolio.
#   2. Revenue has to roughly cover cost. The same initial calibration produced
#      €19.6bn of cost against €13.8bn of revenue - a group losing 40% a year,
#      every year, which is the first thing a finance reviewer would notice.
#
# REV therefore sits high enough to give a mid-single-digit margin over total
# cost, which is where an aerospace prime actually operates.
AMOUNT_MEDIAN = {
    "REV": 30_200.0,
    "MAT": 2_400.0,
    "PER": 1_400.0,
    "SUB": 5_600.0,
    "OVH": 650.0,
    "DEP": 1_900.0,
    "OTH": 500.0,
}

# Lognormal sigma per account group. Higher = fatter tail of large postings.
#
# Calibrated down from an initial set that ran up to 1.1. Above about 0.8 the
# top handful of lines carries most of a period's value, so monthly totals swing
# 30% on sampling alone - which is not what a real monthly P&L looks like, and
# which buried the overspending-programme signal under noise. Line amounts are
# genuinely lognormal; they are not *that* lognormal.
AMOUNT_SIGMA = {
    "REV": 0.70, "MAT": 0.65, "PER": 0.45, "SUB": 0.75,
    "OVH": 0.60, "DEP": 0.40, "OTH": 0.70,
}

# --------------------------------------------------------------------------
# Document types
# --------------------------------------------------------------------------
# ``timing`` drives when the posting lands:
#   spread    - uniformly across the period's working days
#   late_third- weighted to the final third of the period
#   period_end- exactly on the period-end date
#
# Only P&L-relevant document types are modelled. Vendor payments (KZ) hit bank
# and AP, which are balance-sheet accounts this dataset does not carry, so KZ
# is deliberately absent rather than posted to a P&L account it never touches.

DOCUMENT_TYPES = [
    # code, description, share, is_manual, timing, entry_wd_profile, account groups
    ("KR", "Vendor invoice",              0.26, False, "spread",     "same_or_next", ["MAT", "SUB", "OVH"]),
    ("RE", "Invoice receipt (logistics)", 0.18, False, "spread",     "same_or_next", ["MAT", "SUB"]),
    ("WA", "Goods issue",                 0.14, False, "spread",     "same_day",     ["MAT"]),
    ("RV", "Billing document",            0.08, False, "late_third", "same_or_next", ["REV"]),
    ("ML", "Payroll posting",             0.06, False, "period_end", "punctual_wd2", ["PER"]),
    ("AF", "Depreciation posting",        0.05, False, "period_end", "punctual_wd2", ["DEP"]),
    ("KA", "Allocation / assessment",     0.06, False, "period_end", "punctual_wd3", ["OVH"]),
    ("IC", "Intercompany charge",         0.05, False, "late_third", "close_wd1_3",  ["SUB", "OVH"]),
    ("SA", "G/L account document",        0.09, True,  "late_third", "close_manual", ["MAT", "PER", "SUB", "OVH", "OTH"]),
    ("SB", "G/L accrual posting",         0.03, True,  "period_end", "close_manual", ["PER", "SUB", "OVH", "OTH"]),
]

MANUAL_DOCUMENT_TYPES = ("SA", "SB")

#: Manual share is lifted for the slow-close entity. Story #1 and #6.
SLOW_ENTITY_MANUAL_UPLIFT = 1.85

#: Document line counts. Mean ≈ 1.72 lines per document.
DOC_LINE_COUNTS = (1, 2, 3, 4)
DOC_LINE_WEIGHTS = (0.55, 0.25, 0.13, 0.07)

# Manual entries land on working day n after period end, n = 1..12.
# The soft close is working day 4, so everything from index 4 onward is a late
# posting under KPI-03. These two distributions are the entire mechanism behind
# stories #1 and #6 - roughly 20% of the baseline manual tail is late against
# 50% for the slow entity.
MANUAL_CLOSE_ENTRY_WEIGHTS = (
    0.12, 0.20, 0.24, 0.24, 0.09, 0.05, 0.025, 0.015, 0.005, 0.005, 0.003, 0.002
)
SLOW_MANUAL_CLOSE_ENTRY_WEIGHTS = (
    0.05, 0.10, 0.15, 0.20, 0.18, 0.12, 0.08, 0.05, 0.03, 0.02, 0.01, 0.01
)

#: Share of accrual (SB) documents reversed in the following period.
ACCRUAL_REVERSAL_RATE = 0.85

#: Year-end adjustment volume in special periods, as a share of annual lines.
SPECIAL_PERIOD_VOLUME_SHARE = 0.015
#: Year-end adjustments are entered between these working days of January.
SPECIAL_PERIOD_ENTRY_WD_RANGE = (5, 16)

# --------------------------------------------------------------------------
# Close calendar
# --------------------------------------------------------------------------

CLOSE_TASKS = [
    ("T01", "Sub-ledger cut-off — Accounts Payable", 1, 1, False),
    ("T02", "Sub-ledger cut-off — Accounts Receivable", 2, 1, False),
    ("T03", "GR/IR clearing", 3, 2, False),
    ("T04", "Payroll posting", 4, 2, False),
    ("T05", "Depreciation run", 5, 2, False),
    ("T06", "Accruals posting", 6, 3, False),
    ("T07", "Overhead allocation cycle", 7, 3, False),
    ("T08", "Intercompany reconciliation", 8, 3, False),
    ("T09", "FX revaluation", 9, 4, False),
    ("T10", "Soft close / reporting cut-off", 10, 4, True),
    ("T11", "Management reporting pack", 11, 5, False),
    ("T12", "Hard close / period lock", 12, 5, True),
]

SOFT_CLOSE_TASK = "T10"
HARD_CLOSE_TASK = "T12"

#: Extra working days the slow entity takes on each close task, [low, high).
SLOW_ENTITY_CLOSE_DELAY = (2, 5)

#: Baseline close-task delay in working days against the due date, and weights.
#: Negative means early - most close tasks land on or just before target.
CLOSE_DELAY_CHOICES = (-1, 0, 1, 2)
CLOSE_DELAY_WEIGHTS = (0.15, 0.55, 0.22, 0.08)

# --------------------------------------------------------------------------
# Currencies and rates
# --------------------------------------------------------------------------

TRANSACTION_CURRENCIES = ["EUR", "GBP", "USD"]

#: Opening rate to EUR at the start of FY2023.
FX_OPENING_RATE = {"EUR": 1.000000, "GBP": 1.168000, "USD": 0.921000}

#: Monthly drift and volatility of the rate against EUR.
FX_DRIFT = {"EUR": 0.0, "GBP": 0.0022, "USD": -0.0009}
FX_VOLATILITY = {"EUR": 0.0, "GBP": 0.0090, "USD": 0.0110}

RATE_TYPE_ACTUAL = "M"   # monthly average
RATE_TYPE_BUDGET = "B"   # frozen at the fiscal year's opening rate

#: Probability a document is raised in a currency other than the entity's local one.
FOREIGN_CURRENCY_RATE = 0.13

# --------------------------------------------------------------------------
# Intercompany
# --------------------------------------------------------------------------

#: Share of intercompany *pairs* that fail to net to zero. Story #4.
IC_MISMATCH_RATE = 0.02
#: Materiality threshold for flagging a mismatch, group currency.
IC_MATERIALITY_EUR = 1_000.00

# How wrong the partner's booking is when it is wrong. Deliberately large: a
# genuine reconciliation item is a disputed charge or a whole missing invoice,
# not a few percent. An earlier calibration used 3-15%, which - once line
# amounts were scaled to a realistic group size - produced differences below the
# materiality threshold, so the mismatches existed in the data and never
# appeared in the KPI.
IC_PERTURBATION_RANGE = (0.20, 0.60)

# --------------------------------------------------------------------------
# Plan data
# --------------------------------------------------------------------------

BUDGET_VERSION = "BUDGET"
FORECAST_VERSIONS = ["FC-Q1", "FC-Q2", "FC-Q3"]
#: Snapshot taken after this period is closed; forecasts every later period.
FORECAST_SNAPSHOT_AFTER_PERIOD = {"FC-Q1": 3, "FC-Q2": 6, "FC-Q3": 9}

# Budget is anchored on the prior year's actuals plus a growth assumption, the
# way real budgets are built. Nothing is artificially depressed for the
# overspending programme: its overrun shows up as variance because the actuals
# ramp away from a budget that was set honestly. A budget rigged to be too low
# would produce the same chart for the wrong reason.
BUDGET_GROWTH_RATE = 0.03
BUDGET_NOISE_SIGMA = 0.08
#: Minimum annual actual for a combination to receive a budget line at all.
BUDGET_MIN_ANNUAL_EUR = 5_000.00

#: Forecast error grows with horizon: sigma = base + slope * horizon_periods.
FORECAST_ERROR_BASE = 0.045
FORECAST_ERROR_SLOPE = 0.021
#: The runaway programme is the one nobody forecasts correctly.
FORECAST_ERROR_OVERSPEND_MULTIPLIER = 2.1

# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------

#: Pseudonymous posting users per entity. No name is ever generated or mapped.
USERS_PER_ENTITY = 30

# --------------------------------------------------------------------------
# Holidays
# --------------------------------------------------------------------------
# One group-wide calendar. Per-country calendars would be more realistic and
# are recorded as a known simplification in docs/data-dictionary.md.

FIXED_HOLIDAYS = [
    (1, 1),    # New Year's Day
    (5, 1),    # Labour Day
    (12, 25),  # Christmas Day
    (12, 26),  # Boxing Day / St Stephen's
]
#: Easter-relative holidays, as offsets in days from Easter Sunday.
EASTER_HOLIDAY_OFFSETS = [-2, +1]  # Good Friday, Easter Monday

# Business requirements

What Kelip Bank's managers need from monthly reporting, written as numbered requirements with acceptance criteria, and traced from each stakeholder question to the KPI, chart or query that answers it.

> **All data is synthetic.** Kelip Bank is a fictional Malaysian digital bank. The people below are roles, not real people, and every figure is simulated.

## Contents

1. [Kelip Bank](#1-kelip-bank)
2. [Scope](#2-scope)
3. [Stakeholders and their questions](#3-stakeholders-and-their-questions)
4. [Requirements](#4-requirements)
5. [Traceability matrix](#5-traceability-matrix)
6. [Assumptions and constraints](#6-assumptions-and-constraints)

## 1. Kelip Bank

Kelip Bank is a digital bank in Malaysia with no branches: customers open and run their accounts in the app, on Android or iOS. It launched to the public on **1 September 2024**, and its financial year is the calendar year.

**Products**

| Product | What it is | Price |
|---|---|---|
| Kelip Savings (CASA) | An instant-access savings account, with DuitNow transfers, bill payments and DuitNow QR | 2.00% a year at launch; 1.85% from 1 August 2025, after Bank Negara Malaysia cut the OPR to 2.75% on 9 July 2025 |
| Fixed deposits | 6 and 12 months, placed from the savings account in the app | 6 months 2.35%, 12 months 2.50% (2.15% and 2.30% from 1 August 2025) |
| Raya FD promotion (RAYA25) | A 6-month fixed deposit sold over Hari Raya 2025, placements 1 March to 31 May 2025 | 3.88% a year |
| Debit card | Linked to the savings account; issued to customers who ask for one, activated in the app | Free |
| Personal financing | Unsecured loans of 3 to 5 years, launched in January 2025, priced by risk grade A to D | 7.5% to 18.5% a year |

**How customers join.** Every applicant goes through the same eKYC journey in the app: verify a phone number, scan their MyKad, pass a selfie liveness check, get eKYC approval, and the account opens. A guided selfie flow was A/B tested from February to April 2026 and rolled out to everyone on 1 May 2026. Applicants come from app stores and word of mouth (organic), Google Search, Meta (Facebook and Instagram), TikTok, a refer-a-friend bonus of RM35 per account opened, and cashback affiliates paid RM18 per account plus a monthly platform fee.

**Where it stands at 31 August 2026**

- 32,574 accounts opened since launch, 30,751 of them still open, and 18,522 customers active in August
- RM132.2m of deposits, 78.2% of them in savings (the CASA ratio)
- RM49.1m of personal financing outstanding across 4,869 loans
- Three credit policies so far: v1 at launch (grades A to C), v2 from July 2025 (opened grade D and thin-file applicants, debt service ratio up to 60%), and v3 from January 2026 (tightened again)

**FY2026 plan.** Six KPIs have a monthly plan: new customers (rising from 1,600 in January to 1,950 in August), monthly active customers (12,100 to 18,000), total deposits (RM69m to RM115m), a CASA ratio of at least 80%, a cost of funds of at most 2.00%, and PAR30 of at most 3.0%.

## 2. Scope

**In scope**

- The six source systems: app analytics, core banking (customers, accounts and month-end balances), the posting engine (ledger), the card processor, the loan management system, and the marketing team's spend spreadsheet
- Monthly reporting from September 2024 to August 2026, in Malaysia time
- The products above, and the audiences in section 3
- A warehouse, a KPI layer and scorecard, data quality checks, a dashboard, an Excel KPI pack, analyses and the documents that go with them, all rebuilt with one command

**Out of scope** (the [solution design](03_solution_design.md) says how a real bank would add each one)

- Real customer data: everything here is simulated
- Real-time or intraday reporting
- A production credit-scoring model
- Row-level security, so that each manager sees only their own area

## 3. Stakeholders and their questions

Eight stakeholders, each with the three questions they most need the reporting to answer. Every question has an ID (Q01 to Q24) that the KPI catalog and the traceability matrix refer to.

| Stakeholder | Role | Decisions the reporting supports |
|---|---|---|
| Executive committee (ExCo) | CEO and the heads below, monthly | Whether the bank is on plan, and where to intervene |
| Head of Growth | Customer acquisition and marketing spend | Which channels to fund, and how much |
| Head of Onboarding | The sign-up journey and eKYC | Which steps to fix, and whether a change worked |
| Head of Product | The app and engagement | What to build to keep customers active |
| Treasurer | Deposits, funding and pricing | Rates, promotions, and the funding mix |
| Head of Cards | The debit card | Activation, spend and declines |
| Head of Credit Risk | Personal financing | Credit policy, risk appetite and collections |
| CFO and FP&A | Financial planning and reporting | Whether the numbers tie out, and what drives income |

### Questions

**Executive committee**

- **Q01.** Are we on plan this month for customers, activity, deposits, funding mix and credit quality?
- **Q02.** What are the few things that most need our attention this month, and who owns each?
- **Q03.** Is our margin holding up: how are net interest income and the cost of funds moving?

**Head of Growth**

- **Q04.** Which acquisition channels bring customers who stay active?
- **Q05.** What does each paid channel cost per new customer, and per customer still active three months later?
- **Q06.** Are applications and new customers growing in line with plan?

**Head of Onboarding**

- **Q07.** Where in the sign-up journey do applicants drop out?
- **Q08.** Did the guided eKYC flow improve completion, without letting more fraud through?
- **Q09.** How long does it take to open an account, and how often does an application go to manual review?

**Head of Product**

- **Q10.** How many customers use Kelip Bank each month, and how much do they use it?
- **Q11.** What early behaviour tells us a new customer will stay active?
- **Q12.** What kinds of customers do we have, and what should we offer each?

**Treasurer**

- **Q13.** How are total deposits and the CASA ratio tracking against plan?
- **Q14.** What did the Raya FD promotion do to the CASA ratio and the cost of funds, and how much of it was new money?
- **Q15.** How much fixed deposit money stays with us when it matures?

**Head of Cards**

- **Q16.** How much do customers spend on the card, and on what?
- **Q17.** How quickly do new customers activate their card?
- **Q18.** How many card transactions are declined, and why?

**Head of Credit Risk**

- **Q19.** How is the loan book growing, and which monthly vintages have gone past our risk appetite?
- **Q20.** Did the looser v2 credit policy raise delinquency?
- **Q21.** Where are arrears heading: do late loans cure, or roll on to impairment?

**CFO and FP&A**

- **Q22.** Can we have the monthly KPIs in Excel, with numbers that tie to the dashboard and the ledger?
- **Q23.** How is net interest income moving, and how much of that is the cost of funds?
- **Q24.** Is the marketing spend complete and correctly totalled before we report cost per customer?

## 4. Requirements

Each requirement has acceptance criteria that can be tested, and a pointer to where the project meets it. "Must" requirements are in the definition of done; "Should" requirements are met but would be the first to trim.

### Reporting

**BR-01 Executive scorecard** (Must; Q01, Q02)
The six plan KPIs, each month, with actual, plan, % of plan, variance, prior month and a red, amber or green status.
- Status follows each KPI's direction (higher or lower is better) and its amber band from the KPI catalog.
- Status is always shown as an icon and a word as well as a colour.
- The same figures appear in the warehouse (`kpi.scorecard`), on the dashboard's Executive page and in the Excel pack.
- *Met by:* `sql/03_kpi/08_scorecard.sql`, the Executive page, the Excel pack's Scorecard sheet.

**BR-02 KPI definitions** (Must; all questions)
About 20 KPIs, each with a definition, formula, owner, unit, direction, amber band, target or monthly plan, and SQL source.
- Every KPI in the catalog has values in the warehouse, and every scorecard KPI has a plan for the latest month (check `kpi_catalog_coverage`).
- Every KPI traces to at least one question in section 3.
- *Met by:* [`data/reference/kpi_catalog.csv`](../data/reference/kpi_catalog.csv), the [KPI dictionary](05_kpi_dictionary.md).

**BR-03 Acquisition economics** (Must; Q04, Q05, Q06, Q24)
Applications, new customers, spend, cost per new customer and cost per customer still active in month 3, by channel and month.
- Cost per customer is blank, not understated, for a month with a missing invoice.
- *Met by:* `kpi.channel_monthly`, analysis 1, ad-hoc query 01, the Growth page.

**BR-04 Onboarding funnel and experiment readout** (Must; Q07, Q08, Q09)
The share of applicants reaching each sign-up step by month and eKYC flow, and a readout of the eKYC A/B test.
- The test's primary metric, guardrail and decision rule are written down before the results are read, and a sample-ratio check runs first.
- *Met by:* `marts.fct_onboarding_funnel`, `reference.experiments`, analysis 2, ad-hoc query 05, the Growth page.

**BR-05 Engagement** (Must; Q10, Q11, Q12)
Monthly active customers, the active customer rate, transactions per active customer, and customer segments with an action and owner for each.
- "Active" means at least one transaction the customer made themselves, not interest or salary received.
- *Met by:* `kpi.engagement_monthly`, analysis 5, the Engagement page.

**BR-06 Deposits and funding** (Must; Q13, Q14, Q15, Q23)
Total deposits, the CASA ratio, cost of funds, promotion balances, and fixed deposit money kept 30 days after maturity.
- Cost of funds is annualised from interest accrued on average balances.
- *Met by:* `kpi.deposits_monthly`, `kpi.fd_maturity_outcomes`, analysis 3, ad-hoc query 02, the Deposits page.

**BR-07 Cards** (Should; Q16, Q17, Q18)
Card spend by month and merchant category, card activation within 30 days, the approval rate and declines by reason.
- Card activation is only reported for months in which every customer has had the full 30 days.
- *Met by:* `kpi.cards_monthly`, `kpi.card_categories_monthly`, ad-hoc query 03, the Engagement page.

**BR-08 Credit** (Must; Q19, Q20, Q21)
Gross loans, disbursements, PAR30, the GIL ratio, vintage curves by credit policy, and roll rates between arrears buckets.
- Days past due agree with instalments in arrears (check `dpd_matches_arrears`).
- *Met by:* `kpi.credit_monthly`, `kpi.vintage_curves`, `kpi.roll_rates`, analysis 4, ad-hoc query 04, the Credit page.

**BR-09 Net interest income** (Should; Q03, Q23)
Loan interest income, deposit interest expense and net interest income by month, on an accrual basis.
- *Met by:* `kpi.finance_monthly`.

**BR-10 Findings and recommendations** (Must; Q02)
A monthly insights report with five findings, each with its evidence, a recommendation, an owner and a measure of success.
- Every number in the report comes from the warehouse, so it updates with the data.
- *Met by:* the [insights report](../reports/insights_report.md).

### Delivery

**BR-11 Dashboard** (Must; Q01 to Q21)
A Tableau Public dashboard with an Executive page and four department pages (Growth, Engagement, Deposits, Credit).
- Uses a colour-blind-safe palette, never shows status by colour alone, and never uses a dual axis.
- Comes with a [user manual](06_dashboard_user_manual.md) and [build notes](../dashboards/tableau_build_notes.md).
- *Met by:* the extracts in `dashboards/extracts/`, built into Tableau as described in the build notes.

**BR-12 Excel KPI pack** (Must; Q22)
A workbook with the scorecard, a trend chart and all KPIs by month, driven by live formulas, with conditional formatting and one chart.
- It opens with zero formula errors, and its values and totals match the warehouse (checked on every run in LibreOffice).
- *Met by:* [`reports/kelip_bank_kpi_pack.xlsx`](../reports/kelip_bank_kpi_pack.xlsx), [its check](../reports/excel_pack_check.md).

### Data

**BR-13 Data quality** (Must; Q22, Q24)
Checks on the warehouse, each graded error, warn or info, each returning the rows that fail.
- An error stops the build before anything is published; warnings are reported.
- Every error and warning check is proved to work by breaking the data on purpose.
- *Met by:* `sql/tests/`, the [data quality report](../reports/data_quality_report.md), the [break-test report](../reports/break_test_report.md).

**BR-14 Reconciliations** (Must; Q22)
Two reconciliations that tie to the sen: ledger postings to month-end balances, and the card processor to the ledger.
- *Met by:* checks `recon_ledger_to_balances` and `recon_card_processor_to_ledger`, and `dq.recon_deposits_monthly` and `dq.recon_cards_monthly`.

**BR-15 Malaysia time** (Must; all)
Every date and month-end cut-off uses Malaysia time (UTC+8), whatever time zone the source used.
- *Met by:* the staging layer; reconciliation 1 fails if any posting is put in the wrong month.

### Running it

**BR-16 One command, repeatable** (Must)
One command rebuilds everything from the raw files in under five minutes, and two runs give identical outputs.
- *Met by:* [`run_pipeline.py`](../run_pipeline.py); CI reruns the pipeline and compares every output file.

**BR-17 Automated checks** (Must)
Every push to GitHub rebuilds the project and runs the checks, break-tests and link check, with a status badge in the README.
- *Met by:* [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

**BR-18 Documentation** (Must)
Requirements, data sources, solution design, data and KPI dictionaries, a dashboard user manual, a glossary and a decision log.
- The dictionaries are generated from the warehouse and the catalog, so they cannot drift from the tables.
- *Met by:* the [`docs/`](.) folder.

**BR-19 Labelled as synthetic** (Must)
Every output says that the data is synthetic and that Kelip Bank is fictional: the README, reports, charts, dashboard pages and the Excel pack.

## 5. Traceability matrix

From each question to the requirement, the KPIs and the place that answers it. Dashboard pages are described in the [user manual](06_dashboard_user_manual.md); analyses are the numbered findings in the [insights report](../reports/insights_report.md).

| Question | Requirement | KPIs | Answered in |
|---|---|---|---|
| Q01 On plan this month? | BR-01 | K02, K07, K13, K14, K19 | Executive page; Excel Scorecard sheet |
| Q02 What needs attention? | BR-01, BR-10 | (all scorecard KPIs) | Executive page callouts; insights report |
| Q03 Margin holding up? | BR-09 | K15, K22 | Executive page; Deposits page |
| Q04 Channels whose customers stay | BR-03 | K06 | Growth page; analysis 1 |
| Q05 Cost per new and per retained customer | BR-03 | K05, K06 | Growth page; analysis 1; ad-hoc query 01 |
| Q06 Applications and customers against plan | BR-03 | K01, K02 | Growth page |
| Q07 Where applicants drop out | BR-04 | K01, K03, K04 | Growth page; analysis 2 |
| Q08 Did the guided flow work? | BR-04 | K03, K04 | Growth page; analysis 2 |
| Q09 Time to open, manual review | BR-04 | (none) | Ad-hoc query 05 |
| Q10 How many use us, how much | BR-05 | K07, K08, K09 | Engagement page |
| Q11 Early signs a customer stays | BR-05 | K06, K10 | Analysis 1 (card activation); Engagement page |
| Q12 Kinds of customers, offers | BR-05 | K09 | Analysis 5; Engagement page |
| Q13 Deposits and CASA against plan | BR-06 | K13, K14 | Deposits page; Excel Scorecard sheet |
| Q14 What the Raya promotion did | BR-06 | K14, K15 | Analysis 3; ad-hoc query 02; Deposits page |
| Q15 FD money kept at maturity | BR-06 | K16 | Analysis 3; Deposits page |
| Q16 Card spend and categories | BR-07 | K11 | Engagement page; ad-hoc query 03 |
| Q17 Card activation | BR-07 | K10 | Engagement page |
| Q18 Declines and reasons | BR-07 | K12 | Engagement page |
| Q19 Loan book growth, vintages past appetite | BR-08 | K17, K18, K21 | Credit page; ad-hoc query 04 |
| Q20 Did v2 raise delinquency? | BR-08 | K19, K21 | Analysis 4; Credit page |
| Q21 Arrears: cure or roll? | BR-08 | K19, K20 | Analysis 4; Credit page |
| Q22 KPIs in Excel that tie out | BR-12, BR-13, BR-14 | (all) | Excel pack and its Checks sheet; reconciliations |
| Q23 Net interest income and cost of funds | BR-06, BR-09 | K15, K22 | Deposits page; `kpi.finance_monthly` |
| Q24 Marketing spend complete and totalled | BR-03, BR-13 | K05 | Checks `marketing_invoices_missing` and `marketing_sheet_total_foots` |

Every KPI answers at least one question: the catalog's `stakeholder_questions` column holds the links in the other direction, and the [KPI dictionary](05_kpi_dictionary.md) lists them for each KPI.

## 6. Assumptions and constraints

- **Data.** The source files are simulated by a seeded generator, with five stories planted in them on purpose (see the [data sources](02_data_sources.md)). Rates and events are anchored to real Malaysian ones where it matters, such as the July 2025 OPR cut.
- **Month-end.** Figures are for complete calendar months. Measures that need time to observe (month-3 activity, card activation within 30 days, fixed deposit retention, month-6 delinquency) appear once their window has closed.
- **Tools.** Only free tools: Python, DuckDB, Tableau Public, Excel files built with openpyxl, and GitHub Actions.
- **Privacy.** There is no personal data. A real bank would add access controls, masking and retention rules to meet the Personal Data Protection Act 2010 and Bank Negara Malaysia's requirements.

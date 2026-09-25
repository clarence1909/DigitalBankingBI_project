# Dashboard user manual

How to read and use the Kelip Bank dashboard and the Excel KPI pack. It is written for the people who use them: the executive committee and the heads of Growth, Onboarding, Product, Cards, Treasury, Credit Risk and Finance.

> **All data is synthetic.** Kelip Bank is a fictional Malaysian digital bank, and every figure is simulated. The dashboard is a portfolio piece that shows how a bank's monthly reporting could work.

## Contents

1. [What the dashboard is for](#1-what-the-dashboard-is-for)
2. [Opening it](#2-opening-it)
3. [Reading status](#3-reading-status)
4. [The five pages](#4-the-five-pages)
5. [Filters and clicks](#5-filters-and-clicks)
6. [The Excel KPI pack](#6-the-excel-kpi-pack)
7. [Can I trust the numbers?](#7-can-i-trust-the-numbers)
8. [Common questions](#8-common-questions)
9. [Who to ask](#9-who-to-ask)

## 1. What the dashboard is for

The dashboard answers one question for each reader: **are we on plan this month, and if not, where should we look?**

- **Coverage:** September 2024, when Kelip Bank launched, to August 2026, month by month.
- **Time zone:** every date is Malaysia time (UTC+8). A transaction at 11 pm on 31 March counts in March, even though the source system recorded it in UTC as 3 pm.
- **Refresh:** monthly, once the month's data is complete. One command rebuilds everything from the source files (`python run_pipeline.py`), and the dashboard is republished from the new extracts.
- **Definitions:** every KPI is defined, with its formula, owner and target, in the [KPI dictionary](05_kpi_dictionary.md).

## 2. Opening it

- **Dashboard:** open the Tableau Public link in the [README](../README.md) in any web browser. No account or licence is needed to view it.
- **Excel KPI pack:** download [`reports/kelip_bank_kpi_pack.xlsx`](../reports/kelip_bank_kpi_pack.xlsx) and open it in Excel 2010 or later, LibreOffice or Google Sheets. See [section 6](#6-the-excel-kpi-pack).
- **Picture of the Executive page:** [`reports/charts/00_executive_scorecard.png`](../reports/charts/00_executive_scorecard.png), rebuilt with every run, for slides and emails.

## 3. Reading status

Six KPIs have a monthly plan: new customers, monthly active customers, total deposits, the CASA ratio, cost of funds and PAR30. Each month each one gets a status.

| Status | Icon | Colour | Means |
|---|---|---|---|
| On plan | ▲ | Green | At plan or better |
| Watch | ● | Amber | Worse than plan, but within the KPI's amber band |
| Off plan | ▼ | Red | Worse than plan by more than the amber band |

Three things to know:

- **"Better" depends on the KPI.** For customers and deposits, higher is better. For cost of funds and PAR30, lower is better, so a cost of funds of 1.94% against a 2.00% plan is on plan.
- **The amber band is a share of plan,** set per KPI in the catalog. For the CASA ratio it is 5%, so against an 80% plan anything from 76% to just under 80% is Watch.
- **Status never relies on colour alone.** The icon and the word always appear with the colour, so the status reads the same in print, on a phone and for colour-blind readers.

"Change on prior month" says whether the KPI moved the right way since the month before: Better, Worse or Flat (moved by 0.1% of its value or less).

## 4. The five pages

### Executive

For the executive committee. Six tiles show each plan KPI's value, plan, % of plan and status for the month you pick; below them, each KPI's trend against plan; on the right, the month's three headline findings.

**How to use it:** read the tiles first. A Watch or Off plan tile is the prompt to click through to that KPI's department page.

### Growth

For the Head of Growth and the Head of Onboarding.

- **Cost per new customer against cost per retained customer, by channel.** The headline chart. A channel can be cheap per sign-up and expensive per customer who stays, because many of its customers stop using the account. Judge channels on the cost per customer still active in month 3.
- **New customers by channel against plan.**
- **The sign-up funnel,** the share of applicants reaching each step, with the eKYC A/B test's two flows side by side.
- **Onboarding conversion and eKYC completion** against their targets.

### Engagement

For the Head of Product and the Head of Cards.

- **Monthly active customers against plan.** "Active" means the customer made at least one transaction themselves (a transfer, bill payment, card purchase or fixed deposit placement); interest and incoming salary do not count.
- **Active customer rate and transactions per active customer.**
- **Card spend by merchant category, card activation within 30 days, and declines by reason.**
- **Customer segments,** with each segment's share of customers, deposits and card spend, and the action and owner for each (in the tooltip).

### Deposits

For the Treasurer.

- **Total deposits against plan.**
- **CASA ratio and cost of funds against plan,** one above the other on the same months. The shaded band marks the Raya FD promotion (March to May 2025).
- **Savings, standard fixed deposits and promotion deposits,** stacked.
- **Money kept at maturity:** the share of fixed deposit money still with the bank 30 days after it matured, promotion against standard deposits.

### Credit

For the Head of Credit Risk.

- **Gross loans and financing disbursed.**
- **PAR30 against plan, and the GIL ratio against its target.** PAR30 is the share of the loan book 30 or more days past due; GIL is the share more than 90 days past due.
- **Vintage curves by credit policy.** The headline chart. Each line follows the loans approved under one policy and shows the share that have ever been 30 or more days past due, month by month since they were paid out. A line above another means that policy's loans go bad faster.
- **Roll rates:** of the loans in each arrears bucket one month, the share that moved to each bucket the next month.

## 5. Filters and clicks

- **Reporting month** (top right of the Executive page) sets the month for the tiles. It opens on the latest complete month.
- **Channel** (Growth page) filters the channel charts. Colours stay with the channel whatever you filter, so TikTok is always the same colour.
- **Click a tile** on the Executive page to go to that KPI's department page.
- **Hover** over any mark for the exact value, the month and, where it helps, the KPI's definition.
- **Download:** the toolbar under the dashboard downloads an image, a PDF or the data behind a chart.

## 6. The Excel KPI pack

A workbook with the same numbers, for people who work in Excel. It is built by the pipeline from the warehouse, and every figure on its report sheets is a live formula.

| Sheet | What it shows |
|---|---|
| Cover | What is in the pack, how to use it, and the colour key |
| Scorecard | The six plan KPIs for the month you pick: actual, plan, % of plan, variance, status, prior month and change |
| Trend | One scorecard KPI against plan by month, January 2025 to August 2026, with a chart |
| Monthly KPIs | All 22 KPIs for all 24 months; the month picked on Scorecard is shaded |
| Checks | The pack's totals tied to control totals from the warehouse; every row should say PASS |
| KPI data, Plan, KPI catalog | The data the formulas read |

**To use it:** pick a month in the yellow cell on Scorecard, and a KPI in the yellow cell on Trend. Everything else recalculates. Blue text is data exported from the warehouse; black text is a formula; yellow cells are the choices you can change.

## 7. Can I trust the numbers?

Every rebuild runs these checks, and a failed blocking check stops the rebuild before anything is published:

- **26 data quality checks** on the warehouse, from unique keys to funnel steps in the right order ([results](../reports/data_quality_report.md)). Warnings do not stop the build but are shown: at the moment, one missing marketing invoice and one typing error in the marketing spreadsheet's total.
- **Two reconciliations that tie to the sen:** every deposit account's month-end balance equals the sum of its ledger postings, and every settled card purchase in the card processor's file matches a ledger posting.
- **The Excel pack is recalculated and compared with the warehouse:** 0 formula errors, and every value matches ([results](../reports/excel_pack_check.md)).
- **All 24 error and warning checks were proved to work** by breaking the data on purpose and confirming each one caught it ([results](../reports/break_test_report.md)).

## 8. Common questions

**Why is there no cost per new customer for August 2026?**
The Meta invoice for August had not arrived when the data was cut, so August's marketing spend is incomplete. Rather than show a figure that is too low, the KPI stays blank until the invoice is in.

**Why is card activation within 30 days blank for the latest month?**
Customers who opened late in the month have not had 30 days yet. The KPI appears once every customer in that month's intake has had the full 30 days.

**Why did the CASA ratio fall so far in 2025?**
The Raya fixed deposit promotion (3.88% for six months, March to May 2025) drew most of its money out of customers' own Kelip savings. See finding 3 in the [insights report](../reports/insights_report.md).

**Why does card spend in the dashboard differ from the card processor's report?**
The dashboard counts a purchase when it settles to the account (the finance view). A purchase made on 31 August that settles on 2 September counts in September. The reconciliation matches every purchase whichever month it lands in.

**Why do the newest months have no month-3 active rate, FD retention or month-6 delinquency?**
Each needs time to observe: three months after opening, 30 days after maturity, six months after a loan is paid out. The newest cohorts join once their window closes.

## 9. Who to ask

- **What a KPI means or what its target is:** the KPI's owner, listed in the [KPI dictionary](05_kpi_dictionary.md).
- **A number that looks wrong, or a new question:** the BI team, through the project's [GitHub issues](https://github.com/clarence1909/DigitalBankingBI_project/issues). Say which page, which chart, which month and what you expected.

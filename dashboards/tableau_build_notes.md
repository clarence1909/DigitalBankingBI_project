# Tableau build notes

How to build the Kelip Bank dashboard in Tableau Desktop Public Edition (the free Tableau app) from the CSV extracts in [`extracts/`](extracts/), and publish it on Tableau Public, page by page. It takes about six to eight hours the first time. The finished dashboard has five pages: Executive, Growth, Engagement, Deposits and Credit.

> **All data is synthetic.** Kelip Bank is a fictional Malaysian digital bank. Every page carries the line "Synthetic data: Kelip Bank is fictional" in its footer.

The Executive page should end up looking like the pipeline's own rendering of it, [`reports/charts/00_executive_scorecard.png`](../reports/charts/00_executive_scorecard.png). Use that picture as the target.

## Contents

1. [Set up](#1-set-up)
2. [Connect the data](#2-connect-the-data)
3. [Calculated fields and parameters](#3-calculated-fields-and-parameters)
4. [Executive page](#4-executive-page)
5. [Growth page](#5-growth-page)
6. [Engagement page](#6-engagement-page)
7. [Deposits page](#7-deposits-page)
8. [Credit page](#8-credit-page)
9. [Check the numbers, then publish](#9-check-the-numbers-then-publish)
10. [Refresh after the data changes](#10-refresh-after-the-data-changes)

## House rules for every page

These rules keep the dashboard readable and accessible. Check each sheet against them before you move on.

- **Title each chart with its takeaway**, not its contents: "The CASA ratio is back within 2 points of plan", not "CASA ratio by month".
- **Status is never colour alone.** Every red, amber or green mark has the icon (▲ on plan, ● watch, ▼ off plan) and the word next to it.
- **One axis per chart.** Never use a dual axis with two different measures. Two measures of different scale get two charts, one above the other, sharing the month axis.
- **Colours follow the thing, not its rank.** TikTok is the same colour on every page, whatever else is filtered.
- **Thin marks, light gridlines.** Lines 2 px, gridlines a pale grey hairline, no borders around charts.
- **Label the latest value directly** on line charts, and keep a legend whenever there are two or more lines.
- **Text is dark grey or black**, never the colour of a series.

## 1. Set up

1. Download and install **Tableau Desktop Public Edition** (the free desktop app, once called Tableau Public) from [public.tableau.com](https://public.tableau.com/app/discover), and create your Tableau Public profile.
2. Get the extracts. Either clone the repository, or run `python run_pipeline.py` to rebuild them. They are in `dashboards/extracts/`.
3. Add the Kelip colour palettes, so they appear in Tableau's colour menus:
   1. Close Tableau.
   2. Open `Preferences.tps` in a text editor (Notepad is fine). It is in `Documents/My Tableau Public Repository/` (or `Documents/My Tableau Repository/` in some versions; use the one that exists).
   3. Replace its contents with the XML below, then save.
   4. Start Tableau again. The palettes appear under **Edit Colors > Select Color Palette**.

```xml
<?xml version='1.0'?>
<workbook>
  <preferences>
    <color-palette name="Kelip categorical" type="regular">
      <color>#2a78d6</color>
      <color>#eb6834</color>
      <color>#1baf7a</color>
      <color>#eda100</color>
      <color>#e87ba4</color>
      <color>#008300</color>
      <color>#4a3aa7</color>
      <color>#e34948</color>
    </color-palette>
    <color-palette name="Kelip status" type="regular">
      <color>#0ca30c</color>
      <color>#fab219</color>
      <color>#d03b3b</color>
    </color-palette>
    <color-palette name="Kelip blues" type="ordered-sequential">
      <color>#cde2fb</color>
      <color>#86b6ef</color>
      <color>#3987e5</color>
      <color>#2a78d6</color>
      <color>#1c5cab</color>
      <color>#104281</color>
    </color-palette>
  </preferences>
</workbook>
```

The categorical palette is colour-blind safe in this order, so assign colours in this order and never shuffle them. Use it for at most six series on one chart; beyond that, group the smallest into "Other".

| Use | Colour |
|---|---|
| Actual (any single-series line or bar) | Blue `#2a78d6` |
| Plan or target line | Grey `#898781`, dashed |
| Context series (for example, the control group) | Light grey `#b9b8b0` |
| Status: on plan, watch, off plan | `#0ca30c`, `#fab219`, `#d03b3b`, always with the icon and word |
| Chart background | `#fcfcfb` |
| Gridlines | `#e1e0d9` |
| Text | `#0b0b0b` for values, `#52514e` for labels |

4. Pick the font: **Format > Workbook**, set every font to **Tableau Book** (or Arial), dark grey `#52514e` for axis labels and `#0b0b0b` for titles.

## 2. Connect the data

1. Start page > **Connect > To a File > Text file**, and open `dashboards/extracts/scorecard.csv`.
2. If an icon (▲ ● ▼) shows as a strange character, right-click the connection > **Text File Properties** > **Character Set: UTF-8**.
3. Add the other files. Each file is its own data source (**Data > New Data Source > Text file**), except the KPI catalog, which is related to `kpi_monthly` on `kpi_id` so its definitions and targets can go in tooltips. The files are already summarised, so relating the others would only multiply rows.

| File | What it holds | Data source |
|---|---|---|
| `scorecard.csv` | Six plan KPIs by month: actual, plan, % of plan, status and icon, prior month | scorecard |
| `kpi_monthly.csv` | All 22 KPIs by month, long format, with plan and status where there is one | kpi_monthly |
| `kpi_catalog.csv` | Each KPI's definition, formula, owner, unit, direction and target | kpi_monthly (related on `kpi_id`) |
| `growth_channels.csv` | Applications, customers, spend and month-3 activity by channel and cohort month | growth_channels |
| `onboarding_funnel.csv` | Applicants reaching each sign-up step, by start month and eKYC flow | onboarding_funnel |
| `engagement_monthly.csv` | Open and active customers, transactions per active customer | engagement_monthly |
| `cards_monthly.csv` | Card spend, purchases, approvals, declines, activation | cards_monthly |
| `card_categories_monthly.csv` | Card spend by merchant category | card_categories_monthly |
| `customer_segments.csv` | The six customer segments with their share of customers, deposits and spend | customer_segments |
| `deposits_monthly.csv` | Savings, fixed deposit and promotion balances, CASA ratio, cost of funds | deposits_monthly |
| `fd_maturity_outcomes.csv` | Fixed deposit money matured, rolled over, kept and lost, by month | fd_maturity_outcomes |
| `credit_monthly.csv` | Gross loans, disbursements, PAR30, GIL ratio, early delinquency | credit_monthly |
| `vintage_curves.csv` | Share of each vintage ever 30+ days past due, by month on book | vintage_curves |
| `roll_rates.csv` | Loans moving between arrears buckets from one month to the next | roll_rates |
| `finance_monthly.csv` | Loan interest income, deposit interest expense, net interest income | finance_monthly |

4. In each data source, check the field types: every `month_start`, `start_month`, `vintage_month` and `maturity_month` must be a **Date** (click the icon above the column to change it); `kpi_id`, `status` and `channel` are **Strings**.
5. Set default number formats once, so every sheet inherits them (right-click the field > **Default Properties > Number Format**):
   - money fields (`value` where the unit is RM, `spend`, `card_spend`, `total_deposits`, `gross_loans`): Currency (custom), prefix `RM`, display units Millions, one decimal place
   - ratios (`casa_ratio`, `cost_of_funds`, `par30`, `gil_ratio`, `pct_of_plan`, `m3_active_rate`): Percentage, one decimal place (two for `cost_of_funds` and `par30`)
   - counts: Number (custom), no decimals, thousands separator

## 3. Calculated fields and parameters

Create these once (**Analysis > Create Calculated Field**) in the data source named in brackets. They reuse the warehouse's logic rather than rebuilding it, so the dashboard and the Excel pack cannot disagree.

**Parameter: Reporting month** (Date). Right-click in the Data pane > **Create Parameter**: Data type **Date**, Allowable values **List**, **Add values from > scorecard > month_start**, current value **1 Aug 2026**, display format **Month Year**. Right-click it > **Show Parameter**.

| Name | Data source | Formula |
|---|---|---|
| `Is reporting month` | scorecard | `[month_start] = [Reporting month]` |
| `Status text` | scorecard | `[status_icon] + " " + [status_label]` |
| `Value shown` | scorecard | `IF [unit] = "pct" THEN STR(ROUND([actual] * 100, 2)) + "%" ELSEIF [unit] = "rm" THEN "RM" + STR(ROUND([actual] / 1000000, 1)) + "m" ELSE STR(ROUND([actual], 0)) END` |
| `Plan shown` | scorecard | the same as `Value shown`, with `[plan]` in place of `[actual]` |
| `Plan line` | kpi_monthly | `[plan]` (only the six scorecard KPIs have one) |
| `Cost per retained customer` | growth_channels | `SUM([spend]) / SUM([m3_active_customers])` |
| `Cost per new customer` | growth_channels | `SUM([spend]) / SUM([new_customers])` |
| `Month-3 active rate` | growth_channels | `SUM([m3_active_customers]) / SUM([new_customers])` |
| `Reached step` | onboarding_funnel | `SUM([applicants]) / {FIXED [start_month], [ekyc_flow], [is_in_ekyc_test] : SUM(IF [step_no] = 1 THEN [applicants] END)}` |
| `Promotion share` | deposits_monthly | `SUM([promo_fd_balance]) / SUM([total_deposits])` |
| `Kept 30 days` | fd_maturity_outcomes | `SUM([retained_30d]) / SUM([matured_amount])` |
| `Roll rate` | roll_rates | `SUM([loans]) / SUM({FIXED [month_start], [from_bucket] : SUM([loans])})` |

Status colours: when a sheet colours by `status`, click the colour legend > **Edit Colors**, choose the **Kelip status** palette, and assign GREEN `#0ca30c`, AMBER `#fab219`, RED `#d03b3b`.

## 4. Executive page

**Question it answers:** are we on plan this month, and what needs attention? (ExCo, questions Q01 to Q03 in the [business requirements](../docs/01_business_requirements.md).)

### Sheet E1: KPI tiles

A tile per scorecard KPI: the value, plan, % of plan and status.

1. New sheet, data source **scorecard**. Drag `Is reporting month` to **Filters** and keep **True**.
2. Drag `kpi_name` to **Columns**. Sort it by `kpi_id` (right-click > **Sort > Field > kpi_id, Minimum**).
3. Marks type **Text**. Drag onto **Text**: `kpi_name`, `Value shown`, `Plan shown`, `pct_of_plan`, `Status text`.
4. Click **Text** > **...** and lay the label out as:

   ```text
   <kpi_name>
   <Value shown>            (size 24, bold)
   Plan <Plan shown> · <pct_of_plan> of plan
   <Status text>            (bold)
   ```

5. Drag `status` to **Colour**, then set the colour's **Opacity** to about 20% so it tints the tile rather than filling it. The icon and word carry the meaning; the tint only helps.
6. Hide the column header (right-click > **Show Header** off). Tooltip: `<owner> · better when <direction> · amber band <amber_tolerance>`.

### Sheet E2: trend against plan

1. New sheet, data source **kpi_monthly**. Filter `kpi_id` to K02, K07, K13, K14, K15 and K19.
2. Drag `month_start` to **Columns** as a continuous **Month** (right-click > **Month** with the green calendar icon).
3. Drag `value` to **Rows**, then `Plan line` onto the same axis (drop it on the axis when the double-ruler icon appears, so it is **one** shared axis, not a dual axis).
4. Drag `kpi_name` to **Rows** in front of the measures, so each KPI gets its own row (small multiples). Right-click the value axis > **Edit Axis** > **Independent axis ranges for each row**.
5. Colour: `Measure Names`; `value` blue `#2a78d6`, `Plan line` grey `#898781`; make the plan line dashed (**Path** > dashed pattern).
6. Label the last point of `value` only (**Label** > **Line Ends**, end only).

### Sheet E3: callouts

Three short text boxes, one per headline finding in the [insights report](../reports/insights_report.md). Keep each to two lines: the finding in bold, then the number that proves it. For example:

- **The Raya FD promotion diluted CASA.** CASA fell from 91% to 63%; 78% of promotion money was existing savings.
- **v2 credit policy loans go bad faster.** 10.9% were 30+ days past due by month 6, against 3.2% under v1.
- **TikTok sign-ups do not stay.** RM17 per sign-up, but RM77 per customer still active in month 3.

### Dashboard: Executive

1. **Dashboard > New Dashboard**, Size **Fixed**, 1200 × 900.
2. Top: a text object with the title "Kelip Bank executive scorecard" and a subtitle naming the month; show the **Reporting month** parameter control at the top right.
3. Place E1 across the top, E2 below it on the left (about two thirds of the width), and E3 on the right.
4. Footer text: "Synthetic data: Kelip Bank is fictional. Status: ▲ on plan, ● watch (within the amber band), ▼ off plan. Source: kpi.scorecard."
5. Add a **Go to Sheet** action from each tile to its department page (**Dashboard > Actions > Add Action > Go to Sheet**, source E1, run on **Select**).

## 5. Growth page

**Question it answers:** where do customers come from, what do they cost, and where do applicants drop out? (Head of Growth and Head of Onboarding, Q04 to Q09.)

- **G1, cost per new customer against cost per retained customer (the headline chart).** Data source growth_channels, filter `is_paid` = True and `month_start` up to May 2026. `channel_name` on Rows, `Cost per new customer` and `Cost per retained customer` on Columns as a shared axis (Measure Values), marks **Circle**, with a line joining each pair (a dumbbell: add `Measure Names` to **Path** with marks type Line on a duplicate, or simply use two circles and label both). Sort channels by `Cost per retained customer`. Title: "TikTok is the cheapest channel per sign-up but the most expensive per customer who stays".
- **G2, new customers by channel.** Stacked bars of `new_customers` by month, coloured by `channel_name` in the categorical palette order: Organic, Google Search, Meta, TikTok, Refer a friend, Cashback affiliates. Add the K02 plan as a reference line (from kpi_monthly, or type the latest plan into the title).
- **G3, sign-up funnel.** Data source onboarding_funnel. `step_name` on Columns (sort by `step_no`), `Reached step` on Rows, marks **Line** with circles; `ekyc_flow` on Colour (control light grey `#b9b8b0`, guided blue `#2a78d6`); filter `is_in_ekyc_test` = True. Title: "The guided selfie flow lifts account opening, and the gain comes at the liveness check".
- **G4, onboarding conversion and eKYC completion.** kpi_monthly, K03 and K04 as two small line charts sharing the month axis, with their targets as reference lines (75% and 55%).
- **Filters:** a `channel_name` multi-select applied to G1 and G2 (**Apply to worksheets > Selected**).

## 6. Engagement page

**Question it answers:** how many customers use the bank, what they do, and who they are. (Head of Product and Head of Cards, Q10 to Q12 and Q16 to Q18.)

- **N1, monthly active customers against plan** (kpi_monthly K07; actual blue, plan grey dashed).
- **N2, active customer rate and transactions per active customer** (engagement_monthly; two small charts, one above the other, sharing the month axis, never a dual axis).
- **N3, card spend by category** (card_categories_monthly, last six months, horizontal bars sorted by spend, one colour). Title from the data, for example "Online marketplaces and groceries take over a third of card spend".
- **N4, card activation within 30 days** (cards_monthly `card_activation_30d`, with the 65% target as a reference line). The latest month is blank until every customer in it has had 30 days.
- **N5, customer segments** (customer_segments; three bar charts side by side, share of customers, share of deposits and share of card spend, segments in the same order on each). Put `action` and `owner` in the tooltip.
- **N6, declines** (cards_monthly: insufficient funds, wrong PIN, suspected fraud as a small table or bars).

## 7. Deposits page

**Question it answers:** how deposits and their cost are tracking, and what the Raya promotion did. (Treasurer, Q13 to Q15.)

- **D1, total deposits against plan** (kpi_monthly K13).
- **D2, CASA ratio against plan** (K14) **above D3, cost of funds against plan** (K15), sharing the month axis. Shade March to May 2025 with a reference band labelled "Raya FD promotion". Title: "The Raya FD promotion took the CASA ratio from 91% to 63% and pushed cost of funds to 2.60%".
- **D4, savings and fixed deposits** (deposits_monthly; stacked area or bars of `casa_balance`, `fd_balance` less `promo_fd_balance`, and `promo_fd_balance`, three categorical colours in order).
- **D5, money kept at maturity** (fd_maturity_outcomes, `Kept 30 days` by `is_promo_fd`, only rows where `window_complete` is True). Title: "Promotion money was far less likely to stay after maturity".

## 8. Credit page

**Question it answers:** is the loan book healthy, and did the policy change matter? (Head of Credit Risk, Q19 to Q21.)

- **C1, gross loans and financing disbursed** (credit_monthly; two small charts sharing the month axis).
- **C2, PAR30 against plan** (kpi_monthly K19) **above C3, GIL ratio** (credit_monthly `gil_ratio`, with the 2% target as a reference line).
- **C4, vintage curves by policy (the headline chart).** Data source vintage_curves. `months_on_book` on Columns (continuous, 1 to 12), `SUM([ever_30plus_loans]) / SUM([loans])` on Rows, `credit_policy` on Colour (v1 blue, v2 orange, v3 aqua) and on Detail. Filter `months_on_book` from 1 to 12. Label each line's end with the policy name. Title: "Loans approved under the loosened v2 policy were 3.4 times as likely to be 30+ days past due by month 6".
- **C5, roll rates** (roll_rates, last six months; a highlight table with `from_bucket` on Rows, `to_bucket` on Columns and `Roll rate` as the text, coloured with the **Kelip blues** sequential palette).

## 9. Check the numbers, then publish

Before publishing, set the Reporting month to August 2026 and check the dashboard against the warehouse. The Excel pack ([`reports/kelip_bank_kpi_pack.xlsx`](../reports/kelip_bank_kpi_pack.xlsx)) shows the same figures.

| KPI (August 2026) | Should read |
|---|---|
| New customers | 1,972, ▲ On plan (plan 1,950) |
| Monthly active customers | 18,522, ▲ On plan (plan 18,000) |
| Total deposits | RM132.2m, ▲ On plan (plan RM115.0m) |
| CASA ratio | 78.2%, ● Watch (plan 80.0%) |
| Cost of funds | 1.94%, ▲ On plan (plan 2.00%) |
| PAR30 | 2.99%, ▲ On plan (plan 3.00%) |

Then:

1. On each dashboard, add the footer "Synthetic data: Kelip Bank is fictional."
2. Save a local copy as you go (**File > Save**, a `.twbx` file), then publish with **File > Save to Tableau Public As...** and name it **Kelip Bank BI (synthetic data)**. Keep it hidden from your profile until you are ready, if you like.
3. In the browser, open the viz, click **Edit Details**, and add a description: what the dashboard is, that the data is synthetic, and the GitHub link `https://github.com/clarence1909/DigitalBankingBI_project`.
4. Tick **Show workbook sheets as tabs**, so viewers can move between the five pages.
5. Copy the viz link. Paste it into the README where it says `<!-- tableau-link -->`, and take a screenshot of the Executive page for `reports/charts/tableau_executive.png` if you want the README to show the Tableau version.

## 10. Refresh after the data changes

Tableau Public keeps its own copy of the data. After rerunning the pipeline:

1. Open your local `.twbx` (or download it from your Tableau Public profile).
2. **Data > Refresh All Extracts**, or edit each connection to point at the new CSVs.
3. Check the table in section 9 again, then **File > Save to Tableau Public**.

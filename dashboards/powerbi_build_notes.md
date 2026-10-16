# Power BI build notes

The Kelip Bank dashboard is a Power BI report that the pipeline writes itself, as a Power BI project in [`powerbi/`](powerbi/). It has five pages (Executive, Growth, Engagement, Deposits and Credit) with 34 charts and tables, and it reads one file, [`extracts/dashboard_data.csv`](extracts/dashboard_data.csv). These notes explain how to open it, check it and share it, which takes about 15 minutes, then how it is built and how to change it.

> **All data is synthetic.** Kelip Bank is a fictional Malaysian digital bank. Every page carries the line "Synthetic data: Kelip Bank is fictional" in its footer.

The Executive page shows the same figures as the pipeline's own picture of it, [`reports/charts/00_executive_scorecard.png`](../reports/charts/00_executive_scorecard.png).

## Contents

1. [Open and check](#1-open-and-check)
2. [Save and share](#2-save-and-share)
3. [What is in the report](#3-what-is-in-the-report)
4. [How the report is built and checked](#4-how-the-report-is-built-and-checked)
5. [Change or extend it](#5-change-or-extend-it)
6. [Refresh after the data changes](#6-refresh-after-the-data-changes)
7. [House rules for every page](#7-house-rules-for-every-page)

## 1. Open and check

You need **Power BI Desktop**, which is free and runs on Windows. The report is made for the current release, so keep it up to date. You do not need a Power BI account to open, check or save the report.

1. **Install Power BI Desktop.** Open the Microsoft Store, search for **Power BI Desktop** and click **Get**. The Store version keeps itself up to date. (It is also at [powerbi.microsoft.com/desktop](https://powerbi.microsoft.com/desktop).) If it asks you to sign in when it starts, close that window.
2. **Get the files.** Clone the repository, or download it from GitHub as a ZIP file and unzip it. Keep the `dashboards` folder as it is: the report is `dashboards/powerbi/KelipBank.pbip`, and it reads `dashboards/extracts/dashboard_data.csv`.
3. **Open the report.** Double-click `KelipBank.pbip`, or start Power BI Desktop, use **File > Open** and browse to it. It opens on the Executive page, with the other pages as tabs along the bottom. The charts are empty for now: a Power BI project keeps the report and its model but not the data, which you load in step 5.
4. **Point it at your copy of the data.** The model reads the CSV from the folder in its **DataFolder** parameter, which is `C:\Users\clare\DigitalBankingBI_project\dashboards\extracts`, where the author keeps the repository. If your copy is anywhere else:
   1. On the **Home** tab, click the arrow under **Transform data**, then **Edit parameters**.
   2. Set **DataFolder** to your own `dashboards\extracts` folder, for example `D:\Projects\DigitalBankingBI_project\dashboards\extracts`.
   3. Click **OK**, then **Apply changes** in the yellow bar that appears.
5. **Load the data.** On the **Home** tab, click **Refresh**. It takes a few seconds, and the charts fill in.
6. **Check the numbers.** The scorecard on the Executive page should read:

   | KPI (August 2026) | Should read |
   |---|---|
   | New customers | 1,972, plan 1,950, 101.1% of plan, ▲ On plan |
   | Monthly active customers | 18,522, plan 18,000, 102.9% of plan, ▲ On plan |
   | Total deposits | RM132.2m, plan RM115.0m, 114.9% of plan, ▲ On plan |
   | CASA ratio | 78.2%, plan 80.0%, 97.7% of plan, ● Watch |
   | Cost of funds | 1.94%, plan 2.00%, 96.8% of plan, ▲ On plan |
   | PAR30 | 2.99%, plan 3.00%, 99.5% of plan, ▲ On plan |

   The other charts quote their own numbers in their titles, and they match the [insights report](../reports/insights_report.md): for example, TikTok costs RM17 per new customer but RM77 per customer still active in month 3 (Growth), and 10.9% of loans under the v2 policy were 30+ days past due by month 6, against 3.2% under v1 (Credit).

**If something goes wrong:**

- *"DataSource.Error: Could not find a part of the path"* when you refresh: the DataFolder parameter does not point at your copy of the data. Do step 4.
- *Power BI Desktop cannot open the file:* update it to the current release (the Microsoft Store version updates itself). If it still cannot, turn on the preview features for Power BI project (.pbip) files, the enhanced report format (PBIR) and the semantic model text format (TMDL) under **File > Options and settings > Options > Preview features**, then restart Power BI Desktop.
- *A chart shows an error:* note the message. [`reports/powerbi_report_check.md`](../reports/powerbi_report_check.md) lists everything the build checked about the report.

## 2. Save and share

The project folder is for editing and version control. Do not save your changes into it: the pipeline rewrites it on every run. To keep or share the report, save a copy.

1. **Save it as one file.** Use **File > Save as**, choose a folder outside the repository (for example **Documents**), set **Save as type** to **Power BI file (\*.pbix)**, name it `Kelip Bank dashboard` and click **Save**. The `.pbix` file holds the report and its data, so it opens anywhere with Power BI Desktop.
2. **Export a PDF of every page.** Use **File > Export > Export to PDF**. The PDF opens in any browser, so it is the easiest way to show the report to someone without Power BI, for example with a job application.
3. **Take pictures of the pages** for the README or a portfolio: open each page and press **Windows key + Shift + S** to snip it.
4. **Publish it online (optional).** Publishing needs a Power BI account, and Power BI accounts need a work or school email address: personal addresses such as Gmail or Outlook.com cannot sign up. With one, click **Publish** on the **Home** tab, sign in and choose **My workspace**. In the Power BI service you can then share the report with people in your organisation, which needs a Power BI Pro or Premium Per User licence.
5. **Make a public link (optional).** Only if your organisation's Power BI admin allows it: in the Power BI service, open the report and use **File > Embed report > Publish to web (public)**. Anyone with the link can see the report, which is fine here because the data is synthetic. Then, in `README.md`, replace the comment that starts `<!-- powerbi-link` with `[Open the interactive report](your link)`.

## 3. What is in the report

Each chart's title states its takeaway, with the numbers taken from the data when the report is written, and each chart with two or more series has a legend at its top.

| Page | Charts | Questions |
|---|---|---|
| **Executive** | A scorecard of the six plan KPIs (value, plan, % of plan, and status as a tint, an icon and a word); net interest income against its target; what needs attention, with owners; new customers, monthly active customers, total deposits, the CASA ratio, cost of funds and PAR30 against plan | Q01 to Q03 |
| **Growth** | Cost per new customer and per customer still active in month 3, by paid channel; the eKYC test's sign-up funnel, control against guided; onboarding conversion, eKYC completion and activity in month 3; new customers by channel; applications started against target; new customers against plan | Q04 to Q08 |
| **Engagement** | Monthly active customers against plan; active customer rate and card activation within 30 days; transactions per active customer; debit card spend; card spend by category; card declines by reason, with the approval rate; the six customer segments' shares of customers, deposits and card spend, with each segment's action and owner in the tooltip | Q10 to Q12, Q16 to Q18 |
| **Deposits** | Total deposits against plan; savings, standard fixed deposits and Raya promotion deposits; net interest income; the CASA ratio and cost of funds against plan; money kept 30 days after maturity, promotion against standard deposits | Q03, Q13 to Q15 |
| **Credit** | Gross loans; financing disbursed; PAR30 against plan; the GIL ratio; vintage curves by credit policy; early delinquency at month 6; roll rates between arrears buckets | Q19 to Q21 |

The questions are the stakeholder questions in the [business requirements](../docs/01_business_requirements.md). Hovering over a line, bar or cell shows its exact value (and month, on charts over time), and the **?** icon at the top right of each KPI's chart gives the KPI's definition from the [KPI dictionary](../docs/05_kpi_dictionary.md). Each chart stands alone: clicking a point does not filter the others.

**The model** has 12 tables, one per kind of chart (Scorecard, KPI trend, Channel cost, Sign-up funnel, Roll rates and so on), and 32 measures. The KPI trend table has a measure for each of the 19 KPIs the report charts over time, named after the KPI and described with its definition, so the fields list reads like the KPI dictionary. The tables are not related to each other: each chart's numbers are already summarised in SQL, so the model needs no joins, and the star schema lives in the warehouse. Columns in different tables have different names (Month and Channel apart, which never hold unique values), so Power BI finds nothing to link automatically when the data loads.

## 4. How the report is built and checked

- **One tall table.** [`src/export/dashboard_data.py`](../src/export/dashboard_data.py) writes every number the report shows into `dashboard_data.csv`, one row per point, with a `chart` column naming the chart it belongs to (`tiles`, `trend_K13`, `funnel_ab`, ...). All the business logic stays in SQL and Python, where the checks can see it; the model only adds numbers up.
- **The model, in TMDL.** One Power Query, *Dashboard data*, reads the CSV and sets each column's type; it is not loaded itself. Each table keeps its own chart's rows of it and gives the columns readable names, and helper columns set the order of channels, reasons and arrears buckets. The measures are plain DAX: each KPI's measure is `CALCULATE(SUM(...), 'KPI trend'[KPI ID] = "K..")`. Automatic date tables are off, and so are implicit measures, so every number on a chart comes from a named measure with its own format.
- **The report, in PBIR.** Five pages of 1280 x 720 pixels. Titles are built from the data, so a rebuild with new data gives new titles. Each series keeps one colour on every chart (actual is blue, plan and target grey, and each channel, reason, deposit type and policy has its own colour), set on each visual. The scorecard tints each status cell from a measure, and the roll-rate matrix shades each cell from light to darker blue by its share.
- **Written from code.** [`src/export/powerbi_report.py`](../src/export/powerbi_report.py) writes the whole project. Page and visual names are derived from fixed text rather than made up at random, so the files are identical on every run and every machine, and a change shows up in Git as a readable difference.
- **Checked on every build.** [`src/export/powerbi_check.py`](../src/export/powerbi_check.py) reads the files the way Power BI would. It replays each table's Power Query on the CSV with pandas, then checks that every table keeps rows, every column it loads exists with the right type, every sort order gives each value one position, and every measure refers only to fields and values that exist; that every field a chart plots, sorts or colours by is in the model; that every series colour names a value in the data; and that every chart sits inside its page without overlapping another. Any problem stops the build. The results are in [`reports/powerbi_report_check.md`](../reports/powerbi_report_check.md), and the [break-tests](../reports/break_test_report.md) prove the check catches a broken report.
- **Validated against Microsoft's schemas in CI.** On every push, GitHub Actions also runs Microsoft's own report checker, the [Power BI report authoring CLI](https://www.npmjs.com/package/@microsoft/powerbi-report-authoring-cli), which validates the report's files against Microsoft's published report schemas and checks each visual's roles and formatting. (It does not read the TMDL model, which the pipeline's own check covers.) The CLI's version and its dependencies are pinned in [`.github/powerbi-cli/`](../.github/powerbi-cli/).
- **Base theme.** Power BI keeps a copy of its base theme in every report. The one used here, `CY26SU10`, is in [`third_party/powerbi-base-theme/`](../third_party/powerbi-base-theme/), from Microsoft's MIT-licensed CLI.
- **What the checks cannot prove.** No check draws the charts, so opening the report in Power BI Desktop (section 1) is the final check.

## 5. Change or extend it

- **Small changes before sharing,** such as moving a chart: make them in Power BI Desktop, then save your own copy as a `.pbix` file (section 2).
- **Lasting changes** go in [`src/export/powerbi_report.py`](../src/export/powerbi_report.py); then `python run_pipeline.py --only publish` rewrites and rechecks the report. Every KPI already has a trend in the data (`trend_K01` to `trend_K22`), so a new KPI chart is one line in `KPI_MEASURES` and one call to `trend()` on a page.
- **Another data folder.** Change the DataFolder parameter in Power BI Desktop (section 1, step 4), or set the environment variable `KELIP_POWERBI_DATA_DIR` to your `dashboards\extracts` folder before running the pipeline, so the rebuilt report points there: for example `set KELIP_POWERBI_DATA_DIR=D:\Projects\DigitalBankingBI_project\dashboards\extracts` in the Windows command prompt.
- **Run Microsoft's validation yourself.** Install [Node.js](https://nodejs.org/) 20 or later, then, from the repository folder, run:

  ```bash
  npm ci --prefix .github/powerbi-cli
  .github/powerbi-cli/node_modules/.bin/powerbi-report-author validate dashboards/powerbi/KelipBank.pbip --format text
  ```

  It should end with `0 error(s), 0 warning(s); result=succeeded`.

## 6. Refresh after the data changes

1. Close Power BI Desktop if the report is open, without saving.
2. Run `python run_pipeline.py`. It rewrites `dashboard_data.csv` and the report, whose titles quote the new numbers.
3. Open `KelipBank.pbip` again and click **Refresh**. If your copy of the repository is not where the author keeps it, set the DataFolder parameter again first (section 1, step 4): the rebuild resets it, unless you set `KELIP_POWERBI_DATA_DIR` (section 5).
4. Check the scorecard against the Excel pack ([`reports/kelip_bank_kpi_pack.xlsx`](../reports/kelip_bank_kpi_pack.xlsx)), which shows the same figures.
5. Save a new `.pbix` copy or PDF, and publish again if the report is online: publishing under the same name replaces the old version.

## 7. House rules for every page

These rules keep the report readable and accessible. The generator follows them; keep to them when you change it.

- **Title each chart with its takeaway**, not its contents: "The CASA ratio is back within 2 points of plan", not "CASA ratio by month".
- **Status is never colour alone.** Every red, amber or green tint has the icon (▲ on plan, ● watch, ▼ off plan) and the word next to it.
- **One axis per chart.** Never a dual axis with two different measures. Two measures of different scale get two charts.
- **Colours follow the thing, not its rank.** TikTok is the same colour on every page, and actual is always blue against a grey plan or target.
- **Thin marks, light gridlines.** Lines 2 px, pale grey gridlines, no borders around charts.
- **A legend whenever there are two or more series**, and the latest value in the title of every KPI trend.
- **Text is dark grey or black**, never the colour of a series.

"""Write the Power BI report, dashboards/powerbi/, from code.

The report is generated rather than built by hand, so it is rebuilt with
everything else and its titles always quote the current numbers. It is a
Power BI project (PBIP), the folder format Power BI Desktop saves for version
control:

  KelipBank.pbip            the file to open in Power BI Desktop
  KelipBank.SemanticModel/  the data model, in TMDL: one Power Query read of
                            dashboards/extracts/dashboard_data.csv, split into
                            one table per chart, and the measures the charts use
  KelipBank.Report/         the report, in PBIR: five pages (Executive, Growth,
                            Engagement, Deposits and Credit) of charts and text

The pages are 1280 x 720 pixels. The JSON follows Microsoft's published
report schemas (report 3.3.0, page 2.1.0, visual container 2.9.0, the newest
of which came with Power BI Desktop's May 2026 release) and uses the base
theme Microsoft's report CLI gives new reports, so it is made for the current
Power BI Desktop. src/export/powerbi_check.py checks the output on every build.

The model reads dashboard_data.csv from the folder in its DataFolder
parameter: DEFAULT_DATA_DIR, the repo's dashboards/extracts folder on the
author's laptop. On another machine, change the parameter in Power BI Desktop
(Transform data > Edit parameters), or set the KELIP_POWERBI_DATA_DIR
environment variable to your own dashboards/extracts folder before running the
pipeline.
"""

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field

import pandas as pd

from src.config import DASHBOARD_DIR, ROOT
from src.export.dashboard_data import BUCKETS, DATA, LAST_OBSERVED_COHORT, RECENT_FROM, SHORT_CHANNEL

NAME = "KelipBank"
PROJECT_DIR = DASHBOARD_DIR / "powerbi"
MODEL = f"{NAME}.SemanticModel"
REPORT = f"{NAME}.Report"
BASE_THEME = ROOT / "third_party" / "powerbi-base-theme" / "CY26SU10.json"
BASE_THEME_NAME = "CY26SU10"
DEFAULT_DATA_DIR = r"C:\Users\clare\DigitalBankingBI_project\dashboards\extracts"
DATA_DIR_ENV = "KELIP_POWERBI_DATA_DIR"
WIDTH, HEIGHT = 1280, 720

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"
SCHEMAS = {
    "pbip": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json",
    "platform": SCHEMA + "gitIntegration/platformProperties/2.0.0/schema.json",
    "pbir": SCHEMA + "item/report/definitionProperties/2.0.0/schema.json",
    "pbism": SCHEMA + "item/semanticModel/definitionProperties/1.0.0/schema.json",
    "version": SCHEMA + "item/report/definition/versionMetadata/1.0.0/schema.json",
    "report": SCHEMA + "item/report/definition/report/3.3.0/schema.json",
    "pages": SCHEMA + "item/report/definition/pagesMetadata/1.1.0/schema.json",
    "page": SCHEMA + "item/report/definition/page/2.1.0/schema.json",
    "visual": SCHEMA + "item/report/definition/visualContainer/2.9.0/schema.json",
}

FOOTER = ("Synthetic data: Kelip Bank is fictional. Every figure comes from dashboards/extracts/"
          "dashboard_data.csv, rebuilt from the warehouse by run_pipeline.py.")

# The project's colours: the same palette as the report charts and the Excel pack
INK, INK_SECONDARY, WHITE = "#0b0b0b", "#52514e", "#ffffff"
CANVAS, GRIDLINE = "#f3f2ee", "#e6e5e0"
BLUE, ORANGE, AQUA, GOLD, PINK, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
PLAN_GREY, CONTEXT_GREY = "#898781", "#b9b8b0"
BLUES = ["#cde2fb", "#86b6ef", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]
STATUS_FILL = {"On plan": "#ddf2dd", "Watch": "#fef0cc", "Off plan": "#f8dede"}
CHANNEL_ORDER = list(SHORT_CHANNEL.values())  # Organic, Google Search, Meta, TikTok, ...
DEPOSIT_ORDER = ["Savings (CASA)", "Standard fixed deposits", "Raya promotion deposits"]
DECLINE_ORDER = ["Insufficient funds", "Wrong PIN", "Suspected fraud"]
SEGMENT_SERIES = ["Customers", "Deposits", "Card spend"]
POLICIES = ["v1 launch policy", "v2 growth policy", "v3 tightened policy"]
COST_BASES = ["Per new customer", "Per customer active in month 3"]

# Number formats (Power BI format strings)
COUNT, NUMBER, PCT0, PCT1, PCT2 = "#,##0", "#,##0.0", "0%", "0.0%", "0.00%"
RM, RM_MILLIONS = r"\R\M#,##0", r"\R\M#,##0.0\m"


# --------------------------------------------------------------------------------------------
# Identifiers. Power BI names pages and visuals with random ids; these are derived from fixed
# text instead, so every build writes the same files.
# --------------------------------------------------------------------------------------------

def hex_id(seed: str, length: int = 20) -> str:
    return hashlib.sha256(f"kelip-bank:{seed}".encode()).hexdigest()[:length]


def logical_id(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"kelip-bank:{seed}"))


# --------------------------------------------------------------------------------------------
# The semantic model: one table per chart, each a Power Query step over dashboard_data.csv
# --------------------------------------------------------------------------------------------

# The type Power Query gives each column of dashboard_data.csv, and the model type it becomes
CSV_TYPES = {
    "chart": "type text", "month": "type date", "category": "type text", "series": "type text",
    "x": "Int64.Type", "count": "type number", "rate": "type number", "rm_millions": "type number",
    "rm": "type number", "number": "type number", "label": "type text", "detail": "type text",
    "status": "type text", "status_text": "type text", "sort": "Int64.Type",
}
MODEL_TYPE = {"type text": "string", "type date": "dateTime", "Int64.Type": "int64", "type number": "double"}


@dataclass
class Column:
    name: str
    source: str               # its column in dashboard_data.csv, or a column Power Query adds
    hidden: bool = False
    fmt: str | None = None
    sort_by: str | None = None
    dtype: str | None = None  # model type; worked out from the source column when not given


@dataclass
class Measure:
    name: str
    dax: str
    fmt: str | None
    description: str


@dataclass
class Table:
    name: str
    description: str
    rows: str                                    # Power Query row filter, e.g. [chart] = "tiles"
    columns: list
    measures: list = field(default_factory=list)
    added: list = field(default_factory=list)    # (name, M expression, M type), added before columns are kept
    orders: list = field(default_factory=list)   # (order column, column it orders, values in order)

    def column(self, name: str) -> Column:
        return next(c for c in self.columns if c.name == name)


def order_column(name: str) -> Column:
    return Column(name, name, hidden=True, dtype="int64")


def value_column(name: str, source: str) -> Column:
    return Column(name, source, hidden=True)


# KPI trend measures: KPI -> (measure name, value column, format, actual values only)
# The single-KPI charts split Actual from Plan or Target with the Series column; the charts that
# compare two KPIs show only each one's actual values.
KPI_MEASURES = {
    "K01": ("Applications started", "Count", COUNT, False),
    "K02": ("New customers", "Count", COUNT, False),
    "K03": ("Onboarding conversion", "Rate", PCT1, True),
    "K04": ("eKYC completion rate", "Rate", PCT1, True),
    "K06": ("Month-3 active rate", "Rate", PCT1, True),
    "K07": ("Monthly active customers", "Count", COUNT, False),
    "K08": ("Active customer rate", "Rate", PCT1, True),
    "K09": ("Transactions per active customer", "Number", NUMBER, False),
    "K10": ("Card activation within 30 days", "Rate", PCT1, True),
    "K11": ("Debit card spend", "RM millions", RM_MILLIONS, False),
    "K13": ("Total deposits", "RM millions", RM_MILLIONS, False),
    "K14": ("CASA ratio", "Rate", PCT1, False),
    "K15": ("Cost of funds", "Rate", PCT2, False),
    "K17": ("Gross loans", "RM millions", RM_MILLIONS, False),
    "K18": ("Financing disbursed", "RM millions", RM_MILLIONS, False),
    "K19": ("PAR30", "Rate", PCT2, False),
    "K20": ("GIL ratio", "Rate", PCT2, False),
    "K21": ("Early delinquency at month 6", "Rate", PCT1, False),
    "K22": ("Net interest income", "RM", RM, False),
}


def kpi_measure(kpi: str, definition: str) -> Measure:
    name, column, fmt, actual_only = KPI_MEASURES[kpi]
    filters = f"'KPI trend'[KPI ID] = \"{kpi}\""
    if actual_only:
        filters += ", 'KPI trend'[Series] = \"Actual\""
    note = " Actual values only." if actual_only else " Split it by Series to compare it with plan or target."
    return Measure(name, f"CALCULATE(SUM('KPI trend'[{column}]), {filters})", fmt,
                   f"{kpi}: {definition.rstrip('.')}.{note}")


def tables(definitions: dict) -> list:
    """The model's tables. `definitions` maps each KPI to its definition, from the KPI catalog.

    Columns in different tables have different names (Month and Channel apart, which hold no unique values
    in any table), so Power BI's automatic relationship detection finds nothing to link: each chart reads
    its own table, and the tables are meant to stay unrelated.
    """
    buckets = list(BUCKETS.values())
    status_colour = ", ".join(f'"{status}", "{colour}"' for status, colour in STATUS_FILL.items())
    return [
        Table("Scorecard", "The six plan KPIs in the latest month: actual, plan and status.", '[chart] = "tiles"', [
            Column("KPI", "category", sort_by="KPI order"),
            Column("Actual", "label"),
            Column("Plan", "detail"),
            Column("% of plan", "rate", fmt=PCT1),
            Column("Status", "status"),
            Column("Status label", "status_text"),
            Column("KPI order", "sort", hidden=True),
        ], [
            Measure("Status colour", f"SWITCH(SELECTEDVALUE(Scorecard[Status]), {status_colour})", None,
                    "Background colour for a KPI's status: green on plan, amber on watch, red off plan."),
        ]),
        Table("KPI trend", "Each KPI by month, with its plan or target. The measures pick one KPI each.",
              'Text.StartsWith([chart], "trend_")', [
                  Column("KPI ID", "KPI ID"),
                  Column("KPI name", "category"),
                  Column("Month", "month", fmt="mmm yyyy"),
                  Column("Series", "series"),
                  Column("Definition", "detail"),
                  value_column("Count", "count"),
                  value_column("Rate", "rate"),
                  value_column("RM millions", "rm_millions"),
                  value_column("RM", "rm"),
                  value_column("Number", "number"),
              ], [kpi_measure(k, definitions[k]) for k in KPI_MEASURES],
              added=[("KPI ID", 'Text.AfterDelimiter([chart], "_")', "type text")]),
        Table("Channel cost", "Marketing spend per new customer and per customer still active in month 3, "
              "by paid channel, for customers who joined up to the last month with a third month of data.",
              '[chart] = "channel_cost"', [
                  Column("Channel", "category", sort_by="Channel rank"),
                  Column("Cost basis", "series", sort_by="Cost basis order"),
                  value_column("Cost in RM", "rm"),
                  Column("Channel rank", "sort", hidden=True),
                  order_column("Cost basis order"),
              ], [
                  Measure("Cost per customer", "SUM('Channel cost'[Cost in RM])", RM,
                          "Marketing spend divided by the customers the channel brought in."),
              ], orders=[("Cost basis order", "Cost basis", COST_BASES)]),
        Table("New customers by channel", "New customers each month, by the channel they came from.",
              '[chart] = "new_by_channel"', [
                  Column("Month", "month", fmt="mmm yyyy"),
                  Column("Channel", "series", sort_by="Channel order"),
                  value_column("Customers", "count"),
                  order_column("Channel order"),
              ], [
                  Measure("Channel new customers", "SUM('New customers by channel'[Customers])", COUNT,
                          "New customers from the channel."),
              ], orders=[("Channel order", "Channel", CHANNEL_ORDER)]),
        Table("Sign-up funnel", "The eKYC test: share of applicants in each flow who reached each sign-up step.",
              '[chart] = "funnel_ab"', [
                  Column("Step", "category", sort_by="Step order"),
                  Column("Flow", "series"),
                  value_column("Share reached", "rate"),
                  Column("Step order", "sort", hidden=True),
              ], [
                  Measure("Share of applicants", "SUM('Sign-up funnel'[Share reached])", PCT1,
                          "Share of the flow's applicants who reached the step."),
              ]),
        Table("Card spend by category", "Debit card spend by merchant category over the last six months.",
              '[chart] = "card_categories"', [
                  Column("Merchant category", "category", sort_by="Category order"),
                  value_column("Spend in RM millions", "rm_millions"),
                  Column("Category order", "sort", hidden=True),
              ], [
                  Measure("Category card spend", "SUM('Card spend by category'[Spend in RM millions])", RM_MILLIONS,
                          "Debit card spend in the category, in RM millions."),
              ]),
        Table("Card declines", "Declined card payments each month, by reason.", '[chart] = "declines"', [
            Column("Month", "month", fmt="mmm yyyy"),
            Column("Reason", "series", sort_by="Reason order"),
            value_column("Declines", "count"),
            order_column("Reason order"),
        ], [
            Measure("Declined payments", "SUM('Card declines'[Declines])", COUNT,
                    "Card payments declined for the reason."),
        ], orders=[("Reason order", "Reason", DECLINE_ORDER)]),
        Table("Customer segments", "Each customer segment's share of customers, deposits and card spend, "
              "with the action proposed for it and its owner.", '[chart] = "segments"', [
                  Column("Segment", "category", sort_by="Segment order"),
                  Column("Share of", "series", sort_by="Share of order"),
                  value_column("Share of total", "rate"),
                  Column("Action", "label", hidden=True),
                  Column("Owner", "detail", hidden=True),
                  Column("Segment order", "sort", hidden=True),
                  order_column("Share of order"),
              ], [
                  Measure("Segment share", "SUM('Customer segments'[Share of total])", PCT0,
                          "The segment's share of all customers, deposits or card spend."),
                  Measure("Segment action", "SELECTEDVALUE('Customer segments'[Action])", None,
                          "What the insights report proposes for the segment."),
                  Measure("Segment owner", "SELECTEDVALUE('Customer segments'[Owner])", None,
                          "Who owns the segment's action."),
              ], orders=[("Share of order", "Share of", SEGMENT_SERIES)]),
        Table("Deposit mix", "Deposit balances at each month end, by type.", '[chart] = "deposit_mix"', [
            Column("Month", "month", fmt="mmm yyyy"),
            Column("Deposit type", "series", sort_by="Type order"),
            value_column("Balance in RM millions", "rm_millions"),
            order_column("Type order"),
        ], [
            Measure("Deposit balance", "SUM('Deposit mix'[Balance in RM millions])", RM_MILLIONS,
                    "Balances at month end, in RM millions."),
        ], orders=[("Type order", "Deposit type", DEPOSIT_ORDER)]),
        Table("FD retention", "Share of matured fixed deposit money still at Kelip Bank 30 days after maturity.",
              '[chart] = "fd_retention"', [
                  Column("FD type", "category"),
                  value_column("Share kept", "rate"),
              ], [
                  Measure("Money kept at maturity", "SUM('FD retention'[Share kept])", PCT0,
                          "Share of matured money rolled over or kept at Kelip Bank 30 days after maturity."),
              ]),
        Table("Vintage", "Share of loans ever 30+ days past due, by months on book and the credit policy "
              "they were approved under.", '[chart] = "vintage"', [
                  Column("Policy", "series"),
                  Column("Months on book", "x"),
                  value_column("Share past due", "rate"),
              ], [
                  Measure("Share 30+ days past due", "SUM(Vintage[Share past due])", PCT1,
                          "Share of the policy's loans ever 30+ days past due by this month on book."),
              ]),
        Table("Roll rates", "Share of loans in each arrears bucket that moved to each bucket a month later, "
              "over the last six months.", '[chart] = "roll_rates"', [
                  Column("From", "category", sort_by="From order"),
                  Column("To", "series", sort_by="To order"),
                  value_column("Share moved", "rate"),
                  order_column("From order"),
                  order_column("To order"),
              ], [
                  Measure("Share of loans", "SUM('Roll rates'[Share moved])", PCT0,
                          "Share of the From bucket's loans that were in the To bucket a month later."),
              ], orders=[("From order", "From", buckets), ("To order", "To", buckets)]),
    ]


def quote(name: str) -> str:
    """A TMDL or DAX object name, in single quotes unless it is a plain word."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def m_name(step: str) -> str:
    return step if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", step) else f'#"{step}"'


def m_text(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def m_list(values) -> str:
    return "{" + ", ".join(m_text(v) for v in values) + "}"


def base_query() -> str:
    """Power Query for the shared read of dashboard_data.csv: headers, blanks as nulls, and types."""
    typed = ", ".join(f"{{{m_text(c)}, {t}}}" for c, t in CSV_TYPES.items())
    blanks = [c for c in CSV_TYPES if c != "chart"]
    return "\n".join([
        "let",
        f'    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, {{"\\", "/"}}) & "\\dashboard_data.csv"), '
        f'[Delimiter = ",", Columns = {len(CSV_TYPES)}, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        '    #"Promoted headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),',
        f'    #"Blanks as nulls" = Table.ReplaceValue(#"Promoted headers", "", null, Replacer.ReplaceValue, '
        f"{m_list(blanks)}),",
        f'    #"Changed types" = Table.TransformColumnTypes(#"Blanks as nulls", {{{typed}}}, "en-US")',
        "in",
        '    #"Changed types"',
    ])


def table_query(t: Table) -> str:
    """Power Query for one table: its chart's rows of the shared read, renamed for the report."""
    steps = [("Source", '#"Dashboard data"')]

    def last():
        return m_name(steps[-1][0])

    steps.append((f"Kept {t.name} rows", f"Table.SelectRows({last()}, each {t.rows})"))
    for name, expr, mtype in t.added:
        steps.append((f"Added {name}", f"Table.AddColumn({last()}, {m_text(name)}, each {expr}, {mtype})"))
    added_orders = {order for order, _, _ in t.orders}
    kept = [c for c in t.columns if c.name not in added_orders]
    steps.append(("Kept columns", f"Table.SelectColumns({last()}, {m_list(c.source for c in kept)})"))
    renames = [(c.source, c.name) for c in kept if c.source != c.name]
    if renames:
        pairs = ", ".join(f"{{{m_text(a)}, {m_text(b)}}}" for a, b in renames)
        steps.append(("Renamed columns", f"Table.RenameColumns({last()}, {{{pairs}}})"))
    for order, of, values in t.orders:
        steps.append((f"Added {order}", f"Table.AddColumn({last()}, {m_text(order)}, "
                                        f"each List.PositionOf({m_list(values)}, [{of}]) + 1, Int64.Type)"))
    body = ",\n".join(f"    {m_name(name)} = {expr}" for name, expr in steps)
    return f"let\n{body}\nin\n    {last()}"


def column_type(t: Table, c: Column) -> str:
    if c.dtype:
        return c.dtype
    added = {name: mtype for name, _, mtype in t.added}
    return MODEL_TYPE[added.get(c.source) or CSV_TYPES[c.source]]


def table_tmdl(t: Table) -> str:
    lines = [f"/// {t.description}", f"table {quote(t.name)}", ""]
    for m in t.measures:
        lines += [f"\t/// {m.description}", f"\tmeasure {quote(m.name)} = {m.dax}"]
        if m.fmt:
            lines.append(f"\t\tformatString: {m.fmt}")
        lines.append("")
    for c in t.columns:
        lines += [f"\tcolumn {quote(c.name)}", f"\t\tdataType: {column_type(t, c)}"]
        if c.hidden:
            lines.append("\t\tisHidden")
        if c.fmt:
            lines.append(f"\t\tformatString: {c.fmt}")
        lines += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: {c.name}"]
        if c.sort_by:
            lines.append(f"\t\tsortByColumn: {quote(c.sort_by)}")
        lines.append("")
    lines += [f"\tpartition {quote(t.name)} = m", "\t\tmode: import", "\t\tsource ="]
    lines += ["\t\t\t\t" + line for line in table_query(t).split("\n")]
    return "\n".join(lines) + "\n"


def model_files(model_tables: list, data_dir: str) -> dict:
    folder = data_dir.rstrip("\\/")
    expressions = "\n".join([
        "/// The folder that holds dashboard_data.csv: the repo's dashboards\\extracts folder. Change it in "
        "Home > Transform data > Edit parameters.",
        f'expression DataFolder = {m_text(folder)} meta [IsParameterQuery = true, Type = "Text", '
        "IsParameterQueryRequired = true]",
        "",
        "/// Every chart's rows, read once from dashboard_data.csv. Each table keeps its own chart's rows.",
        "expression 'Dashboard data' =",
        *["\t\t" + line for line in base_query().split("\n")],
        "",
    ])
    model = "\n".join([
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-US",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        *[f"ref table {quote(t.name)}" for t in model_tables],
        "",
    ])
    files = {
        f"{MODEL}/.platform": platform("SemanticModel"),
        f"{MODEL}/definition.pbism": as_json({"$schema": SCHEMAS["pbism"], "version": "4.2", "settings": {}}),
        f"{MODEL}/definition/database.tmdl": "database\n\tcompatibilityLevel: 1600\n",
        f"{MODEL}/definition/model.tmdl": model,
        f"{MODEL}/definition/expressions.tmdl": expressions,
    }
    for t in model_tables:
        files[f"{MODEL}/definition/tables/{t.name}.tmdl"] = table_tmdl(t)
    return files


# --------------------------------------------------------------------------------------------
# PBIR building blocks: literal values, fields, and the formatting every chart shares
# --------------------------------------------------------------------------------------------

def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def B(value: bool) -> dict:
    return lit("true" if value else "false")


def N(value) -> dict:
    return lit(f"{value}D")


def S(text: str) -> dict:
    return lit("'" + text.replace("'", "''") + "'")


def C(colour: str) -> dict:
    return {"solid": {"color": S(colour)}}


@dataclass(frozen=True)
class Field:
    table: str
    name: str
    kind: str = "Column"   # Column or Measure

    def expr(self) -> dict:
        return {self.kind: {"Expression": {"SourceRef": {"Entity": self.table}}, "Property": self.name}}

    @property
    def ref(self) -> str:
        return f"{self.table}.{self.name}"

    def project(self, display: str | None = None) -> dict:
        out = {"field": self.expr(), "queryRef": self.ref, "nativeQueryRef": self.name}
        if display:
            out["displayName"] = display
        return out


def col(table, name):
    return Field(table, name, "Column")


def mea(table, name):
    return Field(table, name, "Measure")


def as_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def platform(kind: str) -> str:
    return as_json({"$schema": SCHEMAS["platform"], "metadata": {"type": kind, "displayName": NAME},
                    "config": {"version": "2.0", "logicalId": logical_id(f"platform:{kind}")}})


def container(title: str | None, subtitle: str | None = None, tip: str | None = None, card: bool = True,
              menu: bool = True, title_size: int = 11) -> dict:
    """The visual container: title, subtitle, white card, header (menu) and alt text."""
    vco = {
        "title": [{"properties": {"show": B(False)}}],
        "subTitle": [{"properties": {"show": B(False)}}],
        "background": [{"properties": {"show": B(card), "color": C(WHITE), "transparency": N(0)}}],
        "border": [{"properties": {"show": B(False), "radius": N(6 if card else 0)}}],
        "padding": [{"properties": {"top": N(8 if card else 0), "bottom": N(8 if card else 0),
                                    "left": N(10 if card else 0), "right": N(10 if card else 0)}}],
        "dropShadow": [{"properties": {"show": B(False)}}],
        "visualHeader": [{"properties": {"show": B(menu), "showTooltipButton": B(bool(tip))}}],
    }
    if title:
        vco["title"] = [{"properties": {"show": B(True), "text": S(title), "fontSize": N(title_size), "bold": B(True),
                                        "fontColor": C(INK), "titleWrap": B(True), "alignment": S("left")}}]
        vco["general"] = [{"properties": {"altText": S(title + (f". {subtitle}" if subtitle else ""))}}]
    if subtitle:
        vco["subTitle"] = [{"properties": {"show": B(True), "text": S(subtitle), "fontSize": N(9),
                                           "fontColor": C(INK_SECONDARY), "titleWrap": B(True),
                                           "alignment": S("left")}}]
    if tip:
        vco["visualHeaderTooltip"] = [{"properties": {"text": S(tip)}}]
    return vco


def axis(title: str | None = None, gridlines: bool = False) -> list:
    props = {"show": B(True), "fontSize": N(9), "labelColor": C(INK_SECONDARY), "showAxisTitle": B(bool(title)),
             "gridlineShow": B(gridlines)}
    if title:
        props |= {"titleText": S(title), "titleFontSize": N(9), "titleColor": C(INK_SECONDARY)}
    if gridlines:
        props |= {"gridlineColor": C(GRIDLINE)}
    return [{"properties": props}]


def legend(show: bool) -> list:
    props = {"show": B(show)}
    if show:
        props |= {"position": S("Top"), "fontSize": N(9), "labelColor": C(INK_SECONDARY), "showTitle": B(False)}
    return [{"properties": props}]


def series_colours(column: Field, colours: dict) -> list:
    """One colour per value of a column (a legend's series, or a bar chart's categories), so a thing keeps its
    colour on every chart."""
    return [{
        "properties": {"fill": C(colour)},
        "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": column.expr(), "Right": S(value)["expr"],
        }}}]},
    } for value, colour in colours.items()]


def measure_colours(colours: dict) -> list:
    """One colour per measure, for charts with two measures and no legend column."""
    return [{"properties": {"fill": C(colour)}, "selector": {"metadata": measure.ref}}
            for measure, colour in colours.items()]


def single_colour(colour: str) -> list:
    return [{"properties": {"defaultColor": C(colour)}}]


def labels(show: bool) -> list:
    props = {"show": B(show)}
    if show:
        props |= {"fontSize": N(9), "color": C(INK_SECONDARY)}
    return [{"properties": props}]


def sort_by(fld: Field, descending: bool = False) -> dict:
    return {"sort": [{"field": fld.expr(), "direction": "Descending" if descending else "Ascending"}],
            "isDefaultSort": False}


@dataclass
class Visual:
    key: str
    x: int
    y: int
    w: int
    h: int
    body: dict
    data: bool = True   # a chart or table, rather than text

    def fields(self) -> list:
        state = self.body.get("query", {}).get("queryState", {})
        return [p["queryRef"] for role in state.values() for p in role["projections"]]


# Chart types whose legend and axes Power BI may hide at small sizes unless "responsive" is off
RESPONSIVE = {"lineChart", "clusteredBarChart", "columnChart", "stackedAreaChart"}


def chart(key, box, kind, roles: dict, *, title, subtitle=None, tip=None, objects=None, sort=None,
          title_size=11) -> Visual:
    objects = dict(objects or {})
    if kind in RESPONSIVE:
        objects["general"] = [{"properties": {"responsive": B(False)}}]
    body = {
        "visualType": kind,
        "query": {"queryState": {role: {"projections": projections} for role, projections in roles.items()}},
        "objects": objects,
        "visualContainerObjects": container(title, subtitle, tip, title_size=title_size),
        "drillFilterOtherVisuals": True,
    }
    if sort:
        body["query"]["sortDefinition"] = sort
    return Visual(key, *box, body)


def text_run(text: str, size: int, colour: str = INK, bold: bool = False) -> dict:
    style = {"fontSize": f"{size}pt", "color": colour}
    if bold:
        style["fontWeight"] = "bold"
    return {"value": text, "textStyle": style}


def textbox(key, box, paragraphs: list, card: bool = False) -> Visual:
    """Static text. `paragraphs` is a list of paragraphs, each a list of text runs."""
    body = {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": [
            {"textRuns": runs, "horizontalTextAlignment": "left"} for runs in paragraphs
        ]}}]},
        "visualContainerObjects": container(None, card=card, menu=False),
    }
    return Visual(key, *box, body, data=False)


def header(title: str, subtitle: str) -> Visual:
    return textbox("header", (24, 4, 1232, 64), [[text_run(title, 18, INK, bold=True)],
                                                 [text_run(subtitle, 11, INK_SECONDARY)]])


def footer() -> Visual:
    return textbox("footer", (24, 694, 1232, 20), [[text_run(FOOTER, 8, INK_SECONDARY)]])


# --------------------------------------------------------------------------------------------
# The numbers quoted in titles, read from the same table the charts draw
# --------------------------------------------------------------------------------------------

def month_name(value) -> str:
    return pd.Timestamp(value).strftime("%B %Y")


def pct(value, places=1) -> str:
    return f"{value * 100:.{places}f}%"


def shown(value, fmt: str) -> str:
    """A value as the measure's format string shows it."""
    if fmt == COUNT:
        return f"{value:,.0f}"
    if fmt == NUMBER:
        return f"{value:,.1f}"
    if fmt in (PCT0, PCT1, PCT2):
        return pct(value, {PCT0: 0, PCT1: 1, PCT2: 2}[fmt])
    if fmt == RM_MILLIONS:
        return f"RM{value:,.1f}m"
    return f"RM{value:,.0f}"


class Facts:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def chart(self, name: str) -> pd.DataFrame:
        rows = self.data[self.data["chart"] == name]
        if rows.empty:
            raise ValueError(f"dashboard_data.csv has no rows for chart {name}")
        return rows

    def pivot(self, name, value, index="category", columns="series"):
        return self.chart(name).pivot(index=index, columns=columns, values=value)

    def latest(self, name, measure):
        """The latest actual, the month it is for, and the plan or target that month."""
        rows = self.chart(name).dropna(subset=[measure])
        actual = rows[rows["series"] == "Actual"].sort_values("month").iloc[-1]
        other = rows[(rows["series"] != "Actual") & (rows["month"] == actual["month"])]
        compare = (other["series"].iloc[0], other[measure].iloc[0]) if len(other) else (None, None)
        return actual["month"], actual[measure], compare

    def actuals(self, kpi: str, measure: str) -> pd.Series:
        rows = self.chart(f"trend_{kpi}")
        return rows[rows["series"] == "Actual"].dropna(subset=[measure]).set_index("month")[measure].sort_index()

    def definition(self, kpi: str) -> str:
        return self.chart(f"trend_{kpi}")["detail"].dropna().iloc[0]

    @property
    def last_month(self) -> str:
        return self.chart("trend_K02")["month"].max()


CSV_COLUMN = {"Count": "count", "Rate": "rate", "RM millions": "rm_millions", "RM": "rm", "Number": "number"}


def trend(facts: Facts, kpi: str, box, title_size: int = 11) -> Visual:
    """One KPI by month: the actual line, and the plan or target line beside it."""
    name, column, fmt, _ = KPI_MEASURES[kpi]
    measure = CSV_COLUMN[column]
    month, actual, (other, other_value) = facts.latest(f"trend_{kpi}", measure)
    note = month_name(month)
    if other:
        note += f" · {other.lower()} {shown(other_value, fmt)}"
    history = facts.actuals(kpi, measure)
    if kpi == "K14":
        note += f" · low {pct(history.min())} in {month_name(history.idxmin())}, in the Raya FD promotion"
    if kpi == "K15":
        note += f" · peak {pct(history.max(), 2)} in {month_name(history.idxmax())}"
    series = col("KPI trend", "Series")
    colours = {"Actual": BLUE, **({other: PLAN_GREY} if other else {})}
    return chart(f"trend {kpi}", box, "lineChart", {
        "Category": [col("KPI trend", "Month").project()],
        "Series": [series.project()],
        "Y": [mea("KPI trend", name).project()],
    }, title=f"{name}: {shown(actual, fmt)}", subtitle=note, tip=f"{name}: {facts.definition(kpi)}",
        sort=sort_by(col("KPI trend", "Month")), title_size=title_size, objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(series, colours),
            "lineStyles": [{"properties": {"strokeWidth": N(2), "showMarker": B(False)}}],
        })


def kpi_lines(facts: Facts, key, box, kpis: dict, title, subtitle=None) -> Visual:
    """Rate KPIs on one chart, actual values only. `kpis` maps each KPI to its name in the legend."""
    measures = [mea("KPI trend", KPI_MEASURES[k][0]) for k in kpis]
    tip = " ".join(f"{KPI_MEASURES[k][0]}: {facts.definition(k).rstrip('.')}." for k in kpis)
    return chart(key, box, "lineChart", {
        "Category": [col("KPI trend", "Month").project()],
        "Y": [m.project(label) for m, label in zip(measures, kpis.values())],
    }, title=title, subtitle=subtitle, tip=tip, sort=sort_by(col("KPI trend", "Month")), objects={
        "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
        "dataPoint": measure_colours(dict(zip(measures, [BLUE, ORANGE, AQUA]))),
        "lineStyles": [{"properties": {"strokeWidth": N(2), "showMarker": B(False)}}],
    })


# --------------------------------------------------------------------------------------------
# The pages
# --------------------------------------------------------------------------------------------

@dataclass
class Page:
    name: str
    visuals: list


def grid(columns: list, y: int, h: int) -> list:
    """Boxes along one row, from x = 24, 12 pixels apart: columns is a list of widths."""
    boxes, x = [], 24
    for w in columns:
        boxes.append((x, y, w, h))
        x += w + 12
    return boxes


ROW1, ROW2, ROW_H = 72, 385, 301
THIRDS = [402, 403, 403]
QUARTERS = [299, 299, 299, 299]


def executive(facts: Facts) -> Page:
    tiles = facts.chart("tiles").sort_values("sort")
    on_plan = int((tiles["status"] == "On plan").sum())
    words = {0: "None", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    summary = (f"{words[on_plan]} of the six plan KPIs {'is' if on_plan == 1 else 'are'} on plan" if on_plan < 6
               else "All six plan KPIs are on plan")
    for status, phrase in [("Watch", "on watch"), ("Off plan", "off plan")]:
        names = tiles.loc[tiles["status"] == status, "category"].tolist()
        if names:
            summary += f"; {phrase}: " + (names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1])
    month = month_name(facts.last_month)
    if len(tiles) != 6:
        raise ValueError(f"expected 6 scorecard rows, found {len(tiles)}")

    cost = facts.pivot("channel_cost", "rm")
    cheap = cost["Per new customer"].idxmin()
    casa = facts.actuals("K14", "rate")
    drop = casa.diff().idxmin()
    before, low = casa[casa.index < drop].iloc[-1], casa[casa.index >= drop].min()
    peak = facts.actuals("K15", "rate").max()
    curves = facts.pivot("vintage", "rate", index="x")
    v1, v2 = curves.loc[6, "v1 launch policy"], curves.loc[6, "v2 growth policy"]
    callouts = [
        (f"{cheap} sign-ups do not stay",
         f"RM{cost.loc[cheap, 'Per new customer']:.0f} per new customer, but "
         f"RM{cost.loc[cheap, 'Per customer active in month 3']:.0f} per customer still active in month 3. "
         "Owner: Head of Growth."),
        ("The Raya FD promotion diluted CASA",
         f"The CASA ratio fell from {before * 100:.0f}% to {low * 100:.0f}%, and cost of funds peaked at "
         f"{pct(peak, 2)}. Owner: Treasurer."),
        ("v2 policy loans go bad faster",
         f"{pct(v2)} were 30+ days past due by month 6, against {pct(v1)} under the v1 policy. "
         "Owner: Head of Credit Risk."),
    ]

    sc = "Scorecard"
    scorecard = chart("scorecard", (24, 72, 460, 250), "tableEx", {"Values": [
        col(sc, "KPI").project(),
        col(sc, "Actual").project(pd.Timestamp(facts.last_month).strftime("%b %Y")),
        col(sc, "Plan").project(),
        col(sc, "% of plan").project(),
        col(sc, "Status label").project("Status"),
    ]}, title=f"Plan KPIs, {month}", subtitle="▲ on plan    ● watch: within the amber band    ▼ off plan",
        sort=sort_by(col(sc, "KPI")), objects={
            "columnHeaders": [{"properties": {"fontSize": N(9), "bold": B(True), "fontColor": C(INK_SECONDARY),
                                              "backColor": C(WHITE), "autoSizeColumnWidth": B(True),
                                              "columnAdjustment": S("growToFit"), "wordWrap": B(True)}}],
            "values": [
                {"properties": {"fontSize": N(9), "backColorPrimary": C(WHITE), "backColorSecondary": C(WHITE),
                                "fontColorPrimary": C(INK), "fontColorSecondary": C(INK)}},
                {"properties": {"backColor": {"solid": {"color": {"expr": mea(sc, "Status colour").expr()}}}},
                 "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                              "metadata": col(sc, "Status label").ref}},
            ],
            "grid": [{"properties": {"gridHorizontal": B(True), "gridHorizontalColor": C(GRIDLINE),
                                     "gridVertical": B(False), "rowPadding": N(4)}}],
            "total": [{"properties": {"totals": B(False)}}],
        })
    scorecard.body["visualContainerObjects"]["stylePreset"] = [{"properties": {"name": S("None")}}]

    x0 = 496

    def right(y, h):
        """Three boxes across the right of the page, from x = 496 to 1256."""
        return [(x, y, w, h) for x, w in zip([x0, x0 + 257, x0 + 514], [245, 245, 246])]

    visuals = [
        header(f"Kelip Bank executive scorecard, {month}", summary + "."),
        scorecard,
        trend(facts, "K22", (24, 334, 460, 352)),
        textbox("attention", (x0, 72, 760, 26), [[
            text_run("What needs attention", 12, INK, bold=True),
            text_run("    The insights report has the evidence and a recommendation for each.", 9, INK_SECONDARY),
        ]]),
        *[textbox(f"callout {i + 1}", box, [[text_run(lead, 11, INK, bold=True)],
                                            [text_run(body, 10, INK_SECONDARY)]], card=True)
          for i, ((lead, body), box) in enumerate(zip(callouts, right(102, 118)))],
        *[trend(facts, kpi, box, title_size=10) for kpi, box in zip(["K02", "K07", "K13"], right(232, 221))],
        *[trend(facts, kpi, box, title_size=10) for kpi, box in zip(["K14", "K15", "K19"], right(465, 221))],
        footer(),
    ]
    return Page("Executive", visuals)


def growth(facts: Facts) -> Page:
    cost = facts.pivot("channel_cost", "rm")
    cheap = cost["Per new customer"].idxmin()
    dearest = cost["Per customer active in month 3"].idxmax()
    if cheap == dearest:
        cost_title = (f"{cheap} is the cheapest paid channel per new customer "
                      f"(RM{cost.loc[cheap, 'Per new customer']:.0f}) but the dearest per customer "
                      f"still active in month 3 (RM{cost.loc[cheap, 'Per customer active in month 3']:.0f})")
    else:
        cost_title = "Cost per new customer and per customer still active in month 3, by paid channel"
    basis = col("Channel cost", "Cost basis")
    channel_cost = chart("channel cost", grid(THIRDS, ROW1, ROW_H)[0], "clusteredBarChart", {
        "Category": [col("Channel cost", "Channel").project()],
        "Series": [basis.project()],
        "Y": [mea("Channel cost", "Cost per customer").project()],
    }, title=cost_title, subtitle=f"Paid channels, customers who joined up to {month_name(LAST_OBSERVED_COHORT)}",
        sort=sort_by(col("Channel cost", "Channel")), objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(basis, dict(zip(COST_BASES, [BLUE, ORANGE]))), "labels": labels(True),
        })

    funnel = facts.pivot("funnel_ab", "rate")
    steps = facts.chart("funnel_ab").drop_duplicates("category").sort_values("sort")["category"].tolist()
    gap = (funnel["Guided"] - funnel["Control"]).reindex(steps)
    widest = gap.diff().idxmax()
    flow = col("Sign-up funnel", "Flow")
    funnel_chart = chart("funnel", grid(THIRDS, ROW1, ROW_H)[1], "lineChart", {
        "Category": [col("Sign-up funnel", "Step").project()],
        "Series": [flow.project()],
        "Y": [mea("Sign-up funnel", "Share of applicants").project()],
    }, title=(f"The guided eKYC flow opened accounts for {pct(funnel.loc[steps[-1], 'Guided'])} of applicants, "
              f"against {pct(funnel.loc[steps[-1], 'Control'])} in control; the gap opens at '{widest}'"),
        subtitle="% of applicants in each flow reaching each step", sort=sort_by(col("Sign-up funnel", "Step")),
        objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(flow, {"Control": CONTEXT_GREY, "Guided": BLUE}),
            "lineStyles": [{"properties": {"strokeWidth": N(2), "showMarker": B(True)}}],
        })

    k03, k04 = facts.actuals("K03", "rate"), facts.actuals("K04", "rate")
    onboarding = kpi_lines(
        facts, "onboarding rates", grid(THIRDS, ROW1, ROW_H)[2],
        {"K03": "Onboarding conversion", "K04": "eKYC completion", "K06": "Active in month 3"},
        f"Onboarding conversion {pct(k03.iloc[-1])} and eKYC completion {pct(k04.iloc[-1])} in "
        f"{month_name(k03.index[-1])}",
        "Actual rates by month; activity in month 3 takes three months to see, so its latest months are blank")

    new = facts.chart("new_by_channel")
    last = new[new["month"] == new["month"].max()].set_index("series")["count"]
    channel = col("New customers by channel", "Channel")
    new_chart = chart("new by channel", grid(THIRDS, ROW2, ROW_H)[0], "columnChart", {
        "Category": [col("New customers by channel", "Month").project()],
        "Series": [channel.project()],
        "Y": [mea("New customers by channel", "Channel new customers").project()],
    }, title=(f"{last.idxmax()} brought the most new customers in {month_name(new['month'].max())}: "
              f"{last.max():,.0f} of {last.sum():,.0f}"), subtitle="New customers each month, by channel",
        sort=sort_by(col("New customers by channel", "Month")), objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(channel, dict(zip(CHANNEL_ORDER, [BLUE, ORANGE, AQUA, GOLD, PINK, GREEN]))),
        })

    lower = grid(THIRDS, ROW2, ROW_H)
    return Page("Growth", [
        header("Growth and onboarding", "Where customers come from, what they cost, and where applicants drop out"),
        channel_cost, funnel_chart, onboarding, new_chart,
        trend(facts, "K01", lower[1]), trend(facts, "K02", lower[2]),
        footer(),
    ])


def engagement(facts: Facts) -> Page:
    top = grid(QUARTERS, ROW1, ROW_H)
    k08, k10 = facts.actuals("K08", "rate"), facts.actuals("K10", "rate")
    rates = kpi_lines(facts, "engagement rates", top[1], {"K08": "Active rate", "K10": "Card activated in 30 days"},
                      f"Active rate {pct(k08.iloc[-1])} in {month_name(k08.index[-1])}; card activation "
                      f"{pct(k10.iloc[-1])} in {month_name(k10.index[-1])}",
                      "Card activation takes 30 days to see, so its latest month is blank")

    bottom = grid(THIRDS, ROW2, ROW_H)
    recent = f"{month_name(RECENT_FROM).split()[0]} to {month_name(facts.last_month)}"
    spend = facts.chart("card_categories").sort_values("sort")
    top_two = spend["rm_millions"].iloc[:2].sum() / spend["rm_millions"].sum()
    categories = chart("card categories", bottom[0], "clusteredBarChart", {
        "Category": [col("Card spend by category", "Merchant category").project()],
        "Y": [mea("Card spend by category", "Category card spend").project()],
    }, title=(f"{spend['category'].iloc[0]} and {spend['category'].iloc[1].lower()} took {top_two * 100:.0f}% "
              f"of card spend from {recent}"), subtitle="Debit card spend, RM millions",
        sort=sort_by(mea("Card spend by category", "Category card spend"), descending=True), objects={
            "legend": legend(False), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": single_colour(BLUE), "labels": labels(True),
        })

    declines = facts.chart("declines")
    latest = declines[declines["month"] == declines["month"].max()].set_index("series")["count"]
    approval = facts.latest("trend_K12", "rate")[1]
    reason = col("Card declines", "Reason")
    declined = chart("declines", bottom[1], "columnChart", {
        "Category": [col("Card declines", "Month").project()],
        "Series": [reason.project()],
        "Y": [mea("Card declines", "Declined payments").project()],
    }, title=(f"{pct(approval)} of card payments were approved in {month_name(declines['month'].max())}; "
              f"{latest.idxmax().lower()} caused {pct(latest.max() / latest.sum(), 0)} of declines"),
        subtitle="Declined card payments each month, by reason", sort=sort_by(col("Card declines", "Month")),
        objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(reason, dict(zip(DECLINE_ORDER, [BLUE, ORANGE, AQUA]))),
        })

    shares = facts.pivot("segments", "rate")
    share_of = col("Customer segments", "Share of")
    segments = chart("segments", bottom[2], "clusteredBarChart", {
        "Category": [col("Customer segments", "Segment").project()],
        "Series": [share_of.project()],
        "Y": [mea("Customer segments", "Segment share").project()],
        "Tooltips": [mea("Customer segments", "Segment action").project("Action"),
                     mea("Customer segments", "Segment owner").project("Owner")],
    }, title=(f"{shares['Deposits'].idxmax()} hold {pct(shares['Deposits'].max(), 0)} of deposits; "
              f"{shares['Card spend'].idxmax().lower()} make {pct(shares['Card spend'].max(), 0)} of card spend"),
        subtitle="Each segment's share of customers, deposits and card spend. Hover a bar for its action.",
        sort=sort_by(col("Customer segments", "Segment")), objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(share_of, dict(zip(SEGMENT_SERIES, [BLUE, ORANGE, AQUA]))),
        })

    return Page("Engagement", [
        header("Engagement and cards", "How many customers use the bank, what they spend on, and who they are"),
        trend(facts, "K07", top[0]), rates, trend(facts, "K09", top[2]), trend(facts, "K11", top[3]),
        categories, declined, segments,
        footer(),
    ])


def deposits(facts: Facts) -> Page:
    top, bottom = grid(THIRDS, ROW1, ROW_H), grid(THIRDS, ROW2, ROW_H)
    mix = facts.chart("deposit_mix")
    now = mix[mix["month"] == mix["month"].max()].set_index("series")["rm_millions"]
    kind = col("Deposit mix", "Deposit type")
    mix_chart = chart("deposit mix", top[1], "stackedAreaChart", {
        "Category": [col("Deposit mix", "Month").project()],
        "Series": [kind.project()],
        "Y": [mea("Deposit mix", "Deposit balance").project()],
    }, title=(f"Savings are {pct(now['Savings (CASA)'] / now.sum(), 0)} of RM{now.sum():,.1f}m deposits "
              f"in {month_name(mix['month'].max())}"), subtitle="Balances at month end, RM millions",
        sort=sort_by(col("Deposit mix", "Month")), objects={
            "legend": legend(True), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(kind, dict(zip(DEPOSIT_ORDER, [BLUE, ORANGE, AQUA]))),
        })

    kept = facts.chart("fd_retention").set_index("category")["rate"]
    fd_type = col("FD retention", "FD type")
    retention = chart("fd retention", bottom[2], "clusteredBarChart", {
        "Category": [fd_type.project()],
        "Y": [mea("FD retention", "Money kept at maturity").project()],
    }, title=(f"{pct(kept['Raya promotion deposits'], 0)} of Raya promotion money stayed 30 days after maturity, "
              f"against {pct(kept['Standard fixed deposits'], 0)} of standard fixed deposits"),
        subtitle="Share of matured money still at Kelip Bank 30 days later",
        sort=sort_by(fd_type), objects={
            "legend": legend(False), "categoryAxis": axis(), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(fd_type, dict(zip(DEPOSIT_ORDER[1:], [ORANGE, AQUA]))),
            "labels": labels(True),
        })

    return Page("Deposits", [
        header("Deposits and funding", "How deposits and their cost are tracking, and what the Raya promotion did"),
        trend(facts, "K13", top[0]), mix_chart, trend(facts, "K22", top[2]),
        trend(facts, "K14", bottom[0]), trend(facts, "K15", bottom[1]), retention,
        footer(),
    ])


def credit(facts: Facts) -> Page:
    top = grid(QUARTERS, ROW1, ROW_H)
    bottom = grid([440, 300, 468], ROW2, ROW_H)
    curves = facts.pivot("vintage", "rate", index="x")
    v1, v2 = curves.loc[6, "v1 launch policy"], curves.loc[6, "v2 growth policy"]
    policy = col("Vintage", "Policy")
    vintage = chart("vintage", bottom[0], "lineChart", {
        "Category": [col("Vintage", "Months on book").project()],
        "Series": [policy.project()],
        "Y": [mea("Vintage", "Share 30+ days past due").project()],
    }, title=(f"Loans approved under the v2 growth policy were {v2 / v1:.1f} times as likely to be 30+ days "
              f"past due by month 6 ({pct(v2)} against {pct(v1)})"),
        subtitle="% of loans ever 30+ days past due, by months on book",
        sort=sort_by(col("Vintage", "Months on book")), objects={
            "legend": legend(True), "categoryAxis": axis("Months on book"), "valueAxis": axis(gridlines=True),
            "dataPoint": series_colours(policy, dict(zip(POLICIES, [BLUE, ORANGE, AQUA]))),
            "lineStyles": [{"properties": {"strokeWidth": N(2), "showMarker": B(True)}}],
        })

    roll = facts.pivot("roll_rates", "rate")
    share = mea("Roll rates", "Share of loans")
    recent = f"{month_name(RECENT_FROM).split()[0]} to {month_name(facts.last_month)}"
    roll_rates = chart("roll rates", bottom[2], "pivotTable", {
        "Rows": [col("Roll rates", "From").project()],
        "Columns": [col("Roll rates", "To").project()],
        "Values": [share.project()],
    }, title=(f"{pct(roll.loc['30-59 days', '60-90 days'], 0)} of loans 30-59 days past due rolled to 60-90 days "
              f"a month later, and {pct(roll.loc['60-90 days', '90+ days'], 0)} of those to 90+"),
        subtitle=f"Share of loans moving from each bucket (rows) to the next month's (columns), {recent}",
        objects={
            "columnHeaders": [{"properties": {"fontSize": N(9), "bold": B(True), "fontColor": C(INK_SECONDARY),
                                              "backColor": C(WHITE), "autoSizeColumnWidth": B(True),
                                              "columnAdjustment": S("growToFit"), "wordWrap": B(True)}}],
            "rowHeaders": [{"properties": {"fontSize": N(9), "fontColor": C(INK), "backColor": C(WHITE)}}],
            "values": [
                {"properties": {"fontSize": N(9), "backColorPrimary": C(WHITE), "backColorSecondary": C(WHITE),
                                "fontColorPrimary": C(INK), "fontColorSecondary": C(INK)}},
                {"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
                    "Input": {"SelectRef": {"ExpressionName": share.ref}},
                    "FillRule": {"linearGradient2": {
                        "min": {"color": {"Literal": {"Value": f"'{BLUES[0]}'"}}},
                        "max": {"color": {"Literal": {"Value": f"'{BLUES[2]}'"}}},
                        "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}},
                    }},
                }}}}}},
                 "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": share.ref}},
            ],
            "subTotals": [
                {"properties": {"rowSubtotals": B(False)}, "selector": {"id": "Row"}},
                {"properties": {"columnSubtotals": B(False)}, "selector": {"id": "Column"}},
            ],
            "grid": [{"properties": {"gridHorizontal": B(True), "gridHorizontalColor": C(GRIDLINE),
                                     "gridVertical": B(False), "rowPadding": N(4)}}],
        })
    roll_rates.body["visualContainerObjects"]["stylePreset"] = [{"properties": {"name": S("None")}}]

    return Page("Credit", [
        header("Credit risk", "Whether the loan book is healthy, and whether the credit policy change mattered"),
        *[trend(facts, kpi, box) for kpi, box in zip(["K17", "K18", "K19", "K20"], top)],
        vintage, trend(facts, "K21", bottom[1]), roll_rates,
        footer(),
    ])


# --------------------------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------------------------

def page_files(page: Page) -> dict:
    page_id = hex_id(f"page:{page.name}")
    folder = f"{REPORT}/definition/pages/{page_id}"
    files, names = {}, []
    for i, v in enumerate(page.visuals):
        name = hex_id(f"visual:{page.name}:{v.key}")
        names.append((name, v.data))
        files[f"{folder}/visuals/{name}/visual.json"] = as_json({
            "$schema": SCHEMAS["visual"],
            "name": name,
            "position": {"x": v.x, "y": v.y, "z": i * 1000, "height": v.h, "width": v.w, "tabOrder": i * 1000},
            "visual": v.body,
        })
    data = [name for name, is_data in names if is_data]
    files[f"{folder}/page.json"] = as_json({
        "$schema": SCHEMAS["page"],
        "name": page_id,
        "displayName": page.name,
        "displayOption": "FitToPage",
        "height": HEIGHT,
        "width": WIDTH,
        "objects": {
            "background": [{"properties": {"color": C(CANVAS), "transparency": N(0)}}],
            "outspace": [{"properties": {"color": C(CANVAS), "transparency": N(0)}}],
        },
        # Each chart stands alone: selecting a point shows its tooltip without filtering the others
        "visualInteractions": [{"source": s, "target": t, "type": "NoFilter"}
                               for s in data for t in data if s != t],
    })
    return files


def report_files(pages: list) -> dict:
    page_ids = [hex_id(f"page:{p.name}") for p in pages]
    files = {
        f"{REPORT}/.platform": platform("Report"),
        f"{REPORT}/definition.pbir": as_json({"$schema": SCHEMAS["pbir"], "version": "4.0",
                                              "datasetReference": {"byPath": {"path": f"../{MODEL}"}}}),
        f"{REPORT}/definition/version.json": as_json({"$schema": SCHEMAS["version"], "version": "2.0.0"}),
        f"{REPORT}/definition/report.json": as_json({
            "$schema": SCHEMAS["report"],
            "themeCollection": {"baseTheme": {
                "name": BASE_THEME_NAME,
                "reportVersionAtImport": {"visual": "2.11.0", "report": "3.4.0", "page": "2.3.1"},
                "type": "SharedResources",
            }},
            "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [
                {"name": BASE_THEME_NAME, "path": f"BaseThemes/{BASE_THEME_NAME}.json", "type": "BaseTheme"},
            ]}],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "AllowSummarized",
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
                "useDefaultAggregateDisplayName": True,
            },
        }),
        f"{REPORT}/definition/pages/pages.json": as_json({"$schema": SCHEMAS["pages"], "pageOrder": page_ids,
                                                          "activePageName": page_ids[0]}),
        f"{REPORT}/StaticResources/SharedResources/BaseThemes/{BASE_THEME_NAME}.json":
            BASE_THEME.read_text(encoding="utf-8"),
    }
    for page in pages:
        files |= page_files(page)
    return files


def project_files(data: pd.DataFrame, data_dir: str) -> dict:
    """Every file of the Power BI project, as {path relative to dashboards/powerbi: text}."""
    facts = Facts(data)
    definitions = {k: facts.definition(k) for k in KPI_MEASURES}
    pages = [executive(facts), growth(facts), engagement(facts), deposits(facts), credit(facts)]
    files = {f"{NAME}.pbip": as_json({"$schema": SCHEMAS["pbip"], "version": "1.0",
                                      "artifacts": [{"report": {"path": REPORT}}],
                                      "settings": {"enableAutoRecovery": True}})}
    files |= model_files(tables(definitions), data_dir)
    files |= report_files(pages)
    return files


def write(files: dict) -> None:
    """Replace the project's files. Only the model and report folders are cleared of files the generator no
    longer writes; Power BI Desktop's own .pbi folders (local settings and data cache), and anything else
    saved in dashboards/powerbi/, are left alone."""
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    for folder in (PROJECT_DIR / MODEL, PROJECT_DIR / REPORT):
        for path in sorted(folder.rglob("*"), reverse=True) if folder.exists() else []:
            if ".pbi" in path.relative_to(PROJECT_DIR).parts:
                continue
            if path.is_file() and path.relative_to(PROJECT_DIR).as_posix() not in files:
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    for rel, text in files.items():
        target = PROJECT_DIR / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")


def build() -> dict:
    """Write the project from dashboard_data.csv and return a summary of what it holds."""
    data = pd.read_csv(DATA, dtype={"month": str})
    data_dir = os.environ.get(DATA_DIR_ENV, DEFAULT_DATA_DIR)
    files = project_files(data, data_dir)
    write(files)
    pages = json.loads(files[f"{REPORT}/definition/pages/pages.json"])["pageOrder"]
    names = [json.loads(files[f"{REPORT}/definition/pages/{p}/page.json"])["displayName"] for p in pages]
    visuals = sum(1 for rel in files if rel.endswith("/visual.json"))
    model_tables = sum(1 for rel in files if "/definition/tables/" in rel)
    return {"path": PROJECT_DIR / f"{NAME}.pbip", "pages": names, "visuals": visuals, "tables": model_tables,
            "data_dir": data_dir}

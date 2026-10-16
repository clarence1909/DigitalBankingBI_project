"""The Excel KPI pack: a formula-driven workbook built from the warehouse.

Sheets
  Cover          what the pack is, how to use it, and the colour key
  Scorecard      the six plan KPIs for a month you pick, with status against plan
  Trend          one scorecard KPI against plan by month, with a line chart
  Monthly KPIs   all 22 KPIs for all 24 months
  Checks         the pack's totals tied to control totals computed separately in SQL
  KPI data, Plan, KPI catalog   the data the formulas read, exported from the warehouse

Typed-in numbers live only on the data sheets and in the SQL control totals
(blue text). Everything on the report sheets is a formula (black text), so the
pack recalculates when a reader picks a month or a KPI, or pastes in a newer
export. The formulas stick to functions that Excel 2007 or later and
LibreOffice both calculate (SUMIFS, COUNTIFS, INDEX, MATCH, EDATE, TEXT), so
the pack can be recalculated and checked headless in CI.
"""

from datetime import date, datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import ChartLines, DateAxis
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.comments import Comment
from openpyxl.drawing.line import LineProperties
from openpyxl.formatting.rule import FormulaRule, Rule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.styles.numbers import NumberFormat
from openpyxl.utils import get_column_letter
from openpyxl.utils.indexed_list import IndexedList
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink

from src.config import REPORTS_DIR
from src.util import normalise_xlsx

PACK = REPORTS_DIR / "kelip_bank_kpi_pack.xlsx"
REPORT_MONTH = date(2026, 8, 1)     # the month the scorecard opens on
TREND_FROM = date(2025, 1, 1)       # every scorecard KPI has a plan from here
DEFAULT_TREND_KPI = "K13"
BUILT = datetime(2026, 9, 1)        # fixed, so a rerun writes a byte-identical file

SYNTHETIC = "Synthetic data: Kelip Bank is a fictional Malaysian digital bank, and every figure is simulated."

# Text is ink; blue marks typed-in data and yellow the cells a reader changes
FONT = "Arial"
INK, INK_2, MUTED = "0B0B0B", "52514E", "898781"
INPUT = "0000FF"
LINK = "0563C1"
HEADER_FILL = "EDECE7"
RULE = "C3C2B7"
SELECT_FILL = "FFFF00"
MONTH_HIGHLIGHT = "E3EEFB"
STATUS = {  # label: (icon, icon colour, cell tint); a word and an icon always go with the colour
    "On plan": ("▲", "0CA30C", "DDF2DD"),
    "Watch": ("●", "D99400", "FEF0CC"),
    "Off plan": ("▼", "D03B3B", "F8DEDE"),
}
RESULT_TINT = {"PASS": "DDF2DD", "FAIL": "F8DEDE"}
LINE_ACTUAL, LINE_PLAN, GRID = "2A78D6", "898781", "E1E0D9"

THIN = Side(style="thin", color=RULE)
TREND_FIRST_ROW = 14                # first month row of the trend table


def font(size=10, bold=False, italic=False, color=INK, underline=None):
    return Font(name=FONT, size=size, bold=bold, italic=italic, color=color, underline=underline)


def fill(colour):
    return PatternFill("solid", fgColor=colour)


def write(ws, ref, value, fmt=None, **style):
    """Write a value or formula with the house font; style keywords go to font()."""
    cell = ws[ref]
    cell.value = value
    cell.font = font(**style)
    if fmt:
        cell.number_format = fmt
    return cell


def header_row(ws, row, first_col, labels):
    for i, label in enumerate(labels):
        cell = ws.cell(row=row, column=first_col + i, value=label)
        cell.font = font(bold=True)
        cell.fill = fill(HEADER_FILL)
        cell.border = Border(bottom=THIN)
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def page_title(ws, title, subtitle=SYNTHETIC):
    write(ws, "B2", title, size=16, bold=True)
    write(ws, "B3", subtitle, italic=True, color=INK_2)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2


def widths(ws, spec):
    for col, width in spec.items():
        ws.column_dimensions[col].width = width


def landscape(ws):
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def plain(value):
    """pandas and numpy scalars to the Python types openpyxl writes."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if hasattr(value, "item"):
        return value.item()
    return value


def kpi_formats(data):
    """A number format per KPI, from its unit and the size of its values."""
    formats = {}
    for kpi_id, group in data.groupby("kpi_id"):
        unit, top = group["unit"].iloc[0], group["value"].abs().max()
        if unit == "count":
            fmt = "#,##0"
        elif unit == "number":
            fmt = "0.0"
        elif unit == "pct":
            fmt = "0.00%" if top < 0.1 else "0.0%"
        elif top >= 1e6:
            fmt = '"RM"#,##0.0,,"m"'
        elif top >= 1e5:
            fmt = '"RM"#,##0,"k"'
        else:
            fmt = '"RM"#,##0.00'
        formats[kpi_id] = fmt
    return formats


def signed(fmt):
    return f"+{fmt};-{fmt};{fmt}"


def status_formatting(ws, label_range, icon_range, first_label_cell):
    """Tint the status word and colour the icon, driven by the word."""
    for label, (icon, colour, tint) in STATUS.items():
        ws.conditional_formatting.add(
            label_range, FormulaRule(formula=[f'{first_label_cell}="{label}"'], fill=fill(tint)))
        ws.conditional_formatting.add(
            icon_range, FormulaRule(formula=[f'{first_label_cell}="{label}"'], font=font(bold=True, color=colour)))


def define(wb, name, sheet, cells):
    wb.defined_names[name] = DefinedName(name, attr_text=f"'{sheet}'!{cells}")


# --- data sheets -------------------------------------------------------------------------

def data_sheet(wb, name, frame, source, col_widths, value_formats=None):
    """A plain table: header in row 1, typed-in values in blue, a filter and frozen header."""
    ws = wb.create_sheet(name)
    ws.sheet_properties.tabColor = "B9B8B0"
    columns = list(frame.columns)
    header_row(ws, 1, 1, columns)
    for r, row in enumerate(frame.itertuples(index=False), start=2):
        for c, value in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=plain(value))
            cell.font = font(color=INPUT)
            if isinstance(cell.value, date):
                cell.number_format = "mmm yyyy"
            if value_formats and columns[c - 1] in value_formats:
                cell.number_format = value_formats[columns[c - 1]](row)
    last_row = len(frame) + 1
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{last_row}"
    ws["A1"].comment = Comment(f"Source: {source}. Exported by src/export/excel_pack.py.", "Kelip Bank BI")
    for i, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    return ws, last_row


# --- report sheets -----------------------------------------------------------------------

def cover_sheet(wb):
    ws = wb.active
    ws.title = "Cover"
    write(ws, "B2", "Kelip Bank KPI pack", size=18, bold=True)
    write(ws, "B3", "Monthly KPIs from September 2024 to August 2026, with a scorecard against plan.", color=INK_2)
    write(ws, "B5", "Synthetic data. Kelip Bank is a fictional Malaysian digital bank; every customer, account "
                    "and figure in this workbook is simulated.", bold=True)
    ws["B5"].fill = fill(STATUS["Watch"][2])
    ws.merge_cells("B5:C5")
    ws.sheet_view.showGridLines = False

    write(ws, "B7", "What is in the pack", size=12, bold=True)
    sheets = [
        ("Scorecard", "The six plan KPIs for a month you pick: actual, plan, % of plan, status and change "
                      "on the month before."),
        ("Trend", "One scorecard KPI against plan by month, January 2025 to August 2026, with a chart."),
        ("Monthly KPIs", "All 22 KPIs for all 24 months. The month picked on Scorecard is shaded."),
        ("Checks", "The pack's totals tied to control totals computed separately in SQL. Every row should "
                   "say PASS."),
        ("KPI data", "One row per KPI per month, exported from kpi.kpi_monthly."),
        ("Plan", "The monthly plan for the six scorecard KPIs, from reference.plan_targets."),
        ("KPI catalog", "Each KPI's definition, formula, owner, unit, direction and amber band."),
    ]
    for i, (sheet, text) in enumerate(sheets):
        row = 8 + i
        cell = write(ws, f"B{row}", sheet, color=LINK, underline="single")
        cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'{sheet}'!A1", display=sheet)
        write(ws, f"C{row}", text)

    write(ws, "B16", "How to use it", size=12, bold=True)
    steps = [
        "1. On Scorecard, pick a reporting month in the yellow cell. Status, variances and the headline update.",
        "2. On Trend, pick one of the six scorecard KPIs in the yellow cell. The table and chart update.",
        "3. Look at Checks: every row should say PASS. After pasting a newer export into the data sheets, "
        "the checks show whether the formulas still tie out.",
    ]
    for i, text in enumerate(steps):
        write(ws, f"B{17 + i}", text)
        ws.merge_cells(f"B{17 + i}:C{17 + i}")

    write(ws, "B21", "Colour key", size=12, bold=True)
    write(ws, "B22", 1234, "#,##0", color=INPUT)
    write(ws, "C22", "Blue text: data exported from the warehouse, or a control total computed in SQL")
    write(ws, "B23", "=B22*2", "#,##0")
    write(ws, "C23", "Black text: a formula")
    write(ws, "B24", "Pick me", bold=True, color=INPUT)
    ws["B24"].fill = fill(SELECT_FILL)
    write(ws, "C24", "Yellow cell: a choice you can change")
    for i, (label, (icon, colour, tint)) in enumerate(STATUS.items()):
        row = 25 + i
        write(ws, f"B{row}", f"{icon} {label}", bold=True)
        ws[f"B{row}"].fill = fill(tint)
    write(ws, "C25", "At plan or better")
    write(ws, "C26", "Worse than plan, but within the KPI's amber band")
    write(ws, "C27", "Worse than plan by more than the amber band")

    write(ws, "B29", "About the data", size=12, bold=True)
    notes = [
        "Built by src/export/excel_pack.py from the DuckDB warehouse: kpi.kpi_monthly, "
        "reference.plan_targets and reference.kpi_catalog.",
        "Data to 31 August 2026. Rebuild the warehouse and this pack with: python run_pipeline.py",
        "The formulas use only functions that Excel 2007 or later and LibreOffice both calculate.",
    ]
    for i, text in enumerate(notes):
        write(ws, f"B{30 + i}", text, color=INK_2)
        ws.merge_cells(f"B{30 + i}:C{30 + i}")
    widths(ws, {"A": 2, "B": 18, "C": 100})
    landscape(ws)


def scorecard_sheet(wb, scorecard_ids, formats):
    ws = wb.create_sheet("Scorecard")
    page_title(ws, "Monthly KPI scorecard")
    first, last = 10, 9 + len(scorecard_ids)
    status = f"$J${first}:$J${last}"

    write(ws, "B5", "Reporting month", bold=True)
    ws.merge_cells("B5:C5")
    write(ws, "D5", REPORT_MONTH, "mmm yyyy", bold=True, color=INPUT)
    ws["D5"].fill = fill(SELECT_FILL)
    ws["D5"].alignment = Alignment(horizontal="center")
    write(ws, "E5", "Pick a month from the list in the yellow cell.", italic=True, color=MUTED)
    pick = DataValidation(type="list", formula1="=month_list", allow_blank=False, showErrorMessage=True,
                          errorTitle="Pick a month", error="Pick a month from the list, September 2024 to August 2026.",
                          promptTitle="Reporting month", prompt="Pick the month to report on.", showInputMessage=True)
    ws.add_data_validation(pick)
    pick.add("D5")
    write(ws, "B7", f'=COUNTIF({status},"On plan")&" of "&ROWS({status})&" KPIs on plan in "&TEXT(report_month,"mmmm yyyy")'
                    f'&": "&COUNTIF({status},"Watch")&" to watch, "&COUNTIF({status},"Off plan")&" off plan."',
          size=12, bold=True)

    header_row(ws, 9, 2, ["KPI id", "KPI", "Owner", "Actual", "Plan", "% of plan", "Variance to plan", "",
                          "Status", "Prior month", "Change on prior month", "Better when", "Amber band"])
    for row, kpi_id in enumerate(scorecard_ids, start=first):
        fmt = formats[kpi_id]
        match = f"MATCH($B{row},cat_id,0)"
        actual = f"SUMIFS(data_value,data_kpi,$B{row},data_month,report_month)"
        prior = f"SUMIFS(data_value,data_kpi,$B{row},data_month,EDATE(report_month,-1))"
        cells = {
            "B": (kpi_id, None, {"color": INPUT}),
            "C": (f"=INDEX(cat_name,{match})", None, {}),
            "D": (f"=INDEX(cat_owner,{match})", None, {}),
            "E": (f'=IF(COUNTIFS(data_kpi,$B{row},data_month,report_month)=0,"",{actual})', fmt, {"bold": True}),
            "F": (f'=IF(COUNTIFS(plan_kpi,$B{row},plan_month,report_month)=0,"",'
                  f'SUMIFS(plan_value,plan_kpi,$B{row},plan_month,report_month))', fmt, {}),
            "G": (f'=IF(OR(E{row}="",F{row}=""),"",IF(F{row}=0,"",E{row}/F{row}))', "0.0%", {}),
            "H": (f'=IF(OR(E{row}="",F{row}=""),"",E{row}-F{row})', signed(fmt), {}),
            "I": (f'=IF(J{row}="On plan","▲",IF(J{row}="Watch","●",IF(J{row}="Off plan","▼","")))', None, {}),
            "J": (f'=IF(OR(E{row}="",F{row}=""),"No plan",IF($M{row}="higher",'
                  f'IF(E{row}>=F{row},"On plan",IF(E{row}>=F{row}*(1-$N{row}),"Watch","Off plan")),'
                  f'IF(E{row}<=F{row},"On plan",IF(E{row}<=F{row}*(1+$N{row}),"Watch","Off plan"))))', None,
                  {"bold": True}),
            "K": (f'=IF(COUNTIFS(data_kpi,$B{row},data_month,EDATE(report_month,-1))=0,"",{prior})', fmt, {}),
            "L": (f'=IF(OR(E{row}="",K{row}=""),"",IF(ABS(E{row}-K{row})<=ABS(K{row})*0.001,"Flat",'
                  f'IF((E{row}>K{row})=($M{row}="higher"),"Better","Worse")))', None, {}),
            "M": (f"=INDEX(cat_direction,{match})", None, {}),
            "N": (f"=INDEX(cat_tolerance,{match})", "0%", {}),
        }
        for col, (value, number_format, style) in cells.items():
            write(ws, f"{col}{row}", value, number_format, **style)
            ws[f"{col}{row}"].border = Border(bottom=Side(style="hair", color=RULE))
        ws[f"I{row}"].alignment = Alignment(horizontal="center")
    status_formatting(ws, f"J{first}:J{last}", f"I{first}:I{last}", f"$J{first}")

    notes = [
        ("How status works", True),
        ("▲ On plan: at plan or better.  ● Watch: worse than plan, but within the amber band.  "
         "▼ Off plan: worse than plan by more than the amber band.", False),
        ("Better when says which way is good: higher for customers and deposits, lower for cost of funds and PAR30. "
         "The amber band is a share of plan (5% of a 80.0% CASA plan is 4.0 points).", False),
        ("Change on prior month is Flat when the KPI moved by 0.1% of its value or less. "
         "For ratios, the variance to plan is in percentage points.", False),
        ("Status always shows as an icon and a word as well as a colour, so it reads the same in print "
         "and for colour-blind readers.", False),
        ("Source: kpi.kpi_monthly and reference.plan_targets in the warehouse. Every figure on this sheet is a "
         "formula on the KPI data, Plan and KPI catalog sheets.", False),
    ]
    for i, (text, bold) in enumerate(notes):
        write(ws, f"B{last + 3 + i}", text, bold=bold, color=INK if bold else INK_2)
    widths(ws, {"B": 8, "C": 25, "D": 20, "E": 13, "F": 13, "G": 10, "H": 14, "I": 4, "J": 10, "K": 13,
                "L": 13, "M": 11, "N": 10})
    ws.freeze_panes = "A10"
    landscape(ws)
    define(wb, "report_month", "Scorecard", "$D$5")
    define(wb, "scorecard_ids", "Scorecard", f"$B${first}:$B${last}")
    define(wb, "scorecard_kpis", "Scorecard", f"$C${first}:$C${last}")
    return ws


def trend_sheet(wb, months, default_name):
    ws = wb.create_sheet("Trend")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 2
    write(ws, "B2", '=$C$5&" against plan, January 2025 to August 2026"', size=16, bold=True)
    write(ws, "B3", SYNTHETIC, italic=True, color=INK_2)

    write(ws, "B5", "KPI", bold=True)
    write(ws, "C5", default_name, bold=True, color=INPUT)
    ws["C5"].fill = fill(SELECT_FILL)
    pick = DataValidation(type="list", formula1="=scorecard_kpis", allow_blank=False, showErrorMessage=True,
                          errorTitle="Pick a KPI", error="Pick one of the six scorecard KPIs from the list.",
                          promptTitle="KPI", prompt="Pick a scorecard KPI to chart.", showInputMessage=True)
    ws.add_data_validation(pick)
    pick.add("C5")
    write(ws, "D5", "Pick a scorecard KPI from the list in the yellow cell.", italic=True, color=MUTED)
    helpers = [
        ("KPI id", "=INDEX(scorecard_ids,MATCH($C$5,scorecard_kpis,0))", None),
        ("Better when", "=INDEX(cat_direction,MATCH($C$6,cat_id,0))", None),
        ("Unit code", "=INDEX(cat_unit,MATCH($C$6,cat_id,0))", None),
        ("Shown in", '=IF($C$8="rm","RM millions",IF($C$8="pct","percent",IF($C$8="count","customers","units")))',
         None),
        ("Divided by", '=IF($C$8="rm",1000000,IF($C$8="pct",0.01,1))', "General"),
        ("Amber band", "=INDEX(cat_tolerance,MATCH($C$6,cat_id,0))", "0%"),
    ]
    for i, (label, formula, fmt) in enumerate(helpers):
        write(ws, f"B{6 + i}", label, color=INK_2)
        write(ws, f"C{6 + i}", formula, fmt, color=INK_2)

    head = TREND_FIRST_ROW - 1
    header_row(ws, head, 2, ["Month", "Actual", "Plan", "% of plan", "", "Status"])
    write(ws, f"C{head}", '="Actual ("&$C$9&")"', bold=True)
    write(ws, f"D{head}", '="Plan ("&$C$9&")"', bold=True)
    for col in "CD":
        ws[f"{col}{head}"].fill = fill(HEADER_FILL)
        ws[f"{col}{head}"].border = Border(bottom=THIN)
        ws[f"{col}{head}"].alignment = Alignment(vertical="center", wrap_text=True)
    trend_months = [m for m in months if m >= TREND_FROM]
    last = TREND_FIRST_ROW + len(trend_months) - 1
    for row, month in enumerate(trend_months, start=TREND_FIRST_ROW):
        write(ws, f"B{row}", month, "mmm yyyy")
        write(ws, f"C{row}", f'=IF(COUNTIFS(data_kpi,$C$6,data_month,$B{row})=0,"",'
                             f'SUMIFS(data_value,data_kpi,$C$6,data_month,$B{row})/$C$10)', "#,##0.00")
        write(ws, f"D{row}", f'=IF(COUNTIFS(plan_kpi,$C$6,plan_month,$B{row})=0,"",'
                             f'SUMIFS(plan_value,plan_kpi,$C$6,plan_month,$B{row})/$C$10)', "#,##0.00")
        write(ws, f"E{row}", f'=IF(OR(C{row}="",D{row}=""),"",IF(D{row}=0,"",C{row}/D{row}))', "0.0%")
        write(ws, f"F{row}", f'=IF(G{row}="On plan","▲",IF(G{row}="Watch","●",IF(G{row}="Off plan","▼","")))')
        write(ws, f"G{row}", f'=IF(OR(C{row}="",D{row}=""),"No plan",IF($C$7="higher",'
                             f'IF(C{row}>=D{row},"On plan",IF(C{row}>=D{row}*(1-$C$11),"Watch","Off plan")),'
                             f'IF(C{row}<=D{row},"On plan",IF(C{row}<=D{row}*(1+$C$11),"Watch","Off plan"))))',
              bold=True)
        ws[f"F{row}"].alignment = Alignment(horizontal="center")
    # Counts read better without decimals
    count_style = DifferentialStyle(numFmt=NumberFormat(numFmtId=3, formatCode="#,##0"))
    ws.conditional_formatting.add(f"C{TREND_FIRST_ROW}:D{last}",
                                  Rule(type="expression", dxf=count_style, formula=['$C$8="count"']))
    status_formatting(ws, f"G{TREND_FIRST_ROW}:G{last}", f"F{TREND_FIRST_ROW}:F{last}", f"$G{TREND_FIRST_ROW}")

    chart = LineChart()
    chart.height, chart.width = 10, 20
    chart.legend.position = "b"
    chart.add_data(Reference(ws, min_col=3, max_col=4, min_row=head, max_row=last), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, min_row=TREND_FIRST_ROW, max_row=last))
    chart.y_axis.crossAx = 500
    chart.x_axis = DateAxis(crossAx=100)
    chart.x_axis.number_format = "mmm yy"
    chart.x_axis.majorTimeUnit = "months"
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.y_axis.number_format = "General"
    chart.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill=GRID)))
    actual, plan = chart.series
    for series, colour, width, dash in [(actual, LINE_ACTUAL, 28575, None), (plan, LINE_PLAN, 19050, "dash")]:
        series.smooth = False
        series.marker.symbol = "none"
        series.graphicalProperties.line.solidFill = colour
        series.graphicalProperties.line.width = width
        if dash:
            series.graphicalProperties.line.dashStyle = dash
    ws.add_chart(chart, "I5")

    write(ws, f"B{last + 2}", "Every value is a formula on the KPI data and Plan sheets. Status uses the same rules "
                              "as the Scorecard.", color=INK_2)
    widths(ws, {"B": 12, "C": 14, "D": 14, "E": 10, "F": 4, "G": 10, "H": 3})
    landscape(ws)
    return ws


def monthly_sheet(wb, catalog, months, formats):
    ws = wb.create_sheet("Monthly KPIs")
    page_title(ws, "All 22 KPIs by month")
    write(ws, "B4", "A blank means the KPI has no value that month: no financing before January 2025, a 30-day, "
                    "month-3 or maturity window still open, or a marketing invoice still missing. The month picked on "
                    "Scorecard is shaded.", color=INK_2)
    head, first = 6, 7
    last = first + len(catalog) - 1
    first_month_col, last_month_col = 5, 4 + len(months)
    target_col = last_month_col + 1
    header_row(ws, head, 2, ["KPI id", "KPI", "Better when"])
    for j, month in enumerate(months, start=first_month_col):
        cell = ws.cell(row=head, column=j, value=month)
        cell.font = font(bold=True)
        cell.fill = fill(HEADER_FILL)
        cell.border = Border(bottom=THIN)
        cell.number_format = "mmm yyyy"
        cell.alignment = Alignment(horizontal="right")
    header_row(ws, head, target_col, ["Target", "Owner"])
    first_letter, last_letter = get_column_letter(first_month_col), get_column_letter(last_month_col)

    for row, kpi in enumerate(catalog.itertuples(index=False), start=first):
        match = f"MATCH($B{row},cat_id,0)"
        write(ws, f"B{row}", kpi.kpi_id, color=INPUT)
        write(ws, f"C{row}", f"=INDEX(cat_name,{match})")
        write(ws, f"D{row}", f'=IF(INDEX(cat_direction,{match})="higher","Higher","Lower")')
        for j in range(first_month_col, last_month_col + 1):
            col = get_column_letter(j)
            formula = (f'=IF(COUNTIFS(data_kpi,$B{row},data_month,{col}${head})=0,"",'
                       f'SUMIFS(data_value,data_kpi,$B{row},data_month,{col}${head}))')
            write(ws, f"{col}{row}", formula, formats[kpi.kpi_id])
        target = get_column_letter(target_col)
        write(ws, f"{target}{row}", f'=IF(INDEX(cat_target,{match})="","Monthly plan",INDEX(cat_target,{match}))',
              formats[kpi.kpi_id])
        ws[f"{target}{row}"].alignment = Alignment(horizontal="right")
        write(ws, f"{get_column_letter(target_col + 1)}{row}", f"=INDEX(cat_owner,{match})")
    ws.conditional_formatting.add(f"{first_letter}{head}:{last_letter}{last}",
                                  FormulaRule(formula=[f"{first_letter}${head}=report_month"],
                                              fill=fill(MONTH_HIGHLIGHT)))
    widths(ws, {"B": 8, "C": 30, "D": 11})
    for j in range(first_month_col, last_month_col + 1):
        ws.column_dimensions[get_column_letter(j)].width = 10.5
    ws.column_dimensions[get_column_letter(target_col)].width = 13
    ws.column_dimensions[get_column_letter(target_col + 1)].width = 20
    ws.freeze_panes = ws.cell(row=first, column=first_month_col)
    landscape(ws)
    define(wb, "month_list", "Monthly KPIs", f"${first_letter}${head}:${last_letter}${head}")
    return ws


# Control totals: computed in SQL from the fact tables (not the KPI tables), and compared
# with the pack's own formulas on the Checks sheet.
CONTROLS = [
    ("New customers, Sep 2024 to Aug 2026", '=SUMIFS(data_value,data_kpi,"K02")',
     "SELECT count(*) FROM marts.dim_customer",
     0, "#,##0", "Count of customers in marts.dim_customer"),
    ("Monthly active customers, Aug 2026", '=SUMIFS(data_value,data_kpi,"K07",data_month,DATE(2026,8,1))',
     "SELECT count(*) FROM marts.fct_customer_monthly WHERE month_start = DATE '2026-08-01' AND is_active",
     0, "#,##0", "Active customers in marts.fct_customer_monthly for Aug 2026"),
    ("Total deposits at 31 Aug 2026 (RM)", '=SUMIFS(data_value,data_kpi,"K13",data_month,DATE(2026,8,1))',
     "SELECT sum(amount) FROM marts.fct_ledger_postings WHERE posting_date <= DATE '2026-08-31'",
     0.005, '"RM"#,##0.00', "Every deposit posting in the ledger up to 31 Aug 2026 (the KPI uses month-end balances)"),
    ("CASA ratio at 31 Aug 2026", '=SUMIFS(data_value,data_kpi,"K14",data_month,DATE(2026,8,1))',
     "SELECT sum(amount) FILTER (WHERE product_family = 'CASA') / sum(amount) FROM marts.fct_ledger_postings "
     "WHERE posting_date <= DATE '2026-08-31'",
     1e-9, "0.0000%", "Savings share of all deposit postings in the ledger up to 31 Aug 2026"),
    ("Debit card spend, Sep 2024 to Aug 2026 (RM)", '=SUMIFS(data_value,data_kpi,"K11")',
     "SELECT -sum(amount) FROM marts.fct_ledger_postings WHERE txn_type = 'card_purchase'",
     0.005, '"RM"#,##0.00', "Card purchases posted to the ledger"),
    ("Financing disbursed, Jan 2025 to Aug 2026 (RM)", '=SUMIFS(data_value,data_kpi,"K18")',
     "SELECT sum(amount) FROM marts.fct_ledger_postings WHERE txn_type = 'pf_disbursement'",
     0.005, '"RM"#,##0.00', "Disbursements credited to savings in the ledger (the KPI uses the loan system)"),
    ("Net interest income, Sep 2024 to Aug 2026 (RM)", '=SUMIFS(data_value,data_kpi,"K22")',
     "SELECT (SELECT sum(interest_income_accrued) FROM marts.fct_loan_status_monthly) "
     "- (SELECT sum(interest_accrued) FROM marts.fct_account_balances_monthly)",
     0.01, '"RM"#,##0.00', "Loan interest in marts.fct_loan_status_monthly less deposit interest in "
                          "marts.fct_account_balances_monthly"),
    ("Rows on the KPI data sheet", "=COUNT(data_value)", "SELECT count(*) FROM kpi.kpi_monthly",
     0, "#,##0", "Rows in kpi.kpi_monthly"),
    ("Rows on the Plan sheet", "=COUNT(plan_value)", "SELECT count(*) FROM reference.plan_targets",
     0, "#,##0", "Rows in reference.plan_targets"),
]
CHECKS_FIRST_ROW = 8


def control_totals(con):
    return [float(con.execute(sql).fetchone()[0]) for _, _, sql, *_ in CONTROLS]


def checks_sheet(wb, totals):
    ws = wb.create_sheet("Checks")
    page_title(ws, "Checks: the pack's totals against the warehouse")
    write(ws, "B4", "Each figure in column C is a formula on this workbook's data sheets. Column D is a control "
                    "total computed separately in SQL from the fact tables when the pack was built.", color=INK_2)
    first, last = CHECKS_FIRST_ROW, CHECKS_FIRST_ROW + len(CONTROLS) - 1
    result = f"$G${first}:$G${last}"
    write(ws, "B5", f'=IF(COUNTIF({result},"PASS")=ROWS({result}),"All "&ROWS({result})&" checks pass",'
                    f'COUNTIF({result},"FAIL")&" of "&ROWS({result})&" checks fail")', size=12, bold=True)
    header_row(ws, first - 1, 2, ["Check", "In this pack (formula)", "Control total from SQL", "Difference",
                                  "Allowed difference", "Result", "How the control total is computed"])
    for row, (label, formula, _, tolerance, fmt, how), total in zip(range(first, last + 1), CONTROLS, totals):
        write(ws, f"B{row}", label)
        write(ws, f"C{row}", formula, fmt)
        write(ws, f"D{row}", total, fmt, color=INPUT)
        write(ws, f"E{row}", f"=C{row}-D{row}", "0.00E+00")
        write(ws, f"F{row}", tolerance, "0.00E+00" if tolerance else "0", color=INPUT)
        write(ws, f"G{row}", f'=IF(ABS(E{row})<=F{row},"PASS","FAIL")', bold=True)
        write(ws, f"H{row}", how, color=INK_2)
        ws[f"G{row}"].alignment = Alignment(horizontal="center")
        for col in "BCDEFGH":
            ws[f"{col}{row}"].border = Border(bottom=Side(style="hair", color=RULE))
    for label, tint in RESULT_TINT.items():
        ws.conditional_formatting.add(f"G{first}:G{last}",
                                      FormulaRule(formula=[f'$G{first}="{label}"'], fill=fill(tint)))
    write(ws, f"B{last + 2}", "The allowed difference is zero for counts, half a sen for money, and rounding "
                              "error for the ratio.", color=INK_2)
    widths(ws, {"B": 44, "C": 22, "D": 22, "E": 12, "F": 12, "G": 9, "H": 80})
    landscape(ws)
    return ws


# --- the workbook ------------------------------------------------------------------------

def build(con):
    catalog = con.execute("SELECT * FROM reference.kpi_catalog ORDER BY kpi_id").df()
    data = con.execute("""
        SELECT month_start, kpi_id, kpi_name, family, unit, direction, value
        FROM kpi.kpi_monthly ORDER BY kpi_id, month_start
    """).df()
    plan = con.execute("""
        SELECT p.month_start, p.kpi_id, c.kpi_name, p.plan_value, p.note
        FROM reference.plan_targets AS p JOIN reference.kpi_catalog AS c USING (kpi_id)
        ORDER BY p.kpi_id, p.month_start
    """).df()
    months = [m.date() for m in sorted(pd.to_datetime(data["month_start"]).unique())]
    formats = kpi_formats(data)
    scorecard_ids = catalog.loc[catalog["is_scorecard"], "kpi_id"].tolist()
    default_trend = catalog.set_index("kpi_id").loc[DEFAULT_TREND_KPI, "kpi_name"]

    wb = Workbook()
    # Arial as the workbook's default font, so cells a reader types into match the rest
    wb._fonts = IndexedList([Font(name=FONT, size=10)])
    wb._named_styles["Normal"].font = Font(name=FONT, size=10)
    wb.properties.creator = "Kelip Bank BI pipeline"
    wb.properties.title = "Kelip Bank KPI pack (synthetic data)"
    wb.properties.created = wb.properties.modified = BUILT
    wb.calculation.fullCalcOnLoad = True

    cover_sheet(wb)
    scorecard_sheet(wb, scorecard_ids, formats)
    trend_sheet(wb, months, default_trend)
    monthly_sheet(wb, catalog, months, formats)
    checks_sheet(wb, control_totals(con))

    _, data_last = data_sheet(
        wb, "KPI data", data, "kpi.kpi_monthly", [12, 8, 32, 12, 8, 10, 16],
        {"value": lambda row: formats[row.kpi_id]})
    define(wb, "data_month", "KPI data", f"$A$2:$A${data_last}")
    define(wb, "data_kpi", "KPI data", f"$B$2:$B${data_last}")
    define(wb, "data_value", "KPI data", f"$G$2:$G${data_last}")

    _, plan_last = data_sheet(
        wb, "Plan", plan, "reference.plan_targets", [12, 8, 26, 16, 60],
        {"plan_value": lambda row: formats[row.kpi_id]})
    define(wb, "plan_month", "Plan", f"$A$2:$A${plan_last}")
    define(wb, "plan_kpi", "Plan", f"$B$2:$B${plan_last}")
    define(wb, "plan_value", "Plan", f"$D$2:$D${plan_last}")

    cat_cols = ["kpi_id", "kpi_name", "family", "definition", "formula", "owner", "unit", "direction",
                "amber_tolerance", "target", "target_note", "is_scorecard", "source_table", "source_column",
                "dashboard_page"]
    cat_ws, cat_last = data_sheet(
        wb, "KPI catalog", catalog[cat_cols], "reference.kpi_catalog",
        [8, 30, 12, 60, 50, 20, 8, 10, 10, 12, 40, 11, 26, 26, 20],
        {"amber_tolerance": lambda row: "0%",
         "target": lambda row: formats.get(row.kpi_id, "General")})
    for row in cat_ws.iter_rows(min_row=2, max_row=cat_last):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column in (4, 5, 11))
    for name, col in [("cat_id", "A"), ("cat_name", "B"), ("cat_owner", "F"), ("cat_unit", "G"),
                      ("cat_direction", "H"), ("cat_tolerance", "I"), ("cat_target", "J")]:
        define(wb, name, "KPI catalog", f"${col}$2:${col}${cat_last}")

    wb.active = 0
    PACK.parent.mkdir(parents=True, exist_ok=True)
    wb.save(PACK)
    normalise_xlsx(PACK)
    return PACK

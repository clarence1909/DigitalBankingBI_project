"""Check the generated Power BI report before anyone opens it.

Power BI Desktop cannot run in the pipeline, so the project in dashboards/powerbi/ is checked here by reading
its files the way Power BI would.

  1. The model (TMDL). Each table's Power Query is replayed on dashboard_data.csv: the shared read must match
     the CSV's header, each table must keep some rows and produce every column the model loads, with the type
     the model gives it, and every sort-by column must give each value exactly one position. Every measure's
     DAX may refer only to tables, columns and measures in the model, and every value it filters on (such as
     'KPI trend'[KPI ID] = "K02") must be in the data. Measure names are unique and clash with no column.
  2. The report (PBIR). Every file is valid JSON and declares the schema version the generator targets;
     pages.json lists every page folder once; every visual sits inside its page without overlapping another;
     every field a visual plots, sorts or colours by is in the model, as a column or a measure as used, in a
     role that visual type has; every value a visual colours (a series such as Actual or Plan) occurs in the
     data; and page and visual names are unique.

The results go to reports/powerbi_report_check.md, and any problem stops the build. CI also validates the
report against Microsoft's published PBIR schemas with Microsoft's own report CLI
(@microsoft/powerbi-report-authoring-cli). Opening it in Power BI Desktop is still the final test, which
dashboards/powerbi_build_notes.md walks through.
"""

import json
import re
from collections import Counter

import pandas as pd

from src.config import REPORTS_DIR, ROOT
from src.export.dashboard_data import DATA
from src.export.powerbi_report import MODEL, MODEL_TYPE, NAME, PROJECT_DIR, REPORT, SCHEMAS

CHECK_REPORT = REPORTS_DIR / "powerbi_report_check.md"
IDENT = r"(?:'(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_]*)"

# Roles each visual type accepts, and which of them take measures rather than columns
ROLES = {
    "lineChart": ({"Category", "Series", "Y", "Y2", "Rows", "Tooltips"}, {"Y", "Y2", "Tooltips"}, {"Category", "Y"}),
    "clusteredBarChart": ({"Category", "Series", "Y", "Rows", "Tooltips"}, {"Y", "Tooltips"}, {"Category", "Y"}),
    "columnChart": ({"Category", "Series", "Y", "Rows", "Tooltips"}, {"Y", "Tooltips"}, {"Category", "Y"}),
    "stackedAreaChart": ({"Category", "Series", "Y", "Rows", "Tooltips"}, {"Y", "Tooltips"}, {"Category", "Y"}),
    "tableEx": ({"Values"}, set(), {"Values"}),
    "pivotTable": ({"Rows", "Columns", "Values"}, {"Values"}, {"Values"}),
}


def unquote(name: str) -> str:
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def m_strings(text: str) -> list:
    return [s.replace('""', '"') for s in re.findall(r'"((?:[^"]|"")*)"', text)]


def read_files() -> dict:
    """The project's files as {path relative to dashboards/powerbi: text}, leaving out Desktop's .pbi folders."""
    return {p.relative_to(PROJECT_DIR).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(PROJECT_DIR.rglob("*"))
            if p.is_file() and ".pbi" not in p.relative_to(PROJECT_DIR).parts}


# --------------------------------------------------------------------------------------------
# The model
# --------------------------------------------------------------------------------------------

def parse_tmdl_table(text: str) -> dict:
    """The parts of a table file the checks need: name, columns and their properties, measures, query."""
    table = {"name": None, "columns": {}, "measures": {}, "query": None}
    lines = text.split("\n")
    current, i = None, 0
    while i < len(lines):
        line = lines[i]
        if m := re.fullmatch(rf"table ({IDENT})", line):
            table["name"] = unquote(m[1])
        elif m := re.fullmatch(rf"\tmeasure ({IDENT}) = (.+)", line):
            current = {"dax": m[2]}
            table["measures"].setdefault(unquote(m[1]), []).append(current)
        elif m := re.fullmatch(rf"\tcolumn ({IDENT})", line):
            current = {}
            table["columns"].setdefault(unquote(m[1]), []).append(current)
        elif re.fullmatch(rf"\tpartition ({IDENT}) = m", line):
            current = {}
        elif line == "\t\tsource =":
            body = []
            while i + 1 < len(lines) and lines[i + 1].startswith("\t\t\t\t"):
                i += 1
                body.append(lines[i][4:])
            table["query"] = "\n".join(body)
        elif (m := re.fullmatch(r"\t\t(\w+)(?:: (.*))?", line)) and current is not None:
            current[m[1]] = m[2] if m[2] is not None else True
        i += 1
    return table


def parse_expressions(text: str) -> dict:
    expressions, lines, i = {}, text.split("\n"), 0
    while i < len(lines):
        if m := re.fullmatch(rf"expression ({IDENT}) =(?: (.*))?", lines[i]):
            body = [m[2]] if m[2] else []
            while i + 1 < len(lines) and lines[i + 1].startswith("\t\t"):
                i += 1
                body.append(lines[i][2:])
            expressions[unquote(m[1])] = "\n".join(body)
        i += 1
    return expressions


class Replay:
    """Runs the Power Query steps the generator writes on dashboard_data.csv, with pandas."""

    STEP = re.compile(r'\s{4}(#"(?:[^"]|"")+"|[A-Za-z_]\w*) = (.*?),?')

    def __init__(self, data: pd.DataFrame, problems: list):
        self.data, self.problems = data, problems
        self.base_types = {}

    def base(self, query: str) -> None:
        header = list(self.data.columns)
        columns = re.search(r"Columns = (\d+)", query)
        if not columns or int(columns[1]) != len(header):
            self.problems.append(f"The shared read expects {columns[1] if columns else 'an unknown number of'} "
                                 f"columns but dashboard_data.csv has {len(header)}")
        read = re.search(r'File\.Contents\(Text\.TrimEnd\(DataFolder, \{"\\", "/"\}\) & "\\([^"]+)"\)', query)
        if not read or read[1] != DATA.name:
            self.problems.append(f"The shared read does not read {DATA.name}")
        typed = dict(re.findall(r'\{"([^"]+)", (type \w+|Int64\.Type)\}', query))
        if list(typed) != header:
            self.problems.append(f"The shared read types columns {list(typed)}, but the CSV header is {header}")
        self.base_types = typed

    def table(self, name: str, query: str):
        """The table a query produces, with each column's Power Query type; None if it cannot be read."""
        lines = query.split("\n")
        if len(lines) < 4 or lines[0] != "let" or lines[-2] != "in":
            self.problems.append(f"Table {name}: its Power Query is not a let ... in expression")
            return None, {}
        frame, types, previous = None, {}, None
        for line in lines[1:-2]:
            step = self.STEP.fullmatch(line)
            if not step:
                self.problems.append(f"Table {name}: cannot read the Power Query step `{line.strip()}`")
                return None, {}
            label, expr = step[1], step[2]
            source = re.match(r'Table\.\w+\((#"(?:[^"]|"")+"|\w+), ', expr)
            if previous and (not source or source[1] != previous):
                self.problems.append(f"Table {name}: step {label} does not build on the step before it")
                return None, {}
            if expr == '#"Dashboard data"':
                frame, types = self.data.copy(), dict(self.base_types)
            elif m := re.fullmatch(r'Table\.SelectRows\(.+?, each \[chart\] = "(.+)"\)', expr):
                frame = frame[frame["chart"] == m[1]]
            elif m := re.fullmatch(r'Table\.SelectRows\(.+?, each Text\.StartsWith\(\[chart\], "(.+)"\)\)', expr):
                frame = frame[frame["chart"].str.startswith(m[1])]
            elif m := re.fullmatch(r'Table\.AddColumn\(.+?, "(.+?)", each Text\.AfterDelimiter\(\[(.+?)\], '
                                   r'"(.+?)"\), (type text)\)', expr):
                frame = frame.assign(**{m[1]: frame[m[2]].str.split(m[3], n=1).str[1]})
                types[m[1]] = m[4]
            elif m := re.fullmatch(r"Table\.SelectColumns\(.+?, \{(.*)\}\)", expr):
                keep = m_strings(m[1])
                missing = [c for c in keep if c not in frame.columns]
                if missing:
                    self.problems.append(f"Table {name}: its Power Query keeps columns that do not exist: {missing}")
                    return None, {}
                frame, types = frame[keep], {c: types[c] for c in keep}
            elif m := re.fullmatch(r"Table\.RenameColumns\(.+?, \{(.*)\}\)", expr):
                pairs = re.findall(r'\{"((?:[^"]|"")*)", "((?:[^"]|"")*)"\}', m[1])
                missing = [a for a, _ in pairs if a not in frame.columns]
                if missing:
                    self.problems.append(f"Table {name}: its Power Query renames columns that do not exist: {missing}")
                    return None, {}
                frame = frame.rename(columns=dict(pairs))
                types = {dict(pairs).get(c, c): t for c, t in types.items()}
            elif m := re.fullmatch(r'Table\.AddColumn\(.+?, "(.+?)", each List\.PositionOf\(\{(.*)\}, \[(.+?)\]\) '
                                   r"\+ 1, Int64\.Type\)", expr):
                order, column = m_strings(m[2]), m[3]
                if column not in frame.columns:
                    self.problems.append(f"Table {name}: column {m[1]} orders {column}, which it does not have")
                    return None, {}
                unlisted = sorted(set(frame[column].dropna()) - set(order))
                if unlisted:
                    self.problems.append(f"Table {name}: {m[1]} gives no position to {unlisted}")
                frame = frame.assign(**{m[1]: [order.index(v) + 1 if v in order else 0 for v in frame[column]]})
                types[m[1]] = "Int64.Type"
            else:
                self.problems.append(f"Table {name}: cannot read the Power Query step `{line.strip()}`")
                return None, {}
            previous = label
        if lines[-1].strip() != previous:
            self.problems.append(f"Table {name}: its Power Query does not return its last step")
        return frame, types


def check_model(files: dict, data: pd.DataFrame):
    problems, stats = [], {"tables": [], "dax_refs": 0, "dax_values": 0, "sorts": 0}
    root = f"{MODEL}/definition/"
    model_text = files.get(root + "model.tmdl", "")
    refs = [unquote(m) for m in re.findall(rf"^ref table ({IDENT})$", model_text, flags=re.M)]
    table_files = {rel: text for rel, text in files.items() if rel.startswith(root + "tables/")}
    expressions = parse_expressions(files.get(root + "expressions.tmdl", ""))

    replay = Replay(data, problems)
    if "Dashboard data" not in expressions:
        problems.append("The model has no 'Dashboard data' query reading dashboard_data.csv")
    else:
        replay.base(expressions["Dashboard data"])
    folder = re.fullmatch(r'"((?:[^"]|"")+)" meta \[IsParameterQuery = true.*\]', expressions.get("DataFolder", ""))
    if not folder:
        problems.append("The model has no DataFolder parameter with a folder in it")

    model = {}
    for rel, text in sorted(table_files.items()):
        t = parse_tmdl_table(text)
        if t["name"] is None:
            problems.append(f"{rel} declares no table")
            continue
        if t["name"] in model:
            problems.append(f"Table {t['name']} is declared twice")
        frame, types = replay.table(t["name"], t["query"] or "") if t["query"] else (None, {})
        if not t["query"]:
            problems.append(f"Table {t['name']} has no Power Query")
        elif frame is not None and frame.empty:
            problems.append(f"Table {t['name']}: its Power Query keeps no rows of dashboard_data.csv")
        model[t["name"]] = {**t, "frame": frame, "types": types}
    missing_refs = sorted(set(model) - set(refs))
    if missing_refs or sorted(set(refs) - set(model)):
        problems.append(f"model.tmdl lists tables {refs}, but the table files declare {sorted(model)}")

    measure_names = Counter()
    for name, t in model.items():
        for column, entries in t["columns"].items():
            if len(entries) > 1:
                problems.append(f"Table {name}: column {column} is declared twice")
        for measure, entries in t["measures"].items():
            measure_names[measure] += len(entries)
            if measure in t["columns"]:
                problems.append(f"Table {name}: measure {measure} has the same name as a column")
    problems += [f"Measure {m} is declared {n} times" for m, n in measure_names.items() if n > 1]
    all_measures = {m for t in model.values() for m in t["measures"]}

    for name, t in model.items():
        frame, types = t["frame"], t["types"]
        for column, (props,) in ((c, e[:1]) for c, e in t["columns"].items()):
            source = props.get("sourceColumn")
            if frame is not None and source not in frame.columns:
                problems.append(f"Table {name}: column {column} loads {source}, which its Power Query does not make")
            elif frame is not None and MODEL_TYPE.get(types.get(source)) != props.get("dataType"):
                problems.append(f"Table {name}: column {column} is {props.get('dataType')} in the model but "
                                f"{types.get(source)} in Power Query")
            if "sortByColumn" in props:
                stats["sorts"] += 1
                by = unquote(props["sortByColumn"])
                if by not in t["columns"] or by == column:
                    problems.append(f"Table {name}: column {column} is sorted by {by}, which is not another column "
                                    "of the table")
                elif frame is not None:
                    by_source = t["columns"][by][0].get("sourceColumn")
                    if source in frame.columns and by_source in frame.columns:
                        spread = frame.groupby(source)[by_source].nunique()
                        if (spread > 1).any():
                            problems.append(f"Table {name}: {column} values {list(spread[spread > 1].index)} have "
                                            f"more than one {by}, so Power BI cannot sort by it")
        for measure, entries in t["measures"].items():
            dax = entries[0]["dax"]
            spans = []
            for m in re.finditer(rf"({IDENT})\[([^\]]+)\]", dax):
                spans.append(m.span())
                stats["dax_refs"] += 1
                table, column = unquote(m[1]), m[2]
                if table not in model:
                    problems.append(f"Measure {measure} refers to table {table}, which is not in the model")
                elif column not in model[table]["columns"] and column not in model[table]["measures"]:
                    problems.append(f"Measure {measure} refers to {table}[{column}], which is not in the model")
            for m in re.finditer(r"\[([^\]]+)\]", dax):
                if not any(a <= m.start() < b for a, b in spans):
                    stats["dax_refs"] += 1
                    if m[1] not in all_measures:
                        problems.append(f"Measure {measure} refers to measure [{m[1]}], which is not in the model")
            for m in re.finditer(rf'({IDENT})\[([^\]]+)\] = "((?:[^"]|"")*)"', dax):
                stats["dax_values"] += 1
                table, column, value = unquote(m[1]), m[2], m[3].replace('""', '"')
                target = model.get(table)
                if target and target["frame"] is not None and column in target["columns"]:
                    source = target["columns"][column][0].get("sourceColumn")
                    if source in target["frame"].columns and value not in set(target["frame"][source].dropna()):
                        problems.append(f'Measure {measure} filters {table}[{column}] on "{value}", which is not '
                                        "in the data")
        stats["tables"].append((name, 0 if frame is None else len(frame), len(t["columns"]), len(t["measures"])))

    # Power BI links tables on first load when columns share a name and one side has unique values; the
    # tables here are meant to stay unrelated, so no shared column name may hold unique values anywhere
    owners = {}
    for name, t in model.items():
        for column in t["columns"]:
            owners.setdefault(column, []).append(name)
    for column, names in sorted(owners.items()):
        if len(names) < 2:
            continue
        for name in names:
            frame = model[name]["frame"]
            source = model[name]["columns"][column][0].get("sourceColumn")
            if frame is not None and source in frame.columns and frame[source].is_unique:
                problems.append(f"Column {column} is in tables {names} and unique in {name}, so Power BI "
                                "would link the tables automatically")
    return model, problems, stats


# --------------------------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------------------------

def walk(node, found: list, kind: str):
    """Every field reference (kind "field") or selector reference (kind "selector") in a visual."""
    if isinstance(node, dict):
        if kind == "field":
            for key in ("Column", "Measure"):
                value = node.get(key)
                if isinstance(value, dict) and "Property" in value:
                    found.append((key, value.get("Expression", {}).get("SourceRef", {}).get("Entity"),
                                  value["Property"]))
        if kind == "selector":
            if isinstance(node.get("metadata"), str):
                found.append(node["metadata"])
            if isinstance(node.get("ExpressionName"), str):
                found.append(node["ExpressionName"])
        if kind == "comparison" and "Comparison" in node:
            found.append(node["Comparison"])
        for value in node.values():
            walk(value, found, kind)
    elif isinstance(node, list):
        for value in node:
            walk(value, found, kind)


def expected_schema(rel: str):
    name = rel.rsplit("/", 1)[-1]
    return {"visual.json": SCHEMAS["visual"], "page.json": SCHEMAS["page"], "pages.json": SCHEMAS["pages"],
            "report.json": SCHEMAS["report"], "version.json": SCHEMAS["version"], "definition.pbir": SCHEMAS["pbir"],
            "definition.pbism": SCHEMAS["pbism"], ".platform": SCHEMAS["platform"],
            f"{NAME}.pbip": SCHEMAS["pbip"]}.get(name)


def overlaps(a, b) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def check_report(files: dict, model: dict):
    problems = []
    stats = {"pages": [], "visuals": 0, "fields": 0, "colours": 0, "json": 0}
    parsed = {}
    for rel, text in files.items():
        if not rel.endswith((".json", ".pbir", ".pbism", ".platform", ".pbip")):
            continue
        try:
            parsed[rel] = json.loads(text)
        except json.JSONDecodeError as exc:
            problems.append(f"{rel} is not valid JSON: {exc}")
            continue
        stats["json"] += 1
        expected = expected_schema(rel)
        if expected and parsed[rel].get("$schema") != expected:
            problems.append(f"{rel} declares schema {parsed[rel].get('$schema')}, not {expected}")

    pbip = parsed.get(f"{NAME}.pbip", {})
    if [a.get("report", {}).get("path") for a in pbip.get("artifacts", [])] != [REPORT]:
        problems.append(f"{NAME}.pbip does not open {REPORT}")
    binding = parsed.get(f"{REPORT}/definition.pbir", {}).get("datasetReference", {}).get("byPath", {})
    if binding.get("path") != f"../{MODEL}":
        problems.append(f"The report is not bound to ../{MODEL}")

    pages_dir = f"{REPORT}/definition/pages/"
    folders = sorted({rel[len(pages_dir):].split("/")[0] for rel in files
                      if rel.startswith(pages_dir) and rel.count("/") > pages_dir.count("/")})
    order = parsed.get(pages_dir + "pages.json", {}).get("pageOrder", [])
    if sorted(order) != folders or len(set(order)) != len(order):
        problems.append(f"pages.json lists pages {order}, but the page folders are {folders}")
    if parsed.get(pages_dir + "pages.json", {}).get("activePageName") not in order:
        problems.append("pages.json opens on a page it does not list")

    visual_names = Counter()
    for page_id in order:
        page = parsed.get(f"{pages_dir}{page_id}/page.json")
        if page is None:
            problems.append(f"Page {page_id} has no page.json")
            continue
        if page.get("name") != page_id:
            problems.append(f"Page folder {page_id} holds page {page.get('name')}")
        width, height = page.get("width", 0), page.get("height", 0)
        boxes, charts, texts = {}, 0, 0
        prefix = f"{pages_dir}{page_id}/visuals/"
        for rel in sorted(r for r in parsed if r.startswith(prefix) and r.endswith("/visual.json")):
            visual = parsed[rel]
            folder = rel[len(prefix):].split("/")[0]
            name = visual.get("name")
            visual_names[name] += 1
            where = f"{page.get('displayName')}: visual {name}"
            if name != folder:
                problems.append(f"{where} is in folder {folder}")
            p = visual.get("position", {})
            box = (p.get("x", -1), p.get("y", -1), p.get("width", 0), p.get("height", 0))
            if box[0] < 0 or box[1] < 0 or box[0] + box[2] > width or box[1] + box[3] > height or min(box[2:]) <= 0:
                problems.append(f"{where} at {box} is not inside the {width} x {height} page")
            for other, other_box in boxes.items():
                if overlaps(box, other_box):
                    problems.append(f"{where} overlaps visual {other}")
            boxes[name] = box
            body = visual.get("visual", {})
            kind = body.get("visualType")
            if kind == "textbox":
                texts += 1
                paragraphs = body.get("objects", {}).get("general", [{}])[0].get("properties", {}).get("paragraphs")
                if not isinstance(paragraphs, list) or not all(p.get("textRuns") for p in paragraphs):
                    problems.append(f"{where}: its text is not a list of paragraphs with text runs")
                continue
            charts += 1
            if kind not in ROLES:
                problems.append(f"{where} is a {kind}, which the check does not know")
                continue
            allowed, measure_roles, required = ROLES[kind]
            state = body.get("query", {}).get("queryState", {})
            refs = set()
            for role, projections in state.items():
                if role not in allowed:
                    problems.append(f"{where}: a {kind} has no {role} role")
                for projection in projections.get("projections", []):
                    field = projection.get("field", {})
                    used = "Measure" if "Measure" in field else "Column"
                    wanted = "Measure" if role in measure_roles else "Column"
                    if kind != "tableEx" and used != wanted:
                        problems.append(f"{where}: role {role} takes a {wanted.lower()}, not {projection['queryRef']}")
                    refs.add(projection.get("queryRef"))
            for role in required - set(state):
                problems.append(f"{where}: a {kind} needs the {role} role")
            found = []
            walk(body, found, "field")
            for used, table, prop in found:
                stats["fields"] += 1
                target = model.get(table)
                has = target and (prop in target["measures"] if used == "Measure" else prop in target["columns"])
                if not has:
                    problems.append(f"{where} uses {used.lower()} {table}.{prop}, which is not in the model")
            selectors = []
            walk(body, selectors, "selector")
            for ref in selectors:
                if ref not in refs:
                    problems.append(f"{where} formats {ref}, which the visual does not show")
            comparisons = []
            walk(body, comparisons, "comparison")
            for comparison in comparisons:
                stats["colours"] += 1
                left = comparison.get("Left", {}).get("Column", {})
                table = left.get("Expression", {}).get("SourceRef", {}).get("Entity")
                column = left.get("Property")
                value = comparison.get("Right", {}).get("Literal", {}).get("Value", "")
                value = value[1:-1].replace("''", "'") if value.startswith("'") else value
                target = model.get(table)
                if target and target["frame"] is not None and column in target["columns"]:
                    source = target["columns"][column][0].get("sourceColumn")
                    if source in target["frame"].columns and value not in set(target["frame"][source].dropna()):
                        problems.append(f"{where} colours {table}[{column}] = '{value}', which is not in the data")
        for interaction in page.get("visualInteractions", []):
            if interaction.get("source") not in boxes or interaction.get("target") not in boxes:
                problems.append(f"{page.get('displayName')}: an interaction names a visual not on the page")
        stats["visuals"] += len(boxes)
        stats["pages"].append((page.get("displayName"), charts, texts))
    problems += [f"Visual name {n} is used {k} times" for n, k in visual_names.items() if k > 1]
    return problems, stats


def check(files: dict, data: pd.DataFrame):
    model, model_problems, model_stats = check_model(files, data)
    report_problems, report_stats = check_report(files, model)
    return model_problems + report_problems, model_stats, report_stats


def problems(files: dict, data: pd.DataFrame) -> list:
    """Every problem in a copy of the project's files; the break-tests use it on broken copies."""
    return check(files, data)[0]


def write_report(found, model_stats, report_stats, data_dir):
    tables = model_stats["tables"]
    lines = [
        "# Power BI report check",
        "",
        f"Generated by `src/export/powerbi_check.py`. The report ([`dashboards/powerbi/{NAME}.pbip`]"
        f"(../dashboards/powerbi/{NAME}.pbip)) is written by `src/export/powerbi_report.py` and checked here "
        "against its own model and its data, [`dashboard_data.csv`](../dashboards/extracts/dashboard_data.csv), "
        "with each table's Power Query replayed on the CSV. CI also validates it against Microsoft's published "
        "report schemas with Microsoft's report CLI. All data is synthetic.",
        "",
        "| Test | Result |",
        "|---|---|",
        f"| Pages | {len(report_stats['pages'])}: {', '.join(p for p, _, _ in report_stats['pages'])} |",
        f"| Visuals inside their page, without overlaps | {report_stats['visuals']} |",
        f"| JSON files valid, with the expected schema version | {report_stats['json']} |",
        f"| Field references in the visuals found in the model | {report_stats['fields']} |",
        f"| Series colours whose value is in the data | {report_stats['colours']} |",
        f"| Model tables whose Power Query keeps rows of the CSV | "
        f"{sum(1 for _, rows, _, _ in tables if rows)} of {len(tables)} |",
        f"| Measure references (DAX) found in the model | {model_stats['dax_refs']} |",
        f"| Values measures filter on that are in the data | {model_stats['dax_values']} |",
        f"| Sort-by columns giving each value one position | {model_stats['sorts']} |",
        f"| Problems | {len(found)} |",
        "",
        f"The model reads `{data_dir.rstrip(chr(92) + '/')}\\dashboard_data.csv`, the DataFolder parameter. On "
        "another machine, change the parameter in Power BI Desktop (Transform data > Edit parameters) and "
        "refresh; the [build notes](../dashboards/powerbi_build_notes.md) have the steps.",
        "",
        "## Pages",
        "",
        "| Page | Charts and tables | Text boxes |",
        "|---|---:|---:|",
        *[f"| {page} | {charts} | {texts} |" for page, charts, texts in report_stats["pages"]],
        "",
        "## Model tables",
        "",
        "| Table | Rows | Columns | Measures |",
        "|---|---:|---:|---:|",
        *[f"| {name} | {rows:,} | {columns} | {measures} |" for name, rows, columns, measures in tables],
    ]
    if found:
        lines += ["", "## Problems", ""] + [f"- {p}" for p in found[:50]]
    CHECK_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run():
    data = pd.read_csv(DATA, dtype={"month": str})
    files = read_files()
    found, model_stats, report_stats = check(files, data)
    folder = re.search(r'expression DataFolder = "((?:[^"]|"")*)"',
                       files.get(f"{MODEL}/definition/expressions.tmdl", ""))
    write_report(found, model_stats, report_stats, folder[1] if folder else "?")
    if found:
        for p in found[:20]:
            print(f"      {p}")
        raise SystemExit(f"The Power BI report failed its check: {len(found)} problem(s); see "
                         f"{CHECK_REPORT.relative_to(ROOT).as_posix()}")
    print(f"      Power BI report: {report_stats['visuals']} visuals on {len(report_stats['pages'])} pages; all "
          f"{report_stats['fields']} field references and {len(model_stats['tables'])} Power Query tables check out")
    return {"pages": [p for p, _, _ in report_stats["pages"]], "visuals": report_stats["visuals"],
            "fields": report_stats["fields"], "tables": len(model_stats["tables"])}

# Power BI base theme

`CY26SU10.json` is a Power BI base theme: the default colours, fonts and visual styles that a Power BI report builds on. Power BI keeps a copy of its base theme inside every report, so the generated report has one too, at `dashboards/powerbi/KelipBank.Report/StaticResources/SharedResources/BaseThemes/CY26SU10.json`.

It is copied unchanged from Microsoft's Power BI report authoring CLI, [`@microsoft/powerbi-report-authoring-cli`](https://www.npmjs.com/package/@microsoft/powerbi-report-authoring-cli) version 0.4.0 (source: [microsoft/skills-for-fabric](https://github.com/microsoft/skills-for-fabric)), which writes it into the reports it creates. It is © Microsoft Corporation and licensed under the MIT License, in [`LICENSE.txt`](LICENSE.txt).

[`src/export/powerbi_report.py`](../../src/export/powerbi_report.py) copies it into the report on every build. The report sets its own colours on each chart, so the theme mainly supplies fonts and defaults.

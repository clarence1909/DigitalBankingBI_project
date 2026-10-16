"""Kelip Bank BI project: shared code for the pipeline stages."""

import os

# openpyxl writes its XML with lxml when lxml happens to be installed, and with Python's own
# XML library otherwise, and the two space the XML differently. Always using Python's own
# keeps the Excel files byte-identical on every machine. It must be set before openpyxl is
# first imported, which is why it lives here, in the package every stage imports first.
os.environ["OPENPYXL_LXML"] = "False"

"""Small helpers shared by several stages."""

import io
import re
import zipfile
from pathlib import Path

FIXED_ZIP_TIME = (2026, 9, 1, 0, 0, 0)
FIXED_STAMP = "2026-09-01T00:00:00Z"


def normalise_xlsx(path: Path) -> None:
    """Make an .xlsx byte-identical between runs.

    An .xlsx file is a zip archive, and both the zip entries and the document
    properties carry the time the file was saved. Fixing them means a rerun
    with the same data produces the same file, so Git only shows real changes.
    """
    path = Path(path)
    with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as zin:
        entries = [(info, zin.read(info.filename)) for info in zin.infolist()]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            if info.filename == "docProps/core.xml":
                text = data.decode("utf-8")
                text = re.sub(r"(<dcterms:(created|modified)[^>]*>)[^<]*(</dcterms:\2>)",
                              lambda m: m.group(1) + FIXED_STAMP + m.group(3), text)
                data = text.encode("utf-8")
            zi = zipfile.ZipInfo(info.filename, date_time=FIXED_ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            zout.writestr(zi, data)
    path.write_bytes(out.getvalue())

"""Minimal .xlsx writer (no openpyxl available): write({sheet_name: DataFrame}, path). Strings as inline strings,
numbers as numbers, first row bold-free headers. Enough for a research workbook that opens in Excel / Google Sheets."""
import zipfile, math
from xml.sax.saxutils import escape


def _col(i):
    s = ""
    i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def _cell(ref, v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))): return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool): return f'<c r="{ref}"><v>{v}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'


def write(sheets, path):
    z = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED); names = list(sheets)
    z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
               '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
               + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(names)))
               + "</Types>")
    z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
               'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
               + "".join(f'<sheet name="{escape(n[:31])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(names)) + "</sheets></workbook>")
    z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(names)))
               + "</Relationships>")
    for i, n in enumerate(names):
        df = sheets[n]; rows = [list(df.columns)] + df.astype(object).values.tolist(); out = []
        for r, row in enumerate(rows):
            out.append(f'<row r="{r + 1}">' + "".join(_cell(f"{_col(c)}{r + 1}", v) for c, v in enumerate(row)) + "</row>")
        z.writestr(f"xl/worksheets/sheet{i + 1}.xml", '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                   + "".join(out) + "</sheetData></worksheet>")
    z.close()

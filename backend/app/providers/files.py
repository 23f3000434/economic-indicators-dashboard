"""Bounded readers for official publication formats, without evaluating embedded content."""

from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pypdf import PdfReader

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def pdf_pages(body, limit=40, layout=False):
    if not body.startswith(b"%PDF-"):
        raise ValueError("Expected official PDF, not an error page")
    reader = PdfReader(BytesIO(body))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= limit:
        raise ValueError("PDF page budget exceeded")
    return [p.extract_text(extraction_mode="layout" if layout else "plain") for p in reader.pages]


def workbook(body):
    """Read cached source cell text exactly, including decimal XML values. Never run formulas/macros."""
    with ZipFile(BytesIO(body)) as archive:
        if len(archive.infolist()) > 1000 or sum(m.file_size for m in archive.infolist()) > 32 * 1024 * 1024:
            raise ValueError("Workbook expansion budget exceeded")

        def xml(name):
            raw = archive.read(name)
            if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
                raise ValueError("Unexpected XML declaration")
            return ET.fromstring(raw)

        book = xml("xl/workbook.xml")
        prop = book.find("s:workbookPr", NS)
        if prop is not None and prop.get("date1904") in {"1", "true"}:
            raise ValueError("Unexpected Excel date epoch")
        strings = [
            "".join(t.text or "" for t in item.findall(".//s:t", NS)) for item in xml("xl/sharedStrings.xml")
        ]
        rels = {
            r.get("Id"): r.get("Target")
            for r in xml("xl/_rels/workbook.xml.rels")
            if r.get("TargetMode") != "External"
        }
        result = []
        for sheet in book.findall("s:sheets/s:sheet", NS):
            target = rels[sheet.get(RID)]
            if not target.startswith("worksheets/sheet") or ".." in target or not target.endswith(".xml"):
                raise ValueError("Unexpected workbook relationship")
            rows = []
            for row in xml("xl/" + target).findall(".//s:sheetData/s:row", NS):
                cells = {}
                for cell in row:
                    value = cell.find("s:v", NS)
                    text = value.text if value is not None else ""
                    if cell.get("t") == "s":
                        text = strings[int(text)]
                    elif cell.get("t") == "inlineStr":
                        text = "".join(t.text or "" for t in cell.findall(".//s:t", NS))
                    elif cell.get("t") not in {None, "n"}:
                        raise ValueError("Unexpected source cell type")
                    cells[cell.get("r")] = text
                rows.append(cells)
            result.append((sheet.get("name"), rows))
        return result

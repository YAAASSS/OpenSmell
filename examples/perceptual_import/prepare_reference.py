"""Prepare three explicit records from the pinned published Keller/Vosshall XLSX.

Standard library only. No fetching, formula evaluation, joins or device access.
This is a narrow reproducible preparation example, not a general Excel importer.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

XLSX_SHA256 = "efcb1b07558431c869c5578abcd3fa1e4405a38cc68a8b1c1621594c673d9f62"
SOURCE_URL = "https://static-content.springer.com/esm/art%3A10.1186%2Fs12868-016-0287-2/MediaObjects/12868_2016_287_MOESM1_ESM.xlsx"
ARTICLE_URL = "https://link.springer.com/article/10.1186/s12868-016-0287-2"
SOURCE_INDEXES = [2500, 2501, 0]  # zero-based observations; worksheet row = index+4
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
COLUMNS = ["C", "D", "E", "F", "M", "N", *[chr(x) for x in range(ord("P"), ord("Z") + 1)],
           *["A" + chr(x) for x in range(ord("A"), ord("L") + 1)]]
# The workbook's second header calls R familiarity 1..100, while the article
# describes sliders 0..100. Do not resolve that discrepancy by silent rescaling.
COLUMNS.remove("R")


def prepare_reference(raw):
    """Return prepared CSV bytes and declaration for this exact source only."""
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != XLSX_SHA256:
        raise ValueError("XLSX does not match the documented pinned source; no output prepared")
    selected = {}
    with ZipFile(io.BytesIO(raw)) as archive:
        strings = ["".join(t.text or "" for t in item.findall(".//s:t", NS))
                   for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", NS)]
        wanted = {3, *[i + 4 for i in SOURCE_INDEXES]}
        with archive.open("xl/worksheets/sheet1.xml") as sheet:
            for _, element in ET.iterparse(sheet, events=["end"]):
                if element.tag != "{" + NS["s"] + "}row":
                    continue
                number = int(element.attrib["r"])
                if number in wanted:
                    cells = {}
                    for cell in element.findall("s:c", NS):
                        column = cell.attrib["r"].rstrip("0123456789")
                        if column not in COLUMNS:
                            continue
                        if cell.find("s:f", NS) is not None:
                            raise ValueError("Selected source cell contains a formula; no evaluation allowed")
                        value = cell.find("s:v", NS)
                        cells[column] = "" if value is None or value.text is None else (
                            strings[int(value.text)] if cell.get("t") == "s" else value.text)
                    selected[number] = [cells.get(column, "") for column in COLUMNS]
                element.clear()
                if number >= max(wanted):
                    break
    if set(selected) != wanted:
        raise ValueError("Pinned worksheet selection was incomplete")
    headers = [h.strip() for h in selected[3]]
    if not all(headers) or len(set(headers)) != len(headers):
        raise ValueError("Prepared headers are ambiguous")
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(selected[i + 4] for i in SOURCE_INDEXES)
    prepared = output.getvalue().encode("utf-8")
    manifest = {
        "name": "Keller and Vosshall 2016 — selected published psychophysical records",
        "url": SOURCE_URL, "kind": "dataset", "license": "CC0-1.0 (data; publisher notice)",
        "license_context": {"notice_url": ARTICLE_URL, "data_license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                            "article_license": "CC-BY-4.0", "scope": "Publisher data waiver applies unless otherwise stated; no contrary notice observed in the selected worksheet headers."},
        "attribution": "Andreas Keller and Leslie B. Vosshall, Olfactory perception of chemically diverse molecules, BMC Neuroscience 17, 55 (2016), doi:10.1186/s12868-016-0287-2",
        "preparation": "Pinned XLSX data sheet; header at worksheet row 3. Select explicit zero-based observations 2500,2501,0 in that order. Keep source columns C,D,E,F,M,N,P,Q,S:AL; strip header padding only; numeric XML text retained; absent/empty cells emitted blank, never zero. No demographic columns, averaging, chemical lookup or detection inference. CSV UTF-8 with LF records.",
        "scale_limitation": "Column R familiarity omitted: worksheet row 2 labels it 1..100 whereas article methods describe sliders 0..100. This preparation does not resolve that discrepancy or convert units.",
        "rating_scale": {"min": 0, "max": 100, "unit": "rating"},
        "original": {"url": SOURCE_URL, "sha256": XLSX_SHA256, "byte_count": len(raw), "sheet": "data",
                     "header_worksheet_row": 3, "selected_source_columns": COLUMNS},
        "selected_observations": [{"prepared_data_record": i + 1, "source_zero_based_index": index,
                                   "source_worksheet_row": index + 4} for i, index in enumerate(SOURCE_INDEXES)],
        "prepared_csv": {"sha256": hashlib.sha256(prepared).hexdigest(), "byte_count": len(prepared)},
    }
    return prepared, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path, help="Locally downloaded exact publisher supplement")
    parser.add_argument("--output-directory", type=Path, required=True, help="New passive preparation directory")
    args = parser.parse_args()
    try:
        with args.xlsx.open("rb") as source:
            raw = source.read(20 * 1048576 + 1)
        prepared, manifest = prepare_reference(raw)
        args.output_directory.mkdir(parents=True, exist_ok=False)
        (args.output_directory / "observations.csv").write_bytes(prepared)
        (args.output_directory / "source.json").write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps({"status": "prepared", "csv": manifest["prepared_csv"], "selected": manifest["selected_observations"]}))


if __name__ == "__main__":
    main()

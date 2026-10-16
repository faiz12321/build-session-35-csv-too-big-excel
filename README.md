# Split a large CSV by parsed records

Python 3 standard library only. A record can span physical lines. This tool reads UTF-8 comma-separated CSV with a nonblank unique header and consistent field counts. It streams parsed records, not physical lines.

## Practice

Save make_sample.py, bigcsv.py and test_bigcsv.py in a new empty lesson folder.

    python make_sample.py
    python bigcsv.py sample/sales.csv
    python bigcsv.py sample/sales.csv --split 500000 sample/sales-parts
    python -m unittest -v

Setup creates 1,100,003 fictional records plus a header, about 37 MB. Splitting uses additional disk space. Setup and output paths must be new. Existing files, folders and links are refused, never reset. Each part file is exclusively created. A failed split may leave incomplete output. Keep the original and do not use unverified parts.

## What is checked

Excel permits 1,048,576 worksheet rows. One header leaves 1,048,575 data records. This is only a row-capacity check, not full Excel compatibility. No Excel application was recorded. Column limits, cell sizes, formulas, number conversion and import settings are not checked.

Split output is re-serialized UTF-8 CSV with CRLF record endings. BOM, quoting and line endings can change. Verification compares ordered parsed field values and counts against a SHA-256 digest of the first source scan, including the header comparison. It does not promise byte identity. Do not modify source or output during a run. Source paths can follow links. One huge record can use substantial memory or exceed Python's CSV field limit. Empty files and blank records are rejected. Header-only input creates an empty output folder with no parts.

26 temporary-fixture tests cover multiline fields, embedded CR, quotes, commas, exact parsed order, malformed input, limits, collisions and preservation of source bytes/mtime. They are limited checks, not proof for all filesystems or concurrent changes. Reports expose paths and errors may reveal data. Use fictional input and keep private output private.

## Sources and license

- https://support.microsoft.com/en-us/excel/excel-specifications-and-limits
- https://docs.python.org/3/library/csv.html

Code is MIT licensed; see LICENSE. Python and Excel are separate products with their own terms and are not included. No warranty.

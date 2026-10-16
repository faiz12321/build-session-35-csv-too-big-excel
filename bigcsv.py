"""Count UTF-8 comma-separated CSV records, optionally split into a new folder.

A record can span physical lines. Output is re-serialized CSV, not byte-identical.
This does not run Excel or check formulas, type conversion or import settings.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

EXCEL_GRID = 1_048_576
MAX_DATA = EXCEL_GRID - 1  # One worksheet row is used by the header.


def read_records(path):
    with Path(path).open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, None)
        if not header or any(not cell.strip() for cell in header):
            raise ValueError('missing or blank header')
        if len(set(header)) != len(header):
            raise ValueError('duplicate header')
        yield header
        for number, row in enumerate(reader, 1):
            if len(row) != len(header):
                raise ValueError('record %d has %d fields; expected %d'
                                 % (number, len(row), len(header)))
            yield row


def add_digest(digest, row):
    digest.update((json.dumps(row, ensure_ascii=True, separators=(',', ':'))+'\n').encode())


def scan(path):
    records = read_records(path)
    header = next(records)
    digest = hashlib.sha256()
    total = 0
    for row in records:
        total += 1
        add_digest(digest, row)
    return header, total, digest.hexdigest()


def split(path, maximum, output, expected):
    """Write only in a newly created directory. Never reuse or reset one."""
    if not 1 <= maximum <= MAX_DATA:
        raise ValueError('split size must be 1 to %d data records' % MAX_DATA)
    target = Path(output)
    target.mkdir()  # Atomic refusal of any existing output path.
    parts = []
    records = read_records(path)
    header = next(records)
    handle = None
    try:
        for row in records:
            if not parts or parts[-1][1] == maximum:
                if handle is not None:
                    handle.close()
                name = target / ('part%04d.csv' % (len(parts)+1))
                handle = name.open('x', encoding='utf-8', newline='')
                writer = csv.writer(handle, lineterminator='\r\n')
                writer.writerow(header)
                parts.append([name, 0])
            writer.writerow(row)
            parts[-1][1] += 1
    finally:
        if handle is not None:
            handle.close()
    # Verify serialized output as ordered parsed field values, not raw bytes.
    total = 0
    digest = hashlib.sha256()
    for name, count in parts:
        rows = read_records(name)
        if next(rows) != header:
            raise ValueError('part header differs')
        actual = 0
        for row in rows:
            add_digest(digest, row)
            actual += 1
        if actual != count:
            raise ValueError('part count differs')
        total += actual
    if (header, total, digest.hexdigest()) != expected:
        raise ValueError('ordered field digest/count differs from first source scan')
    return parts


def main(argv):
    if len(argv) not in (2, 5) or (len(argv) == 5 and argv[2] != '--split'):
        print('Usage: python bigcsv.py FILE [--split MAX_DATA_RECORDS NEW_FOLDER]', file=sys.stderr)
        return 2
    path = Path(argv[1])
    maximum = None
    if len(argv) == 5:
        try:
            maximum = int(argv[3])
            if not 1 <= maximum <= MAX_DATA:
                raise ValueError()
        except ValueError:
            print('Split size must be 1 to %d data records.' % MAX_DATA, file=sys.stderr)
            return 2
    try:
        expected = scan(path)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print('Cannot scan CSV: ' + str(error), file=sys.stderr)
        return 1
    header, rows, digest = expected
    print('CSV record count')
    print('File: ' + str(path))
    print('Data records: {:,}'.format(rows))
    print('Worksheet rows including header: {:,}'.format(rows+1))
    print('Excel worksheet row limit: {:,}'.format(EXCEL_GRID))
    print('Within row-count limit only.' if rows <= MAX_DATA else 'Exceeds row-count limit with one header row.')
    print('Not checked: Excel columns, cell limits, formulas, type conversions or import settings.')
    if maximum is None:
        print('Read only. --split MAX NEW_FOLDER can write new parts.')
        return 0
    try:
        parts = split(path, maximum, argv[4], expected)
    except FileExistsError:
        print('Stopped: output path already exists. Nothing there was replaced.', file=sys.stderr)
        return 1
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print('Split not verified: ' + str(error), file=sys.stderr)
        print('Keep the source. Inspect the new output folder for incomplete parts; do not use them.', file=sys.stderr)
        return 1
    for name, count in parts:
        print('Wrote %s: %s data records plus header.' % (name, format(count, ',')))
    print('Verified {:,} ordered parsed records against the first source scan.'.format(rows))
    print('Field values/order matched a SHA-256 digest; output bytes/quoting can differ.')
    print('Source was read only. This is not a full Excel compatibility or safety check.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

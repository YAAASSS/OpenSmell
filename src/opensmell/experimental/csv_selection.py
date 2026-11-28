"""Bounded streaming selection of a prepared CSV. No numeric interpretation."""
import csv
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat

from .._json import decode_bytes
from .perceptual_import import _source, MAX_SOURCE_BYTES, IDENTITY_COLUMNS, RATING_COLUMNS

SELECTION_KEY = 'org.opensmell.experimental.csv-selection'
MAX_INPUT_BYTES = 1024 * 1048576
MAX_RECORD_BYTES = 65536
MAX_OUTPUT_BYTES = 512 * 1024
MAX_RECORDS = 100


class _Lines:
    """csv.reader owns record boundaries; retain only one bounded raw record."""
    def __init__(self, stream):
        self.text = stream
        self.digest = hashlib.sha256()
        self.byte_count = 0
        self.record = bytearray()
        self.first = True

    def __iter__(self):
        return self

    def __next__(self):
        line = self.text.readline(MAX_RECORD_BYTES + 1)
        if not line:
            raise StopIteration
        raw = line.encode('utf-8')  # newline='' preserves LF/CRLF/CR; strict UTF8 is reversible
        self.record.extend(raw)
        if len(self.record) > MAX_RECORD_BYTES:
            raise ValueError('CSV logical record exceeds 64 KiB')
        self.digest.update(raw)
        self.byte_count += len(raw)
        if self.byte_count > MAX_INPUT_BYTES:
            raise ValueError('CSV input exceeds 1 GiB')
        if self.first:
            self.first = False
            if line.startswith('\ufeff'):
                return line[1:]
        return line


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def select_keller_csv(path, *, rows, source_raw, directory):
    """Scan a local prepared UTF8 CSV to EOF, then create a small passive selection.

    Selection is structural, not measurement validation. All cells/quoting stay
    byte-exact; a missing final terminator gains a declared LF only if reordered
    before another selected record. The large original is fingerprinted, not embedded.
    """
    if (not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= MAX_RECORDS
            or any(type(r) is not int or r < 1 for r in rows) or len(set(rows)) != len(rows)):
        raise ValueError('Select 1..100 unique positive logical data records in caller order')
    rows = list(rows)
    if not isinstance(source_raw, bytes) or len(source_raw) > MAX_SOURCE_BYTES:
        raise ValueError('Source declaration requires bytes within 1 MiB')
    source, _ = _source(decode_bytes(source_raw))
    if SELECTION_KEY in source:
        raise ValueError('Source already has reserved csv-selection context; explicit fresh preparation required')
    path = Path(path)
    initial = path.stat()
    if not stat.S_ISREG(initial.st_mode) or initial.st_size > MAX_INPUT_BYTES:
        raise ValueError('Expected a regular local CSV within 1 GiB')
    wanted = set(rows)
    retained, retained_size, count = {}, 0, 0
    with path.open('rb') as binary:
        before = os.fstat(binary.fileno())
        if _identity(before) != _identity(initial):
            raise ValueError('CSV changed before scanning')
        with io.TextIOWrapper(binary, encoding='utf-8', errors='strict', newline='') as text:
            lines = _Lines(text)
            reader = csv.reader(lines, strict=True)
            header = next(reader, None)
            if (not header or any(not h or h != h.strip() for h in header)
                    or len(set(header)) != len(header) or any(h not in header for h in IDENTITY_COLUMNS)
                    or not any(h in header for h in RATING_COLUMNS)):
                raise ValueError('Invalid prepared CSV headers')
            header_raw = bytes(lines.record)
            while True:
                lines.record.clear()
                offset = lines.byte_count
                try:
                    cells = next(reader)
                except StopIteration:
                    break
                count += 1
                if len(cells) != len(header):
                    raise ValueError('CSV field count mismatch at logical data record ' + str(count))
                if count in wanted:
                    raw = bytes(lines.record)
                    retained_size += len(raw)
                    if retained_size + len(header_raw) > MAX_OUTPUT_BYTES:
                        raise ValueError('Selected CSV exceeds 512 KiB')
                    retained[count] = (raw, offset)
            after = os.fstat(binary.fileno())
            if (_identity(before) != _identity(after) or _identity(after) != _identity(path.stat())
                    or lines.byte_count != before.st_size):
                raise ValueError('CSV changed while scanning; no selection prepared')
            digest, byte_count = lines.digest.hexdigest(), lines.byte_count
    missing = wanted - retained.keys()
    if missing:
        raise ValueError('Selected logical data records do not exist: ' + ','.join(map(str, sorted(missing))))
    output = bytearray(header_raw)
    mappings = []
    for index, row in enumerate(rows):
        raw, offset = retained[row]
        selected_offset = len(output)
        output.extend(raw)
        added = index < len(rows)-1 and not raw.endswith((b'\r', b'\n'))
        if added:
            output.extend(b'\n')
        mappings.append({'selected_record': index+1, 'source_record': row,
                         'source_byte_offset': offset, 'selected_byte_offset': selected_offset,
                         'original_byte_count': len(raw), 'original_sha256': hashlib.sha256(raw).hexdigest(),
                         'separator_added': bool(added)})
    if len(output) > MAX_OUTPUT_BYTES:
        raise ValueError('Selected CSV exceeds 512 KiB')
    selected = bytes(output)
    context = {'version': '0.1', 'input': {'name': path.name, 'sha256': digest, 'byte_count': byte_count,
                'data_record_count': count, 'embedded': False}, 'requested_records': rows,
                'selected_csv': {'sha256': hashlib.sha256(selected).hexdigest(), 'byte_count': len(selected)},
                'header': {'sha256': hashlib.sha256(header_raw).hexdigest(), 'byte_count': len(header_raw)},
                'records': mappings, 'original_source_sha256': hashlib.sha256(source_raw).hexdigest(),
                'limitations': ['Whole input was structurally scanned, not chemically/numerically validated.',
                               'Input digest identifies the observed byte stream, not authentication or a locked filesystem snapshot.',
                               'Only selected raw records/header retained; the full input cannot be recovered.',
                               'A declared LF may separate an originally unterminated final record reordered before another row.',
                               'Source/identity/license/scale remain caller declarations; no imputation, joins or device action.']}
    derived = deepcopy(source)
    derived['preparation'] += '; explicit streaming logical-record selection; see csv-selection context'
    derived[SELECTION_KEY] = context
    source_bytes = (json.dumps(derived, indent=2, ensure_ascii=True, allow_nan=False)+'\n').encode()
    if len(source_bytes) > MAX_SOURCE_BYTES:
        raise ValueError('Derived source declaration exceeds 1 MiB')
    report = {'format': SELECTION_KEY, 'version': '0.1', 'status': 'prepared', 'execution': 'not_attempted',
              'physical_validation': False, 'selection': context,
              'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)} for name, raw in
                        [('observations.csv', selected), ('source.json', source_bytes), ('original-source.json', source_raw)]}}
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    marker = target/'selection.json'
    marker.write_text('{"status":"incomplete","execution":"not_attempted"}\n')
    for name, raw in [('observations.csv', selected), ('source.json', source_bytes), ('original-source.json', source_raw)]:
        with (target/name).open('xb') as stream:
            stream.write(raw)
    with (target/'selection.pending').open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    (target/'selection.pending').replace(marker)
    return report

#!/usr/bin/env python3
"""
Share of history (LC classes C, D, E, F) in MARC files of the Library of Congress.

    python3 history_class_share.py parts/BooksAll.2016.part*.utf8.gz

For every record: take the first LC call number (field 050 $a, else 090 $a),
read its leading letters, and count it as a class only if the letters are a
real LC subclass (D, DK, PS ...) followed by a number. Prefixes such as MLC,
MIC, LAW or CPB are not classes. K (law) accepts up to three letters.
Reads plain or .gz MARC files (binary). Standard library only.
"""
import gzip
import re
import sys
from collections import Counter

RT, FT, SF = b"\x1d", b"\x1e", b"\x1f"
LETTERS = re.compile(r"^\s*([A-Za-z]{1,3})")

LC = set("""A AC AE AG AI AM AN AP AS AY AZ
B BC BD BF BH BJ BL BM BP BQ BR BS BT BV BX
C CB CC CD CE CJ CN CR CS CT
D DA DAW DB DC DD DE DF DG DH DJ DJK DK DL DP DQ DR DS DT DU DX
E F
G GA GB GC GE GF GN GR GT GV
H HA HB HC HD HE HF HG HJ HM HN HQ HS HT HV HX
J JA JC JF JJ JK JL JN JQ JS JV JX JZ
K
L LA LB LC LD LE LF LG LH LJ LT
M ML MT
N NA NB NC ND NE NK NX
P PA PB PC PD PE PF PG PH PJ PK PL PM PN PQ PR PS PT PZ
Q QA QB QC QD QE QH QK QL QM QP QR
R RA RB RC RD RE RF RG RJ RK RL RM RS RT RV RX RZ
S SB SD SF SH SK
T TA TC TD TE TF TG TH TJ TK TL TN TP TR TS TT TX
U UA UB UC UD UE UF UG UH
V VA VB VC VD VE VF VG VK VM
Z ZA""".split())


def valid_class(call_number):
    m = LETTERS.match(call_number or "")
    if not m:
        return None
    letters = m.group(1).upper()
    rest = call_number.strip()[len(m.group(1)):]
    if rest and not (rest[0].isdigit() or rest[0] in " ."):
        return None                      # letters are the start of a word
    if letters[0] == "K":
        return letters
    return letters if letters in LC else None


def call_number(record):
    """First 050 $a, else first 090 $a, of one binary MARC record."""
    try:
        base = int(record[12:17])
    except ValueError:
        return None
    directory = record[24:base - 1]
    found = {}
    for i in range(0, len(directory) - 11, 12):
        tag = directory[i:i + 3].decode("ascii", "ignore")
        if tag not in ("050", "090") or tag in found:
            continue
        length = int(directory[i + 3:i + 7])
        start = int(directory[i + 7:i + 12])
        field = record[base + start: base + start + length].rstrip(FT)
        for part in field.split(SF)[1:]:
            if part[:1] == b"a":
                found[tag] = part[1:].decode("utf-8", "ignore")
                break
    return found.get("050") or found.get("090")


def records(handle):
    buffer = b""
    while True:
        chunk = handle.read(1 << 20)
        if not chunk:
            break
        buffer += chunk
        pieces = buffer.split(RT)
        buffer = pieces.pop()
        for piece in pieces:
            if len(piece) > 24:
                yield piece
    if len(buffer) > 24:
        yield buffer


def main(paths):
    total = 0
    classes = Counter()
    for path in paths:
        with open(path, "rb") as probe:
            gzipped = probe.read(2) == b"\x1f\x8b"
        handle = gzip.open(path, "rb") if gzipped else open(path, "rb")
        before = total
        try:
            for record in records(handle):
                total += 1
                cls = valid_class(call_number(record))
                if cls:
                    classes[cls[0]] += 1
        except (EOFError, OSError) as error:
            print(f"WARNING: {path} is damaged ({error}); counted what could be read.",
                  file=sys.stderr)
        finally:
            handle.close()
        print(f"  {path}: {total - before:,} records", file=sys.stderr)

    classified = sum(classes.values())
    history = sum(classes[c] for c in "CDEF")
    print(f"\nRecords in files:        {total:,}")
    print(f"With a valid LC class:   {classified:,} ({classified / total:.1%})")
    for c in "CDEF":
        print(f"  {c}  {classes[c]:>10,}  {classes[c] / total:.1%}")
    print(f"History, classes C-F:    {history:,}")
    print(f"  share of all records:           {history / total:.1%}")
    print(f"  share of records with a class:  {history / classified:.1%}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])

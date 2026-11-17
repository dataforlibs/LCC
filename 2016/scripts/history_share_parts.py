#!/usr/bin/env python3
"""
History share in the Library of Congress MARC file (plain or .gz).

    python3 history_share.py BooksAll.2016.part*.utf8.gz --csv subclasses.csv

Counts, in one pass:
  1. LC class of each record (first 050 $a, fallback 090 $a), keeping only
     real LC subclass codes (so prefixes such as CPB, MLC, MIC, LAW are NOT
     counted as classes).
  2. History by class number: C, D, E, F.
  3. History by subject heading: records with $v or $x "History" in any
     650/651 (e.g. "Ukraine -- History -- 20th century").
  4. The union of 2 and 3, and the overlap.
"""
import argparse, csv, gzip, re, sys
from collections import Counter

RT, FT, SF = b"\x1d", b"\x1e", b"\x1f"
CLASS_RE = re.compile(r"^\s*([A-Za-z]{1,3})")

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


def valid_class(raw):
    """Return a valid LC subclass code from a call number, else None.
    Tries the longest leading letter run first (DJK before DJ before D)."""
    m = CLASS_RE.match(raw or "")
    if not m:
        return None
    s = m.group(1).upper()
    # the call number letters must be followed by a digit or end (not a word)
    rest = raw.strip()[len(m.group(1)):]
    if rest and not (rest[0].isdigit() or rest[0] in " ."):
        return None
    if s[0] == "K" and len(s) <= 3:      # law classes: K, KB, KBM, KF ...
        return s
    return s if s in LC else None


def is_history_term(t):
    t = re.sub(r"[^a-z ]", "", (t or "").lower()).strip()
    return t == "history"


def parse_binary(rec):
    out = {"c": None, "h": False}
    try:
        base = int(rec[12:17])
    except ValueError:
        return out
    d = rec[24:base - 1]
    got = {}
    for i in range(0, len(d) - 11, 12):
        tag = d[i:i + 3].decode("ascii", "ignore")
        if tag not in ("050", "090", "650", "651"):
            continue
        ln, st = int(d[i + 3:i + 7]), int(d[i + 7:i + 12])
        data = rec[base + st: base + st + ln].rstrip(FT)
        subs = [(p[:1].decode("ascii", "ignore"), p[1:].decode("utf-8", "ignore"))
                for p in data.split(SF)[1:]]
        if tag in ("050", "090"):
            if tag not in got:
                got[tag] = next((t for c, t in subs if c == "a"), None)
        elif any(c in "vx" and is_history_term(t) for c, t in subs):
            out["h"] = True
    out["c"] = valid_class(got.get("050") or got.get("090"))
    return out


def iter_binary(fh):
    buf = b""
    while True:
        chunk = fh.read(1 << 20)
        if not chunk:
            break
        buf += chunk
        parts = buf.split(RT)
        buf = parts.pop()
        for p in parts:
            if len(p) > 24:
                yield parse_binary(p)
    if len(buf) > 24:
        yield parse_binary(buf)


def iter_xml(fh):
    import xml.etree.ElementTree as ET
    for _, el in ET.iterparse(fh, events=("end",)):
        if el.tag.endswith("record"):
            got, h = {}, False
            for df in el:
                tag = df.attrib.get("tag")
                subs = [(s.attrib.get("code"), s.text or "") for s in df]
                if tag in ("050", "090") and tag not in got:
                    got[tag] = next((t for c, t in subs if c == "a"), None)
                elif tag in ("650", "651") and any(
                        c in ("v", "x") and is_history_term(t) for c, t in subs):
                    h = True
            yield {"c": valid_class(got.get("050") or got.get("090")), "h": h}
            el.clear()


def pct(n, d):
    return f"{n / d:.1%}" if d else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="one or more files (e.g. all 43 parts)")
    ap.add_argument("--csv")
    a = ap.parse_args()

    total = 0
    sub = Counter()
    hist_class = hist_head = both = 0
    for path in a.paths:
        with open(path, "rb") as p:
            is_gz = p.read(2) == b"\x1f\x8b"
        if is_gz:
            with gzip.open(path, "rb") as g:
                head = g.read(64)
        else:
            with open(path, "rb") as g:
                head = g.read(64)
        is_xml = head.lstrip()[:1] == b"<"
        fh = gzip.open(path, "rb") if is_gz else open(path, "rb")
        it = iter_xml(fh) if is_xml else iter_binary(fh)
        n0 = total
        try:
            for r in it:
                total += 1
                c = r["c"]
                by_class = bool(c and c[0] in "CDEF")
                if c:
                    sub[c] += 1
                hist_class += by_class
                hist_head += r["h"]
                both += by_class and r["h"]
        except (EOFError, OSError) as e:
            print(f"WARNING: {path} truncated/corrupt ({e}); partial.", file=sys.stderr)
        finally:
            fh.close()
        print(f"  {path}: {total - n0:,} records (running total {total:,})", file=sys.stderr)

    classified = sum(sub.values())
    main_c = Counter()
    for k, v in sub.items():
        main_c[k[0]] += v
    union = hist_class + hist_head - both

    print(f"\nRecords in file:                 {total:,}")
    print(f"With a valid LC class:           {classified:,} ({pct(classified, total)})")
    print(f"\n{'Class':<6}{'Records':>12}{'% of all':>10}")
    for c in "CDEF":
        print(f"{c:<6}{main_c[c]:>12,}{pct(main_c[c], total):>10}")
    print(f"{'C-F':<6}{hist_class:>12,}{pct(hist_class, total):>10}   history by class number")
    print(f"\nHistory by heading (650/651 $v or $x = History): {hist_head:,} ({pct(hist_head, total)})")
    print(f"  of which also in C-F:          {both:,}")
    print(f"  History heading, class outside C-F: {hist_head - both:,}")
    print(f"UNION (class C-F OR History heading): {union:,} ({pct(union, total)})")
    print("\nTop 15 classes:")
    for c, n in main_c.most_common(15):
        print(f"  {c}: {n:,} ({pct(n, total)})")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["subclass", "records", "pct_of_all"])
            for c, n in sorted(sub.items()):
                w.writerow([c, n, f"{n / total:.6f}"])
        print(f"\nWrote {a.csv}")


if __name__ == "__main__":
    main()

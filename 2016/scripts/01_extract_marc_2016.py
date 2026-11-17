#!/usr/bin/env python3
"""
Extract (lcc_subclass, pub_year) from LC MARC21 binary parts (BooksAll.2016.partNN.utf8.gz).

Usage:  python3 01_extract_marc_2016.py <parts_dir> <out_dir> [n_workers]
Writes: <out_dir>/subclass_raw_records.csv, class_raw_records.csv (all valid LC classes, for class-level ranks), extraction_summary.csv, dropped_valid_classes.csv

Rules
  * Call number = first 050 $a, else first 090 $a   (valid_class() is the same logic as
    history_class_share.py: only real LC subclass codes followed by a digit/space/period;
    MLC, MIC, CPB, LAW, IN ... are NOT classes).
  * pub_year = 008/07-10 (Date1), kept if 1400..2020.
  * Class -> analysis subclass (202-subclass list in subclasses.txt, plus E and F):
      E185* -> 'E18' (African American history, E185 only; the 2014 run matched all E180-E189)
      E99*  -> 'E99'
      any other E -> 'E', any F -> 'F'  (American history; both were missing in the 2014 run)
      3-letter K law codes (KBP, KDC, KFN ...) -> their 2-letter parent when that is in the list
      v2: valid LC subclasses outside the original list (PZ, NA, TT, BQ, KK, ...) are now kept as their own
      subclasses; 3-letter K codes fold into their 2-letter parent (KKH -> KK). dropped_valid_classes.csv is
      therefore empty.
"""
import gzip, re, sys, os, csv, glob
from collections import Counter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
SUBS = set(l.strip() for l in open(os.path.join(HERE, 'subclasses.txt')) if l.strip())
RT, FT, SF = b"\x1d", b"\x1e", b"\x1f"
LETTERS = re.compile(r"^\s*([A-Za-z]{1,3})")
LC = set("""A AC AE AG AI AM AN AP AS AY AZ B BC BD BF BH BJ BL BM BP BQ BR BS BT BV BX
C CB CC CD CE CJ CN CR CS CT D DA DAW DB DC DD DE DF DG DH DJ DJK DK DL DP DQ DR DS DT DU DX E F
G GA GB GC GE GF GN GR GT GV H HA HB HC HD HE HF HG HJ HM HN HQ HS HT HV HX
J JA JC JF JJ JK JL JN JQ JS JV JX JZ K L LA LB LC LD LE LF LG LH LJ LT M ML MT
N NA NB NC ND NE NK NX P PA PB PC PD PE PF PG PH PJ PK PL PM PN PQ PR PS PT PZ
Q QA QB QC QD QE QH QK QL QM QP QR R RA RB RC RD RE RF RG RJ RK RL RM RS RT RV RX RZ
S SB SD SF SH SK T TA TC TD TE TF TG TH TJ TK TL TN TP TR TS TT TX U UA UB UC UD UE UF UG UH
V VA VB VC VD VE VF VG VK VM Z ZA""".split())

def valid_class(cn):
    m = LETTERS.match(cn or "")
    if not m: return None
    letters = m.group(1).upper(); rest = cn.strip()[len(m.group(1)):]
    if rest and not (rest[0].isdigit() or rest[0] in " ."): return None
    if letters[0] == "K": return letters
    return letters if letters in LC else None

def call_number(rec):
    try: base = int(rec[12:17])
    except ValueError: return None, None
    d = rec[24:base-1]; found = {}; f008 = None
    for i in range(0, len(d)-11, 12):
        tag = d[i:i+3].decode('ascii', 'ignore'); ln = int(d[i+3:i+7]); st = int(d[i+7:i+12])
        if tag == '008' and f008 is None: f008 = rec[base+st:base+st+ln]
        if tag in ('050', '090') and tag not in found:
            fld = rec[base+st:base+st+ln].rstrip(FT)
            for part in fld.split(SF)[1:]:
                if part[:1] == b'a': found[tag] = part[1:].decode('utf-8', 'ignore'); break
    return (found.get('050') or found.get('090')), f008

def to_subclass(cn, cls):
    # Every valid LC class is analysed (v2: the 2014 list of 202 is no longer a filter).
    if cls == 'E':
        m = re.match(r"\s*E\s*(\d+)", cn.upper()); n = int(m.group(1)) if m else None
        return 'E18' if n == 185 else 'E99' if n == 99 else 'E'
    if cls == 'F': return 'F'
    if cls[0] == 'K': return cls[:2] if len(cls) >= 2 else 'K'   # KBP -> KB, KKH -> KK
    return cls

def process(args):
    path, out = args
    st = Counter(); dropped = Counter(); buf = b''
    with gzip.open(path, 'rb') as f, open(out, 'w', newline='') as o:
        w = csv.writer(o); w.writerow(['lcc_subclass', 'pub_year'])
        oc = open(out.replace('.csv', '_class.csv'), 'w', newline=''); wc = csv.writer(oc); wc.writerow(['main_class', 'pub_year'])
        while True:
            ch = f.read(1 << 24); buf += ch
            parts = buf.split(RT); buf = parts.pop()
            if not ch and len(buf) > 24: parts.append(buf); buf = b''
            for r in parts:
                if len(r) <= 24: continue
                st['records'] += 1
                try:
                    cn, f008 = call_number(r)
                    if not cn: st['no_call_number'] += 1; continue
                    cls = valid_class(cn)
                    if not cls: st['not_an_lc_class'] += 1; continue
                    st['valid_lc_class'] += 1
                    ym = re.match(rb'\d{4}', (f008 or b'')[7:11])
                    if not ym: st['no_year'] += 1; continue
                    y = int(ym.group())
                    if not 1400 <= y <= 2020: st['year_out_of_range'] += 1; continue
                    wc.writerow([cls[0], y]); st['class_level_kept'] += 1   # every valid LC class, incl. ones outside the list
                    s = to_subclass(cn, cls)
                    if s is None: dropped[cls] += 1; st['valid_class_outside_list'] += 1; continue
                    w.writerow([s, y]); st['kept'] += 1
                except Exception: st['parse_error'] += 1
            if not ch: break
    oc.close()
    return os.path.basename(path), st, dropped

if __name__ == '__main__':
    parts_dir, out_dir = sys.argv[1], sys.argv[2]; nw = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    os.makedirs(os.path.join(out_dir, 'raw'), exist_ok=True)
    files = sorted(glob.glob(os.path.join(parts_dir, '*.gz')))
    jobs = [(p, os.path.join(out_dir, 'raw', re.search(r'part(\d+)', p).group(1) + '.csv')) for p in files]
    T = Counter(); D = Counter()
    with Pool(nw) as pool:
        for name, st, dr in pool.imap_unordered(process, jobs):
            T.update(st); D.update(dr); print(name, dict(st), flush=True)
    with open(os.path.join(out_dir, 'extraction_summary.csv'), 'w') as o:
        o.write('item,count\n'); [o.write(f'{k},{v}\n') for k, v in T.items()]
    with open(os.path.join(out_dir, 'dropped_valid_classes.csv'), 'w') as o:
        o.write('lc_class,records\n'); [o.write(f'{k},{v}\n') for k, v in D.most_common()]
    with open(os.path.join(out_dir, 'subclass_raw_records.csv'), 'w', newline='') as o:
        o.write('lcc_subclass,pub_year\n')
        for _, p in jobs:
            with open(p) as f: next(f); o.write(f.read())
    with open(os.path.join(out_dir, 'class_raw_records.csv'), 'w', newline='') as o:
        o.write('main_class,pub_year\n')
        for _, p in jobs:
            with open(p.replace('.csv', '_class.csv')) as f: next(f); o.write(f.read())
    print('TOTAL', dict(T))

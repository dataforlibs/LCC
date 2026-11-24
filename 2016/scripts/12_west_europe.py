#!/usr/bin/env python3
"""
Count Western European history (DA-DQ) and literature (PQ, PR, PT) records by class number and publication year,
to compare when histories and literatures of the same countries reached their midpoint.

Usage:  python3 12_west_europe.py <parts_dir> <out_json> [n_workers]
Writes: <out_json> (e.g. west_numbers.json), same format as dk_numbers.json

Same rules as 01_extract_marc_2016.py (first 050 $a else 090 $a, pub_year = 008/07-10 in 1400..2020).
Each record is counted under a named group (a country for the D classes, a language or regional section for P).
Output keys look like "DA:Ireland", "PR:Ireland (PR8700-8893)"; numbers outside a listed range are "<class>:other".
Ranges follow the LC classification outlines. Note that major Irish and Scottish authors are classed in the
English by-period tables (Joyce PR6019, Yeats PR5900, Burns PR4300), so the PR Ireland/Scotland/Wales groups are
only the regional sections, not all Irish, Scottish or Welsh writing in English.
"""
import gzip, re, sys, os, glob, json, importlib.util
from collections import Counter, defaultdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ex01', os.path.join(HERE, '01_extract_marc_2016.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
RT = ex.RT

# Ranges from the LC classification outlines. Numbers are compared as floats.
GROUPS = {
 'DA': [(1, 9.99, 'Great Britain general (DA1-9)'), (10, 18.2999, 'British Empire (DA10-18)'), (20, 690.99, 'England'),
        (700, 745.99, 'Wales'), (750, 890.99, 'Scotland'), (900, 995.99, 'Ireland')],
 'DB': [(1, 879.99, 'Austria'), (881, 898.99, 'Liechtenstein'), (901, 999.99, 'Hungary'), (2000, 3150.99, 'Czechoslovakia, Czech Republic, Slovakia')],
 'DC': [(1, 947.99, 'France (incl. Andorra, Monaco)')],
 'DD': [(1, 905.99, 'Germany')],
 'DG': [(1, 999.99, 'Italy and Malta (DG)')],
 'DH': [(1, 399.99, 'Low Countries general (DH1-399)'), (401, 811.99, 'Belgium'), (901, 925.99, 'Luxembourg')],
 'DJ': [(1, 500.99, 'Netherlands')],
 'DL': [(1, 99.99, 'Scandinavia general (DL1-99)'), (101, 291.99, 'Denmark'), (301, 398.99, 'Iceland'), (401, 596.99, 'Norway'),
        (601, 991.99, 'Sweden'), (1002, 1180.99, 'Finland')],
 'DP': [(1, 402.99, 'Spain'), (501, 900.99, 'Portugal')],
 'DQ': [(1, 851.99, 'Switzerland')],
 'PQ': [(1, 3999.99, 'French literature'), (4001, 5999.99, 'Italian literature'), (6001, 8929.99, 'Spanish literature'), (9000, 9999.99, 'Portuguese literature (incl. Brazil)')],
 'PR': [(1, 1489.99, 'English literature: history, criticism, collections (PR1-1489)'), (1490, 6126.99, 'English literature by period (PR1490-6126)'),
        (8309, 8489.99, 'England regional (PR8309-8489)'), (8490, 8499.99, 'Celtic literature in English (PR8490-8499)'),
        (8500, 8693.99, 'Scotland regional (PR8500-8693)'), (8700, 8893.99, 'Ireland regional (PR8700-8893)'),
        (8894, 8967.99, 'Wales regional (PR8894-8967, approximate)'), (9000, 9899.99, 'Commonwealth and other (PR9000-9899)')],
 'PT': [(1, 4897.99, 'German literature'), (5001, 5980.99, 'Dutch literature'), (6000, 6467.99, 'Flemish literature'), (6500, 6593.99, 'Afrikaans literature'),
        (7001, 7099.99, 'Scandinavian literature general'), (7101, 7599.99, 'Icelandic and Old Norse literature (incl. Faroese)'),
        (7601, 8260.99, 'Danish literature'), (8301, 9155.99, 'Norwegian literature'), (9201, 9999.99, 'Swedish literature')],
}
CLASSES = tuple(GROUPS)

def key_for(cn, cls):
    m = re.match(r"\s*" + cls + r"\s*(\d+(?:\.\d+)?)", cn if isinstance(cn, str) else cn.decode('utf-8', 'replace'), re.I)
    if not m: return None
    n = float(m.group(1))
    for lo, hi, name in GROUPS[cls]:
        if lo <= n <= hi: return cls + ':' + name
    return cls + ':other'

def process(path):
    cnt = Counter(); buf = b''
    with gzip.open(path, 'rb') as f:
        while True:
            ch = f.read(1 << 24); buf += ch
            parts = buf.split(RT); buf = parts.pop()
            if not ch and len(buf) > 24: parts.append(buf); buf = b''
            for r in parts:
                if len(r) <= 24: continue
                try:
                    cn, f008 = ex.call_number(r)
                    cls = ex.valid_class(cn) if cn else None
                    if cls not in CLASSES: continue
                    ym = re.match(rb'\d{4}', (f008 or b'')[7:11])
                    if not ym: continue
                    y = int(ym.group())
                    if not 1400 <= y <= 2020: continue
                    k = key_for(cn, cls)
                    if k: cnt[(k, y)] += 1
                except Exception: pass
            if not ch: break
    return os.path.basename(path), cnt

if __name__ == '__main__':
    parts_dir, out = sys.argv[1], sys.argv[2]; nw = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    files = sorted(glob.glob(os.path.join(parts_dir, '*.gz')))
    tot = Counter()
    with Pool(nw) as pool:
        for name, c in pool.imap_unordered(process, files):
            tot.update(c); print(name, sum(c.values()), flush=True)
    d = defaultdict(dict)
    for (k, y), n in tot.items(): d[k][str(y)] = n
    json.dump({'source': 'LC MARC 2016, records with a publication year', 'classes': d}, open(out, 'w'))
    print('records:', sum(tot.values()), 'class numbers:', len(d))

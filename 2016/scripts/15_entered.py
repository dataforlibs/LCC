#!/usr/bin/env python3
"""
Count records by the year they were entered on file (MARC 008/00-05, YYMMDD) against publication year,
to test whether collections of a region were catalogued long after publication (for example in a
regional-studies buying wave) rather than when the books appeared.

Usage:  python3 15_entered.py <parts_dir> <out_json> [n_workers]
Writes: <out_json> (e.g. entered_numbers.json)

Same record rules as 14_places.py: valid LC class (first 050 $a, else 090 $a) and pub_year = 008/07-10 in 1400..2020.
Entered year: yy <= 16 -> 20yy, else 19yy. MARC began in 1968 and the file is from 2016, so any yy in 17..67
(or an unreadable date) is counted as "bad". Records converted from old catalogue cards carry the conversion
date, not the original cataloguing date, so early entry years (1968-1980) are unreliable.

Output: {"source", "bad", "all": {entered_year: n},
         "places":  {code:  {"ent": {entered_year: n}, "x": {"<pub decade>|<entered_year>": n}}},
         "classes": {cls:   {...}},            e.g. "DS", "PL", "E"
         "groups":  {group: {...}}}            e.g. "DS:China", "PL:China, Chinese literature" (as in 13_world.py)
"""
import gzip, re, sys, os, glob, json, importlib.util
from collections import Counter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
ex = load('ex01', '01_extract_marc_2016.py')
w = load('w13', '13_world.py')
RT = ex.RT

def process(path):
    ent = Counter(); cross = Counter(); allc = Counter(); bad = Counter(); buf = b''
    with gzip.open(path, 'rb') as f:
        while True:
            ch = f.read(1 << 24); buf += ch
            parts = buf.split(RT); buf = parts.pop()
            if not ch and len(buf) > 24: parts.append(buf); buf = b''
            for r in parts:
                if len(r) <= 24: continue
                try:
                    cn, f008 = ex.call_number(r)
                    if not cn or not f008 or len(f008) < 18: continue
                    cls = ex.valid_class(cn)
                    if not cls: continue
                    ym = re.match(rb'\d{4}', f008[7:11])
                    if not ym: continue
                    y = int(ym.group())
                    if not 1400 <= y <= 2020: continue
                    m = re.match(rb'(\d\d)(\d\d)(\d\d)', f008[0:6])
                    ey = None
                    if m:
                        yy = int(m.group(1)); mo = int(m.group(2))
                        if 1 <= mo <= 12:
                            ey = 2000 + yy if yy <= 16 else 1900 + yy
                            if ey < 1968: ey = None
                    if ey is None: bad['n'] += 1; continue
                    code = f008[15:18].decode('ascii', 'ignore').strip().lower()
                    if not code or code in ('|||', 'xx') or not code.isalpha(): code = 'unknown'
                    pd_ = (y // 10) * 10 if y >= 1850 else 1840
                    allc[ey] += 1
                    keys = [('places', code), ('classes', cls)]
                    if cls in w.CLASSES:
                        g = w.key_for(cn, cls)
                        if g: keys.append(('groups', g))
                    for kind, k in keys:
                        ent[(kind, k, ey)] += 1; cross[(kind, k, pd_, ey)] += 1
                except Exception: pass
            if not ch: break
    return os.path.basename(path), ent, cross, allc, bad['n']

if __name__ == '__main__':
    parts_dir, out = sys.argv[1], sys.argv[2]; nw = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    files = sorted(glob.glob(os.path.join(parts_dir, '*.gz')))
    ent = Counter(); cross = Counter(); allc = Counter(); bad = 0
    with Pool(nw) as pool:
        for name, e, c, a, b in pool.imap_unordered(process, files):
            ent.update(e); cross.update(c); allc.update(a); bad += b; print(name, sum(a.values()), flush=True)
    res = {'source': 'LC MARC 2016; entered = 008/00-05, publication year = 008/07-10', 'bad': bad,
           'all': {str(k): v for k, v in sorted(allc.items())}, 'places': {}, 'classes': {}, 'groups': {}}
    for (kind, k, ey), n in ent.items(): res[kind].setdefault(k, {'ent': {}, 'x': {}})['ent'][str(ey)] = n
    for (kind, k, pdc, ey), n in cross.items(): res[kind][k]['x'][f'{pdc}|{ey}'] = n
    json.dump(res, open(out, 'w'))
    print('records:', sum(allc.values()), 'bad entry dates:', bad, 'places:', len(res['places']), 'groups:', len(res['groups']))

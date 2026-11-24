#!/usr/bin/env python3
"""
Count world history (DR-DU, E, F) and literature (PJ, PK, PL, PQ, PR, PS) records by class number and year,
to compare when histories and literatures of the same countries reached their midpoint.

Usage:  python3 13_world.py <parts_dir> <out_json> [n_workers]
Writes: <out_json> (e.g. world_numbers.json), same format as west_numbers.json
Keys look like "DS:China" (history) or "PL:China, Chinese literature". Numbers outside listed ranges are "<class>:other".
Language-based literature groups (Arabic, Spanish American, Hindi...) cover a language area, not one country.

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

# Ranges follow the LC classification outlines (DS, DT, DU, E-F, PJ-PK, PL, PQ); a few (marked 'check') were not verified.
GROUPS = {
 'DR': [(51, 98.99, 'Bulgaria (check)'), (201, 296.99, 'Romania (check)'), (401, 741.99, 'Turkey (check)')],
 'DS': [(36, 39.2, 'Arab countries (general)'), (54, 54.95, 'Cyprus'), (67, 79.9, 'Iraq'), (80, 90.99, 'Lebanon'), (92, 99.99, 'Syria'),
        (101, 151.99, 'Israel'), (153, 154.9, 'Jordan'), (155, 156.99, 'Asia Minor'), (161, 195.5, 'Armenia'), (201, 248.99, 'Arabian Peninsula, Saudi Arabia'),
        (251, 326.99, 'Iran'), (327, 329.4, 'Central Asia'), (350, 375.99, 'Afghanistan'), (376, 392.2, 'Pakistan'), (393, 396.9, 'Bangladesh'),
        (401, 486.8, 'India'), (488, 490.99, 'Sri Lanka'), (491, 495.8, 'Bhutan and Nepal'), (527, 530.9, 'Burma'), (554, 560.72, 'Cambodia, Laos, Vietnam'),
        (561, 589.99, 'Thailand'), (591, 610.9, 'Malaysia and Singapore'), (611, 649.99, 'Indonesia'), (651, 689.99, 'Philippines'),
        (701, 799.99, 'China'), (801, 897.99, 'Japan'), (901, 937.99, 'Korea')],
 'DT': [(43, 154.99, 'Egypt'), (154.1, 159.9, 'Sudan'), (211, 239.99, 'Libya'), (241, 269.99, 'Tunisia'), (271, 299.99, 'Algeria'), (301, 330.99, 'Morocco'),
        (371, 390.99, 'Ethiopia'), (391, 398.99, 'Eritrea'), (401, 409.99, 'Somalia'), (421, 450.95, 'East Africa (Uganda, Kenya, Tanzania, Rwanda, Burundi)'),
        (509.97, 512.99, 'Ghana'), (515, 515.99, 'Nigeria'), (516, 516.99, 'Sierra Leone'), (521, 555.99, 'French West Africa'), (561, 581.99, 'Cameroon'),
        (621, 637.99, 'Liberia'), (641, 665.99, 'Congo (Zaire)'), (1251, 1465.99, 'Angola'), (1501, 1685.99, 'Namibia'), (1701, 2405.99, 'South Africa'),
        (2421, 2525.99, 'Botswana'), (2871, 3025.99, 'Zimbabwe'), (3031, 3145.99, 'Zambia'), (3161, 3257.99, 'Malawi'), (3291, 3415.99, 'Mozambique')],
 'DU': [(80, 398.99, 'Australia'), (400, 430.99, 'New Zealand'), (739, 747.99, 'New Guinea')],
 'E': [(151, 889.99, 'United States')],
 'F': [(1, 975.99, 'United States'), (1001, 1145.99, 'Canada'), (1201, 1392.99, 'Mexico'), (1421, 1577.99, 'Central America'), (1601, 2191.99, 'Caribbean'),
       (2251, 2299.99, 'Colombia'), (2301, 2349.99, 'Venezuela'), (2361, 2471.99, 'Guianas'), (2501, 2659.99, 'Brazil'), (2661, 2699.99, 'Paraguay'),
       (2701, 2799.99, 'Uruguay'), (2801, 3032.99, 'Argentina'), (3051, 3285.99, 'Chile'), (3301, 3359.99, 'Bolivia'), (3401, 3619.99, 'Peru'), (3701, 3799.99, 'Ecuador')],
 'PJ': [(5001, 5060.99, 'Israel, Hebrew literature'), (7501, 8517.99, 'Arab countries, Arabic literature'), (9001, 9269.99, 'Ethiopia, Ethiopic and Amharic')],
 'PK': [(1651, 1799.99, 'Bangladesh and Bengal, Bengali'), (2030, 2142.99, 'India, Hindi literature'), (2151, 2212.99, 'Pakistan, Urdu literature'), (6001, 6996.99, 'Iran, Persian literature')],
 'PL': [(700, 889.99, 'Japan, Japanese literature'), (950, 998.99, 'Korea, Korean literature'), (2250, 3208.99, 'China, Chinese literature'), (101, 271.99, 'Turkey, Turkish literature'), (8000, 8844.99, 'Africa, African literature')],
 'PC': [(601, 872.99, 'Romania, Romanian language and literature')],
 'PG': [(801, 1146.99, 'Bulgaria, Bulgarian language and literature')],
 'PQ': [(3900, 3919.99, 'Canada, literature in French'), (7296, 7298.99, 'Mexico, literature'), (7370, 7442.99, 'Cuba, Dominican Republic, Puerto Rico, literature'), (7471, 7539.99, 'Central America, literature'),
        (7600, 7798.99, 'Argentina, literature'), (7800, 7822.99, 'Bolivia, literature'), (7900, 8098.99, 'Chile, literature'), (8160, 8180.99, 'Colombia, literature'),
        (8200, 8220.99, 'Ecuador, literature'), (8250, 8259.99, 'Paraguay, literature'), (8300, 8498.99, 'Peru, literature'), (8510, 8520.99, 'Uruguay, literature'),
        (8530, 8550.99, 'Venezuela, literature'), (9500, 9698.99, 'Brazil, literature')],
 'PR': [(9180, 9199.99, 'Canada, literature in English'), (9600, 9619.99, 'Australia, literature'), (9620, 9639.99, 'New Zealand, literature')],
 'PS': [(1, 3576.99, 'United States, literature'), (3600, 3999.99, 'United States, literature')],
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

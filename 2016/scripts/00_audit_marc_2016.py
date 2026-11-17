#!/usr/bin/env python3
"""Audit where every MARC record goes. Usage: python3 00_audit_marc_2016.py <parts_dir> [workers]"""
import gzip, re, sys, glob, collections
from multiprocessing import Pool
def audit(p):
    c=collections.Counter(); pref=collections.Counter()
    buf=b''; f=gzip.open(p,'rb')
    while True:
        ch=f.read(1<<24); buf+=ch; parts=buf.split(b'\x1d'); buf=parts.pop()
        if not ch and buf.strip(): parts.append(buf); buf=b''
        for r in parts:
            if len(r)<24: continue
            c['records']+=1
            try:
                base=int(r[12:17]); d=r[24:base-1]; t={}
                for i in range(0,len(d)-11,12):
                    tag=d[i:i+3]; st=base+int(d[i+7:i+12]); t.setdefault(tag,[]).append(r[st:st+int(d[i+3:i+7])])
                has050=b'050' in t; other=any(x in t for x in (b'090',b'060',b'082',b'084'))
                if not has050:
                    c['no050']+=1
                    if b'090' in t: c['no050_has090']+=1
                    if b'082' in t: c['no050_has082_dewey']+=1
                    if not other: c['no050_no_other_callno']+=1
                    continue
                c['has050']+=1
                sa=[x for x in t[b'050'][0].split(b'\x1f')[1:] if x[:1]==b'a']
                if not sa: c['050_no_a']+=1; continue
                m=re.match(r'[A-Z]{1,3}',sa[0][1:].decode('utf8','ignore').strip().upper())
                if not m: c['050_nonletter']+=1; continue
                pref[m.group()]+=1
                y=re.match(rb'\d{4}',t[b'008'][0][7:11]) if b'008' in t else None
                if not y: c['bad_year']+=1
                elif not 1400<=int(y.group())<=2020: c['year_out_of_range']+=1
            except Exception: c['parse_error']+=1
        if not ch: break
    return c,pref
if __name__=='__main__':
    fs=sorted(glob.glob(sys.argv[1]+'/*.gz')); C=collections.Counter(); P=collections.Counter()
    with Pool(int(sys.argv[2]) if len(sys.argv)>2 else 2) as pool:
        for c,p in pool.imap_unordered(audit,fs): C.update(c); P.update(p)
    for k,v in C.most_common(): print(f'{k:28s}{v:>12,}')
    print('TOP PREFIXES',P.most_common(40))
    import json; json.dump({'counts':C,'prefixes':P},open('audit.json','w'))

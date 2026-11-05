# 予算書PDFから事業（◎）を抜き出すスクリプト（作成時に使用したもの）
# 使い方: 予算書PDFを r8ip.pdf として置き、python3 extract_projects.py → proj.json
# 必要: pip install pdfplumber
import pdfplumber, re, json
p=pdfplumber.open('r8ip.pdf')
def num(s):
    s=s.replace(',','').replace('△','-')
    try: return int(s)
    except: return None
proj=[]; kan=kou=None; moku=None
for pn in range(31,182):
    pg=p.pages[pn]
    ws=pg.extract_words()
    rows={}
    for w in ws: rows.setdefault(round(w['top']/4),[]).append(w)
    keys=sorted(rows)
    for idx,k in enumerate(keys):
        r=sorted(rows[k],key=lambda w:w['x0'])
        line=' '.join(w['text'] for w in r)
        m=re.search(r'（款）\s*(\d+)\s*(\S+)\s*（項）\s*(\d+)\s*(\S+)',line)
        if not m and '（款）' in line and idx+1<len(keys):
            nl=' '.join(w['text'] for w in sorted(rows[keys[idx+1]],key=lambda w:w['x0']))
            m2=re.match(r'(\d+)\s*(\S+)\s+(\d+)\s*(\S+)',nl)
            if m2: kan=(int(m2.group(1)),m2.group(2)); kou=(int(m2.group(3)),m2.group(4)); continue
        if m:
            kan=(int(m.group(1)),m.group(2)); kou=(int(m.group(3)),m.group(4)); continue
        lw=[w for w in r if w['x0']<50 and re.match(r'^\d+\D',w['text'])]
        if lw: moku=re.sub(r'^\d+','',lw[0]['text'])
        for w in r:
            if w['text'].startswith('◎') and w['x0']>590:
                amt=[x for x in r if x['x0']>w['x1'] and x['x1']>770]
                name=''.join(x['text'] for x in r if x['x0']>=w['x0'] and x['x1']<770)
                v=num(amt[0]['text']) if amt else None
                if v is None and idx+1<len(keys):
                    nr=sorted(rows[keys[idx+1]],key=lambda w:w['x0'])
                    name+=''.join(x['text'] for x in nr if 600<=x['x0'] and x['x1']<770 and not x['text'].startswith(('・','◎')) and not re.match(r'^\d\d$',x['text']))
                    a2=[x for x in nr if x['x1']>770]
                    v=num(a2[0]['text']) if a2 else None
                proj.append(dict(kan=kan[1],kanno=kan[0],kou=kou[1],kouno=kou[0],name=name[1:],v=v,page=pn+1))
json.dump(proj,open('proj.json','w'),ensure_ascii=False,indent=0)
from collections import defaultdict
s=defaultdict(int)
for x in proj: s[(x['kanno'],x['kan'],x['kouno'],x['kou'])]+= x['v'] or 0
for k in sorted(s): print(k,s[k])
print(len(proj),[x for x in proj if not x['v']])

# 事業一覧に「令和7年度の当初予算と決算」を足すスクリプト
# 使い方:
#   pdftotext -layout r7yosannsyo.pdf r7.txt        （令和7年度 一般会計当初予算書）
#   pdftotext -bbox r7seikasetumei.pdf seika.html    （令和7年度 成果説明書。座標つき）
#   python3 tools/build_kessan.py r7.txt seika.html
# 出力: data/kessan_r7.csv、data/projects.csv / .json と index.html の埋め込みデータに
#       r7_budget（R7当初・千円）、r7_kessan（R7決算・千円）、r7_page（成果説明書の頁）を追加
import csv, html as html_lib, json, re, sys

r7_txt, seika_txt = sys.argv[1], sys.argv[2]

# 令和7年度当初予算書の「◎」事業
b7 = {}
lines = open(r7_txt, encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    m = re.search(r'◎(\S+(?:\s\S+)?)\s+([\d,]+)\s*$', l)
    if m:
        n = m.group(1).replace(' ', '')
        b7[n] = b7.get(n, 0) + int(m.group(2).replace(',', ''))
        continue
    m = re.search(r'◎(\S+)\s*$', l)
    if m and i + 1 < len(lines):
        m2 = re.search(r'(\S+)\s+([\d,]+)\s*$', lines[i + 1].strip())
        if m2:
            n = m.group(1) + m2.group(1)
            b7[n] = b7.get(n, 0) + int(m2.group(2).replace(',', ''))

# 成果説明書の事務事業（一般会計だけ）。「年度別事業費」の行の数字を、
# 見出し「令和7年度」の列に位置（x座標）で対応づける。
# -layout のテキストは列の順番が入れ替わるページがあるため、座標で読む。
k7 = {}
src = open(seika_txt, encoding='utf-8').read()
for pno, pg in enumerate(src.split('<page ')[1:], 1):
    ws = [(float(a), float(b), float(c), float(d), html_lib.unescape(t)) for a, b, c, d, t in
          re.findall(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)<', pg)]
    heads = [w for w in ws if '会計・款・項・目' in w[4]]
    for e in [w for w in ws if w[4] == '年度別事業費']:
        y = e[1]
        hd = max([w for w in heads if w[1] < y], key=lambda w: w[1], default=None)
        if not hd:
            continue
        cand = [w for w in ws if 4 < hd[1] - w[1] < 20 and w[0] < 330]
        if not cand:
            continue
        ny = max(w[1] for w in cand)
        name = ''.join(w[4] for w in sorted([w for w in cand if abs(w[1] - ny) < 2], key=lambda w: w[0]))
        acct = ''.join(w[4] for w in sorted([w for w in ws if 4 < w[1] - hd[1] < 20 and w[0] < 120], key=lambda w: w[0]))
        if not acct.startswith('一般会計'):
            continue
        hdrs = [w for w in ws if w[4].startswith('令和７年度') and 0 < y - w[1] < 16]
        nums = [w for w in ws if abs(w[1] - y) < 2 and re.match(r'^[\d,]+$', w[4])]
        if not hdrs or not nums:
            continue
        n = min(nums, key=lambda w: abs(w[2] - hdrs[0][2]))
        if abs(n[2] - hdrs[0][2]) > 30:
            continue
        if name in k7:
            print('成果説明書で重複:', name, file=sys.stderr)
        k7[name] = (int(n[4].replace(',', '')), pno)

proj = list(csv.DictReader(open('data/projects.csv', encoding='utf-8-sig')))
out = []
for p in proj:
    n = p['name']
    b, k = b7.get(n), k7.get(n)
    p['r7_budget'] = b if b is not None else ''
    p['r7_kessan'] = k[0] if k else ''
    p['r7_page'] = k[1] if k else ''
    out.append(dict(name=n, r8_budget=p['amount'], r7_budget=p['r7_budget'], r7_kessan=p['r7_kessan'], seika_page=p['r7_page']))

fields = list(proj[0].keys())
with open('data/projects.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(proj)
with open('data/kessan_r7.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

def jv(p):
    d = dict(p)
    for k in ('amount', 'page', 'r7_budget', 'r7_kessan', 'r7_page'):
        d[k] = int(d[k]) if str(d[k]) != '' else None
    return d
pj = [jv(p) for p in proj]
json.dump(pj, open('data/projects.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# index.html の埋め込みデータを差し替え
html = open('index.html', encoding='utf-8').read()
pre = '<script>dash._load('
a = html.index(pre) + len(pre)
b = html.index(');</script>', a)
emb = json.loads(html[a:b])
emb['projects'] = pj
html = html[:a] + json.dumps(emb, ensure_ascii=False) + html[b:]
open('index.html', 'w', encoding='utf-8').write(html)

hit = sum(1 for p in proj if p['r7_kessan'] != '')
print(f'事業 {len(proj)} 件のうち、R7決算が見つかった {hit} 件、R7当初が見つかった {sum(1 for p in proj if p["r7_budget"] != "")} 件')

"""近隣・類似団体との比較データ（data/compare.json）を作り、index.html に埋め込む。

元データはすべて総務省の公開xlsx。初回はダウンロードして tools/.cache/ に置く。
    python3 tools/build_compare.py
"""
import json
import pathlib
import re
import statistics
import urllib.request

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / 'tools' / '.cache'
BASE = 'https://www.soumu.go.jp/main_content/'

# 市町村別決算状況調：年度ごとに [都市の5表, 町村の5表]（概況・歳入・目的別・性質別・地方債現在高等）
KESSAN = {
    'R2': ('r02', ['000800819', '000800820', '000800822', '000800823', '000800825'], ['000800826', '000800828', '000800830', '000800832', '000800834']),
    'R3': ('r03', ['000871018', '000871019', '000871020', '000871021', '000871022'], ['000871023', '000871024', '000871025', '000871026', '000871027']),
    'R4': ('r04', ['000937287', '000937288', '000937289', '000937290', '000937291'], ['000937292', '000937293', '000937294', '000937295', '000937296']),
    'R5': ('r05', ['000999900', '000999901', '000999902', '000999903', '000999904'], ['000999905', '000999906', '000999908', '000999910', '000999911']),
    'R6': ('r06', ['001061669', '001061670', '001061671', '001061672', '001061673'], ['001061674', '001061675', '001061676', '001061677', '001061678']),
}
RUIJI_LIST = '001085446'  # 令和6年度 類似団体別市町村財政指数表 都道府県別団体名一覧表
AGE = '001023715'  # 令和7年 住民基本台帳年齢階級別人口（市区町村別・総計）

KOMORO = '202088'
KINRIN = {'202037': '上田市', '202177': '佐久市', '202193': '東御市', '203211': '軽井沢町', '203238': '御代田町', '203246': '立科町'}
RUIJI = {'202070': '須坂市', '062111': '東根市', '082368': '小美玉市', '082309': 'かすみがうら市'}
GROUP = '都市Ⅰ－１'


def fetch(fid):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{fid}.xlsx'
    if not p.exists():
        req = urllib.request.Request(BASE + f'{fid}.xlsx', headers={'User-Agent': 'Mozilla/5.0'})
        p.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return p


def load_table(fid):
    """決算状況調の1表を {団体コード: {見出し: 値}} にする。見出しは複数行を '/' でつなぐ。"""
    out = {}
    for ws in openpyxl.load_workbook(fetch(fid), read_only=True, data_only=True):
        rows = list(ws.iter_rows(values_only=True))
        h = next(i for i, r in enumerate(rows) if r and '団体名' in [str(c).strip() if c else '' for c in r])
        ncol = max(len(r) for r in rows)
        hdr = []
        for j in range(ncol):
            parts = [str(rows[i][j]).replace('\n', '').replace('　', '') for i in range(h, h + 6)
                     if j < len(rows[i]) and rows[i][j] not in (None, '')]
            hdr.append('/'.join(parts))
        for r in rows[h + 6:]:
            if r and len(r) > 14 and r[14] and re.fullmatch(r'\d{6}', str(r[14])):
                out.setdefault(str(r[14]), {}).update({hdr[j]: r[j] for j in range(15, len(r)) if r[j] is not None})
    return out


def pick(d, pat):
    for k, v in d.items():
        if re.search(pat, k):
            return v
    return None


def num(x):
    if isinstance(x, (int, float)):
        return x
    return 0 if x in ('-', '－') else None


def indicators(t):
    """1団体1年度の5表から、ページに出す指標を計算する。金額は千円、1人あたりは円。"""
    g, rv, mk, se, sa = t
    pop = pick(g, r'^住民基本台帳登載人口')
    ssk = pick(g, r'^標準財政規模')

    def pc(x):
        x = num(x)
        return None if x is None else round(x * 1000 / pop)

    return {
        'pop': pop,
        'zaiseiryoku': pick(g, r'^財政力指数'),
        'keijo': pick(g, r'^経常収支比率'),
        'jisshitsu_kosai': pick(g, r'実質公債費比率'),
        'shorai_futan': num(pick(g, r'将来負担比率')),
        'zaicho_ratio': round(num(pick(sa, r'財政調整基金')) / ssk * 100, 1),
        'saishutsu_pc': pc(pick(g, r'^歳出総額')),
        'chihozei_pc': pc(pick(rv, r'^一/地方税$')),
        'furusato_pc': pc(pick(rv, r'ふるさと納税')),
        'chihosai_pc': pc(pick(sa, r'^地方債現在高')),
        'minsei_pc': pc(pick(mk, r'^三/民生費')),
        'kyoiku_pc': pc(pick(mk, r'^十/教育費')),
        'kensetsu_pc': pc(pick(se, r'^六/普通建設事業費')),
        'shokuin_pk': round(num(pick(se, r'職員総数')) / pop * 1000, 2),
    }


def main():
    # 類似団体区分（R6）
    ws = openpyxl.load_workbook(fetch(RUIJI_LIST), read_only=True, data_only=True).active
    group, excluded = [], set()
    for r in ws.iter_rows(min_row=4, values_only=True):
        vals = [str(x) for x in r if x is not None]
        if GROUP in vals:
            group.append(vals[0])
            if '※' in vals:
                excluded.add(vals[0])
    selected = [c for c in group if c not in excluded]

    targets = {KOMORO: '小諸市', **KINRIN, **RUIJI}
    years = list(KESSAN)
    series, median = {c: {} for c in targets}, {}
    profile = {}
    for y, (_, city, town) in KESSAN.items():
        tables = [{**load_table(a), **load_table(b)} for a, b in zip(city, town)]
        per = {}
        for c in set(selected) | set(targets):
            if c in tables[0]:
                per[c] = indicators([tb.get(c, {}) for tb in tables])
        for c in targets:
            series[c][y] = per[c]
        median[y] = {k: round(statistics.median([per[c][k] for c in selected if c in per and per[c][k] is not None]), 2)
                     for k in per[KOMORO] if k != 'pop'}
        if y == 'R6':
            for c in targets:
                g = tables[0][c]
                profile[c] = {
                    'area': pick(g, r'^面積'),
                    'ind1': pick(g, r'第１次'), 'ind2': pick(g, r'第２次'), 'ind3': pick(g, r'第３次'),
                }

    # 高齢化率（65歳以上の割合）
    ws = openpyxl.load_workbook(fetch(AGE), read_only=True, data_only=True).active
    for r in ws.iter_rows(values_only=True):
        if r[3] == '計' and str(r[0]) in targets and r[4]:
            profile[str(r[0])]['aging'] = round(sum(r[18:26]) / r[4] * 100, 1)

    out = {
        'years': years,
        'names': targets,
        'komoro': KOMORO,
        'kinrin': list(KINRIN),
        'ruiji': list(RUIJI),
        'group': GROUP,
        'group_total': len(group),
        'group_selected': len(selected),
        'series': series,
        'median': median,
        'profile': profile,
    }
    (ROOT / 'data' / 'compare.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    # Excel で開ける CSV（1行＝1団体×1年度）
    keys = list(series[KOMORO]['R6'])
    lines = [','.join(['団体コード', '団体名', '年度'] + keys)]
    for c, name in targets.items():
        for y in years:
            lines.append(','.join([c, name, y] + ['' if series[c][y][k] is None else str(series[c][y][k]) for k in keys]))
    (ROOT / 'data' / 'compare.csv').write_text('\ufeff' + '\n'.join(lines) + '\n', encoding='utf-8')

    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    block = '<script id="cmp-data">window.KM_CMP = ' + json.dumps(out, ensure_ascii=False) + ';</script>'
    html, n = re.subn(r'<script id="cmp-data">.*?</script>', lambda m: block, html, flags=re.S)
    if n != 1:
        raise SystemExit('index.html に <script id="cmp-data"> が見つからない')
    (ROOT / 'index.html').write_text(html, encoding='utf-8')
    print('data/compare.json と index.html を更新した')


if __name__ == '__main__':
    main()

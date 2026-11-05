# 款・項の表と事業一覧を data/*.json にまとめるスクリプト（作成時に使用したもの）
# 款別の金額と財源内訳（REV / EXP）は予算書の「事項別明細書 総括」（PDF 8〜9頁）から転記。
# 項は第1表（PDF 2〜6頁）のテキスト（all.txt = pdfplumber で全頁を書き出したもの）から読み取り、款の合計と一致するか検算する。
import re, json
txt=open('all.txt').read()
s=txt[txt.index('#### PAGE 1\n'):txt.index('#### PAGE 6\n')]
REV=[(1,'市税',5222285,5200193),(2,'地方譲与税',210000,217237),(3,'利子割交付金',7000,2000),(4,'配当割交付金',20000,20000),(5,'株式等譲渡所得割交付金',20000,10000),(6,'法人事業税交付金',90000,90000),(7,'地方消費税交付金',1000000,1000000),(8,'ゴルフ場利用税交付金',7000,7000),(9,'地方特例交付金',67469,30978),(10,'地方交付税',4750000,4350000),(11,'交通安全対策特別交付金',3000,3000),(12,'分担金及び負担金',104355,95677),(13,'使用料及び手数料',261199,238493),(14,'国庫支出金',5747253,4626703),(15,'県支出金',1330142,1204047),(16,'財産収入',94608,73342),(17,'寄附金',421020,439020),(18,'繰入金',1920354,1785942),(19,'繰越金',200000,200000),(20,'諸収入',892015,845668),(21,'市債',1332300,412700),(99,'環境性能割交付金（廃款）',0,18000)]
EXP=[(1,'議会費',186251,181559,0,0,0,186251),(2,'総務費',2331772,2159684,170073,8300,151351,2002048),(3,'民生費',7211982,6838320,3303458,7600,128019,3772905),(4,'衛生費',3773752,3551026,2229210,1200,163597,1379745),(5,'労働費',71842,71845,0,0,70121,1721),(6,'農林水産業費',454367,502373,86609,13700,17481,336577),(7,'商工費',1062412,1412113,18750,0,637158,406504),(8,'土木費',2291958,1923536,357718,394600,95481,1444159),(9,'消防費',525288,517465,0,0,23548,501740),(10,'教育費',3906327,1779321,905677,906900,538632,1555118),(11,'災害復旧費',100,100,0,0,0,100),(12,'公債費',1824819,1875858,0,0,0,1824819),(13,'諸支出金',20932,20932,0,0,0,20932),(14,'予備費',38198,35868,0,0,0,38198)]
for r in EXP: assert r[2]==sum(r[4:]),r
assert sum(r[2] for r in REV)==23700000 and sum(r[3] for r in REV)==20870000
assert sum(r[2] for r in EXP)==23700000 and sum(r[3] for r in EXP)==20870000
def rg(n):
    return {1:'市税',10:'地方交付税',7:'地方消費税交付金',14:'国庫支出金',15:'県支出金',21:'市債',18:'繰入金（基金の取り崩しなど）'}.get(n, '譲与税・各種交付金' if n in (2,3,4,5,6,8,9,11,99) else 'その他の収入')
rev_kan=[dict(no=n,kan=k,amount=a,prev=p,group=rg(n)) for n,k,a,p in REV]
small={5,11,13,14}
exp_kan=[dict(no=n,kan=k,amount=a,prev=p,kenkoku=kk,chihousai=c,sonota=so,ippan=ip,group=('労働費・災害復旧費・諸支出金・予備費' if n in small else k)) for n,k,a,p,kk,c,so,ip in EXP]
# kou parse
lines=[l.strip() for l in s.split('\n')]
revnames={k:n for n,k,a,p in REV}; expnames={k:n for n,k,*_ in EXP}
side='rev'; cur=None; rev_kou=[]; exp_kou=[]
for l in lines:
    if l.startswith('歳 出'): side='exp'; cur=None; continue
    m=re.match(r'^(\d+)\s+(.+?)\s+([\d,]+)$',l)
    if not m: continue
    no,name,amt=int(m.group(1)),m.group(2).replace(' ',''),int(m.group(3).replace(',',''))
    names=revnames if side=='rev' else expnames
    if name.startswith('商工費1'): cur='商工費'; exp_kou.append(dict(kan='商工費',kou='商工費',amount=amt)); continue
    if name in names and names[name]==no and cur!=name:
        cur=name; continue
    if name=='新型コロナウイルス感染症対策地方税減収補': name='新型コロナウイルス感染症対策地方税減収補填特別交付金'
    (rev_kou if side=='rev' else exp_kou).append(dict(kan=cur,kou=name,amount=amt))
from collections import defaultdict
def chk(rows,K):
    d=defaultdict(int)
    for r in rows: d[r['kan']]+=r['amount']
    for n,k,a,*_ in K:
        if a and d[k]!=a: print('MISMATCH',k,d[k],a)
chk(rev_kou,REV); chk(exp_kou,EXP)
proj=json.load(open('proj.json'))
P=[]
for x in proj:
    if x['v'] is None: x['v']=50
    P.append(dict(kan=x['kan'],kou=x['kou'],name=x['name'],amount=x['v'],page=x['page']))
P.append(dict(kan='民生費',kou='人権政策費',name='男女共同参画推進事業',amount=994,page=91))
P.sort(key=lambda x:(-x['amount']))
for i,x in enumerate(P): x['id']=f'P{i+1:03d}'
dk=defaultdict(int)
for x in P: dk[(x['kan'],x['kou'])]+=x['amount']
for r in exp_kou:
    if dk[(r['kan'],r['kou'])]!=r['amount']: print('projdiff',r,dk[(r['kan'],r['kou'])])
print('proj total',sum(x['amount'] for x in P), len(P))
kikin=[dict(fund='財政調整基金',amount=1429000,prev=1388000),dict(fund='学校建設準備基金',amount=400000,prev=0),dict(fund='地域振興基金',amount=80506,prev=86829),dict(fund='森林環境整備基金',amount=5280,prev=500),dict(fund='地域福祉基金',amount=1400,prev=1800),dict(fund='環境衛生基金',amount=1000,prev=1000),dict(fund='減債基金',amount=0,prev=300000),dict(fund='特別会計からの繰入金',amount=3168,prev=None)]
print('kikin',sum(k['amount'] for k in kikin))
pop=[dict(date='2026-04-01',population=40800,basis='住民基本台帳（小諸市区別世帯人口表）')]
import os
od=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data'); os.makedirs(od,exist_ok=True)
for n,o in [('rev_kan',rev_kan),('rev_kou',rev_kou),('rev_kikin',kikin),('exp_kan',exp_kan),('exp_kou',exp_kou),('projects',P),('population',pop)]:
    json.dump(o,open(f'{od}/{n}.json','w'),ensure_ascii=False)
    print(n,len(o),os.path.getsize(f'{od}/{n}.json'))

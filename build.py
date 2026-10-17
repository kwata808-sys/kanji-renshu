"""データを組み立てて docs/ に公開用の一式を作る。python3 build.py"""
import json, re, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(f"{ROOT}/data/kanji.json"))
# 学年は現行の配当表（src/grades.txt）から取る。kanji.json の学年は2020年より前のもの
grade = {}
for line in open(f"{ROOT}/src/grades.txt"):
    if line.startswith("#") or not line.strip(): continue
    g, ks = line.split()
    for k in ks: grade[k] = int(g)

strokes, readings = {}, {}
for k in grade:
    s = open(f"{ROOT}/data/kvg/kanji/{ord(k):05x}.svg").read()
    strokes[k] = re.findall(r'<path[^>]* d="([^"]+)"', s)
    v = d.get(k, {"readings_kun": [], "readings_on": []})
    kun = [r for r in v["readings_kun"] if not r.startswith("-") and not r.endswith("-")]
    on = v["readings_on"]
    readings[k] = (on[0] if on else "") + "|" + (kun[0] if kun else "")

def make_icons(out):
    """ホーム画面のアイコン：緑の地に白い「字」と赤丸"""
    from PIL import Image, ImageDraw, ImageFont
    font = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
    for size in (180, 192, 512):
        im = Image.new("RGB", (size, size), "#2e7a57")
        dr = ImageDraw.Draw(im)
        f = ImageFont.truetype(font, int(size * 0.58))
        dr.text((size / 2, size / 2), "字", font=f, fill="white", anchor="mm")
        m = size * 0.12
        dr.ellipse([m, m, size - m, size - m], outline="#ff6b57", width=max(3, size // 28))
        im.save(f"{out}/icon-{size}.png")

errs = []
def load_questions(name):
    """2年生の文つき問題を読み、文に答えの字が出ていないかなどを検査する"""
    out = []
    for line in open(f"{ROOT}/src/{name}"):
        line = line.strip()
        if not line or line.startswith("#"): continue
        w, r, s = line.split("|")
        if s.count("＿") != 1: errs.append(f"{name} ＿が1つでない: {line}")
        for c in s:
            if c in grade and grade[c] >= 2: errs.append(f"{name} 文に2年以上の漢字 {c}: {line}")
        for c in w:
            if re.match(r"[\u4e00-\u9fff]", c) and c not in strokes: errs.append(f"{name} 書き順なし {c}: {line}")
        out.append([w, r, s])
    g2 = [k for k, g in grade.items() if g == 2]
    covered = set("".join(q[0] for q in out))
    missing = [k for k in g2 if k not in covered]
    if missing: errs.append(f"{name} 問題のない2年の字: " + "".join(missing))
    return out
qs = load_questions("questions.txt")
unko = {"2": load_questions("unko2.txt")}

def load_stories(name, g):
    """長文。地の文と題に、その学年の字が出ていないか（答えを先に見せていないか）を検査する"""
    out, cur = [], None
    for n, line in enumerate(open(f"{ROOT}/src/{name}"), 1):
        line = line.rstrip("\n")
        if line.startswith("#") and not line.startswith("## "): continue
        if line.startswith("## "):
            cur = {"t": line[3:].strip(), "x": []}; out.append(cur); plain = cur["t"]
        elif cur is not None and line.strip():
            cur["x"].append(line.strip()); plain = re.sub(r"\{[^}]*\}", "", line)
            for w, r in re.findall(r"\{([^|}]+)\|([^}]+)\}", line):
                if not any(grade.get(c) == g for c in w): errs.append(f"{name} {n}行目: {w} に{g}年の字が無い")
                if any(re.match(r"[\u4e00-\u9fff]", c) and grade.get(c, 9) > g for c in w): errs.append(f"{name} {n}行目: {w} に{g}年より後の字")
        else: continue
        bad = [c for c in plain if grade.get(c, 0) >= g]
        if bad: errs.append(f"{name} {n}行目: 地の文に{g}年以上の字 {''.join(bad)}")
    return out
stories = {"2": load_stories("stories2.txt", 2)}

kana = []
for line in open(f"{ROOT}/src/kana.txt"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    kana.append(line.split("|"))

if errs:
    print("\n".join(errs)); sys.exit(1)

# 言葉の読みの辞書（JMdict のよく使う言葉から、小学校の漢字だけでできた言葉）
import glob
KANA = re.compile(r"^[\u3041-\u309f\u30a0-\u30ffー]+$")
full = {}
jm = json.load(open(glob.glob(f"{ROOT}/data/jmdict-eng-common*.json")[0]))
for e in jm["words"]:
    for k in e["kanji"]:
        t = k["text"]
        ks = [c for c in t if not KANA.match(c)]
        if not ks or any(c not in grade for c in ks): continue
        rs = sorted([r for r in e["kana"] if r["appliesToKanji"] == ["*"] or t in r["appliesToKanji"]], key=lambda r: not r["common"])
        if rs and (t not in full or (k["common"] and not full[t][1])): full[t] = (rs[0]["text"], k["common"])
dic = {k: v[0] for k, v in full.items()}

# 2年生以外の問題は src/words.txt（字ごとに子ども向けの言葉を選んだもの）から作る。読みは辞書から引く
words = {g: [] for g in range(1, 7)}
for n, line in enumerate(open(f"{ROOT}/src/words.txt"), 1):
    line = line.strip()
    if not line or line.startswith("#"): continue
    k, *ws = line.split()
    if k not in grade: errs.append(f"words.txt {n}行目: {k} は配当表に無い"); continue
    g = grade[k]
    for w in ws:
        m = re.match(r"^(.+?)（(.+)）$", w)
        w, r = (m.group(1), m.group(2)) if m else (w, dic.get(w, ""))
        if k not in w: errs.append(f"words.txt {n}行目: {w} に {k} が無い")
        late = [c for c in w if not KANA.match(c) and grade.get(c, 9) > g]
        if late: errs.append(f"words.txt {n}行目: {w} に {g}年より後の字 {''.join(late)}")
        if not r: errs.append(f"words.txt {n}行目: {w} の読みが辞書に無い")
        words[g].append([w, r, "＿"])
nowords = [k for k, g in grade.items() if g != 2 and not any(k in x[0] for x in words[g])]
if nowords: errs.append("言葉の無い字: " + "".join(nowords))
if errs:
    print("\n".join(errs)); sys.exit(1)
q = {str(g): (qs if g == 2 else words[g]) for g in range(1, 7)}
nq = {g: len(v) for g, v in q.items()}
none = [k for k in grade if not any(k in x[0] for x in q[str(grade[k])])]
data = {"stories": stories, "unko": unko, "dic": dic, "strokes": strokes, "read": readings, "grade": grade, "q": q, "kana": kana}
# 共有先（GASのURL）は config.json に置く。無ければ端末だけに保存する
cfg = json.load(open(f"{ROOT}/config.json")) if os.path.exists(f"{ROOT}/config.json") else {}
body = open(f"{ROOT}/src/app.html").read()
body = body.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
body = body.replace('/*SYNC_URL*/""', json.dumps(cfg.get("sync_url", "")))
head = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="かんじ">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#f3f7f1">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" href="icon-192.png">
</head><body>
"""
import datetime
ver_label = datetime.datetime.now().strftime("%m%d-%H%M")
body = body.replace("/*VERSION*/", ver_label)
html = head + body + "\n</body></html>\n"
out = f"{ROOT}/docs"
os.makedirs(out, exist_ok=True)
open(f"{out}/index.html", "w").write(html)
open(f"{out}/.nojekyll", "w").write("")
open(f"{out}/version.txt", "w").write(ver_label)
json.dump({"name": "かんじ練習帳", "short_name": "かんじ", "start_url": "./", "scope": "./", "display": "standalone",
           "background_color": "#f3f7f1", "theme_color": "#f3f7f1", "lang": "ja",
           "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                     {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}]},
          open(f"{out}/manifest.webmanifest", "w"), ensure_ascii=False)
# 版が変わるたびに sw.js の中身も変わるようにして、更新が端末に届くようにする
import hashlib
ver = hashlib.sha1(html.encode()).hexdigest()[:10]
open(f"{out}/sw.js", "w").write(open(f"{ROOT}/src/sw.js").read().replace("__VERSION__", ver))
make_icons(out)
print(f"ok: 問題数 {nq} / 問題の無い字 {len(none)}({''.join(none)}) / かな{len(kana)}問 / 書き順{len(strokes)}字 / {len(html)//1024}KB / 共有先 {'あり' if cfg.get('sync_url') else 'なし'} / 版 {ver_label}")

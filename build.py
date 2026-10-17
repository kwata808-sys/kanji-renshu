"""データを組み立てて dist/index.html を作る。python3 build.py"""
import json, re, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(f"{ROOT}/data/kanji.json"))
grade = {k: v["grade"] for k, v in d.items() if v.get("grade") and v["grade"] <= 6}

strokes, readings = {}, {}
for k in grade:
    s = open(f"{ROOT}/data/kvg/kanji/{ord(k):05x}.svg").read()
    strokes[k] = re.findall(r'<path[^>]* d="([^"]+)"', s)
    kun = [r for r in d[k]["readings_kun"] if not r.startswith("-") and not r.endswith("-")]
    on = d[k]["readings_on"]
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

qs, errs = [], []
for line in open(f"{ROOT}/src/questions.txt"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    w, r, s = line.split("|")
    if s.count("＿") != 1: errs.append(f"＿が1つでない: {line}")
    for c in s:
        if c in grade and grade[c] >= 2: errs.append(f"文に2年以上の漢字 {c}: {line}")
    for c in w:
        if re.match(r"[一-鿿]", c) and c not in strokes: errs.append(f"書き順なし {c}: {line}")
    qs.append([w, r, s])
g2 = [k for k, g in grade.items() if g == 2]
covered = set("".join(q[0] for q in qs))
missing = [k for k in g2 if k not in covered]
if missing: errs.append("問題のない2年の字: " + "".join(missing))

kana = []
for line in open(f"{ROOT}/src/kana.txt"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    kana.append(line.split("|"))

if errs:
    print("\n".join(errs)); sys.exit(1)

data = {"strokes": strokes, "read": readings, "grade": grade, "q": qs, "kana": kana}
# 共有先（GASのURL）は config.json に置く。無ければ端末だけに保存する
cfg = json.load(open(f"{ROOT}/config.json")) if os.path.exists(f"{ROOT}/config.json") else {}
body = open(f"{ROOT}/src/app.html").read()
body = body.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
body = body.replace('/*SYNC_URL*/""', json.dumps(cfg.get("sync_url", "")))
head = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
html = head + body + "\n</body></html>\n"
out = f"{ROOT}/docs"
os.makedirs(out, exist_ok=True)
open(f"{out}/index.html", "w").write(html)
open(f"{out}/.nojekyll", "w").write("")
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
print(f"ok: {len(qs)}問 / かな{len(kana)}問 / 書き順{len(strokes)}字 / {len(html)//1024}KB / 共有先 {'あり' if cfg.get('sync_url') else 'なし'} / 版 {ver}")

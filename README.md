# かんじ練習帳

小学2年生の漢字を、iPhone・iPad に指で書いて練習するWebアプリ。
1画ずつ「書き順・書く向き・だいたいの位置と形」を判定する（トメ・ハネ・ハライは見ない）。

- 公開ページ：https://kwata808-sys.github.io/kanji-renshu/
- 記録は Google スプレッドシート（`gas/Code.gs`）を通して端末どうしで共有する

## 組み立て

```bash
# 書き順データと学年表を取ってくる（初回のみ）
mkdir -p data && cd data
curl -LO https://github.com/KanjiVG/kanjivg/releases/download/r20250816/kanjivg-20250816-main.zip
unzip -q kanjivg-20250816-main.zip -d kvg
curl -LO https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji.json
# 言葉の読みの辞書（jmdict-eng-common-*.json）
curl -L -o jmdict.zip "$(curl -s https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest | python3 -c 'import sys,json;print([a["browser_download_url"] for a in json.load(sys.stdin)["assets"] if "eng-common" in a["name"] and a["name"].endswith(".json.zip")][0])')"
unzip -q jmdict.zip
cd ..
python3 build.py   # docs/ に公開用の一式ができる
```

- `src/questions.txt` 2年生の問題（文は ひらがな と 1年生の漢字だけ。build.py が検査する）
- `src/kana.txt` ひらがな・カタカナのクイズ
- `config.json` 共有先（GAS のウェブアプリURL）

## データの出典

- 書き順：[KanjiVG](https://kanjivg.tagaini.net/)（Copyright (C) Ulrich Apel, CC BY-SA 3.0）。
  `docs/index.html` に含まれる書き順データは同じ CC BY-SA 3.0 で提供する
- 学年：[kanji-data](https://github.com/davidluzgouveia/kanji-data)（MIT）
- 言葉の読み：[JMdict](https://www.edrdg.org/jmdict/j_jmdict.html)（EDRDG、CC BY-SA 4.0）を [jmdict-simplified](https://github.com/scriptin/jmdict-simplified) 経由で使用

# アフリカの夜 / HIROSHIE — Lyric Video (v2)

1920x1080 / 24fps / 3:47。ビート（136BPM）に合わせたカット割り、3DCG素材の温かい色調＋ハレーション、光のきらめき、雨、舞う光の粒、1文字ずつ浮かぶ明朝体の歌詞。

- `assets/sheets/` 受け取った素材シート、`assets/panels/` 切り出したパネル（`make_panels.py` で生成）
- `assets/lyrics.txt` 時刻付き歌詞（`0:14　歌詞` / 消える時刻を指定するなら `1:11-1:18　歌詞`）
- `timeline.py` カット割り（どのパネルを何秒から、どう動かすか）
- `render.py` レンダラー

```
python3 make_panels.py
python3 render.py                  # out/africa_no_yoru_HIROSHIE.mp4
python3 render.py --stills 20,57   # 確認用静止画
```
フォントは Ubuntu `fonts-noto-cjk` の NotoSerifCJK（Regular/Bold）を `fonts/` に置く（リポジトリには含めない）。

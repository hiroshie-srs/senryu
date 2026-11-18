# アフリカの夜 / ヒロシエ — Lyric Video

1920x1080 / 24fps / シネマスコープ風レターボックス、フィルムグレイン、ティール寄りに抑えた色調、明朝体の小さめ白文字リリック（フェード＋ブラーイン）。

- `timeline.py` … 歌詞タイミングとショット割り（カメラの始点・終点）。歌詞のズレはここの秒数を直すだけで調整可能。
- `render.py` … レンダラー（Python + Pillow + NumPy → ffmpeg）。
- `assets/` … 曲・画像素材。

```
python3 render.py                    # out/africa_no_yoru_mv.mp4
python3 render.py --stills 20,72     # 確認用の静止画
```

フォント `fonts/NotoSerifCJK-Regular.ttc` は Ubuntu の `fonts-noto-cjk` パッケージから取得（リポジトリには含めない）。

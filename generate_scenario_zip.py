"""
テキスト版シナリオ（ZIP）生成スクリプト

Windows環境で解凍時に日本語ファイル名/フォルダ名が文字化けしないよう、
ファイル名をUTF-8でエンコードし、汎用フラグのUTF-8ビット（0x800）を立てる。
Python標準のzipfileは非ASCII名に対して自動的にこの処理を行う。
"""

import os
import zipfile

# このスクリプトはリポジトリ直下から実行する想定
ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "scenario_text.zip")

# ZIPに含めるシナリオフォルダ（番号順）
INCLUDE_DIRS = [
    "000_導入",
    "001_ミドル1",
    "002_ミドル2",
    "003_ミドル3",
    "099_クライマックス",
    "100_エンディング",
    "101_報酬",
    "102_解説",
    "103_素材配布",
]

UTF8_FLAG = 0x800  # General purpose bit 11: filenames are UTF-8


def collect_files():
    paths = []
    for d in INCLUDE_DIRS:
        dir_path = os.path.join(ROOT, d)
        if not os.path.isdir(dir_path):
            print(f"警告: フォルダが見つかりません: {d}")
            continue
        for dirpath, _, filenames in os.walk(dir_path):
            for name in filenames:
                if name.lower().endswith(".txt"):
                    full = os.path.join(dirpath, name)
                    arc = os.path.relpath(full, ROOT)
                    paths.append((full, arc))
    # アーカイブ内の並びを安定させる
    paths.sort(key=lambda x: x[1])
    return paths


def build_zip():
    files = collect_files()
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, arc in files:
            # アーカイブ名は OS パス区切りを '/' に統一
            arcname = arc.replace(os.sep, "/")
            info = zipfile.ZipInfo(arcname)
            info.compress_type = zipfile.ZIP_DEFLATED
            # UTF-8フラグを明示的に立てる（Windowsでの文字化け防止）
            info.flag_bits |= UTF8_FLAG
            with open(full, "rb") as f:
                zf.writestr(info, f.read())
    print(f"生成完了: {OUTPUT}（{len(files)}ファイル）")


if __name__ == "__main__":
    build_zip()

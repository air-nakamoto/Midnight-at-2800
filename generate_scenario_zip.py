"""
テキスト版シナリオ（ZIP）生成スクリプト

Windows環境で解凍時に日本語ファイル名/フォルダ名が文字化けしないよう、
ファイル名をUTF-8でエンコードし、汎用フラグのUTF-8ビット（0x800）を立てる。
Python標準のzipfileは非ASCII名に対して自動的にこの処理を行う。

また、ZIP内に「ブラウザで開けば中の.txtを参照・編集できる」自己完結型の
HTMLツール（_テキスト編集ツール.html）を同梱する。全テキストとJSZipを
HTMLへ埋め込むため、ローカル（file://）でもオフラインで動作する。
"""

import datetime
import json
import os
import zipfile

# このスクリプトはリポジトリ直下から実行する想定
ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(ROOT, "scenario_text.zip")

# 同梱するブラウザ編集ツール関連
EDITOR_TEMPLATE = os.path.join(ROOT, "scenario_editor.template.html")
JSZIP_PATH = os.path.join(ROOT, "vendor", "jszip.min.js")
EDITOR_ARCNAME = "_テキスト編集ツール.html"

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


def build_editor_html(files):
    """全テキストとJSZipを埋め込んだ自己完結型の編集ツールHTMLを生成する。"""
    if not os.path.isfile(EDITOR_TEMPLATE):
        print(f"警告: 編集ツールのテンプレートが見つかりません: {EDITOR_TEMPLATE}")
        return None
    if not os.path.isfile(JSZIP_PATH):
        print(f"警告: JSZipが見つかりません: {JSZIP_PATH}")
        return None

    with open(EDITOR_TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    with open(JSZIP_PATH, encoding="utf-8") as f:
        jszip = f.read()

    data = {}
    for full, arc in files:
        arcname = arc.replace(os.sep, "/")
        with open(full, encoding="utf-8") as f:
            data[arcname] = f.read()
    # </script> がテキスト内にあってもHTMLが壊れないようエスケープ
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    html = template.replace("/*__JSZIP__*/", jszip)
    html = html.replace("/*__SCENARIO_DATA__*/ {}", data_json)
    html = html.replace("/*__GENERATED_AT__*/", generated_at)
    return html


def build_zip():
    files = collect_files()
    editor_html = build_editor_html(files)
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
        if editor_html is not None:
            info = zipfile.ZipInfo(EDITOR_ARCNAME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits |= UTF8_FLAG
            zf.writestr(info, editor_html.encode("utf-8"))

    extra = 1 if editor_html is not None else 0
    print(f"生成完了: {OUTPUT}（テキスト{len(files)}ファイル + ツール{extra}）")


if __name__ == "__main__":
    build_zip()

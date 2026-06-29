"""
テキスト版シナリオ（ZIP）生成スクリプト

Windows標準の「右クリック→すべて展開」(エクスプローラー内蔵ZIP) で
日本語のファイル名/フォルダ名が文字化けしないよう、ファイル名を
CP932（Shift_JIS）でエンコードし、汎用フラグのUTF-8ビット（0x800）は
立てない。

  ※経緯：以前はUTF-8名＋UTF-8フラグで格納していたが、Windowsの
    エクスプローラー内蔵ZIP展開はこのフラグを無視してシステムの
    ANSIコードページ（日本語環境ではCP932）で名前を解釈する版が多く、
    結果としてファイル名が文字化けしていた。配布対象は日本語Windows
    ユーザーのため、CP932名（フラグなし）で格納するのが最も確実。
  ※トレードオフ：CP932名は非日本語ロケールのWindowsやmacOS/Linux、
    一部の解凍ソフトでは化ける可能性がある。本ZIPは日本語Windowsでの
    エクスプローラー標準展開を最優先する。
  ※万一CP932で表現できない文字を含む名前があった場合は、その
    エントリのみ従来どおりUTF-8名＋フラグにフォールバックする。

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


class CP932ZipInfo(zipfile.ZipInfo):
    """ファイル名をCP932で格納し、UTF-8フラグ（bit 11）を立てないZipInfo。

    Windowsエクスプローラーの内蔵ZIP展開は、UTF-8フラグを無視して
    システムANSIコードページ（日本語環境ではCP932）で名前を解釈する版が
    多い。CP932名・フラグなしで格納することで、その環境でも日本語名が
    正しく表示される。CP932で表現できない名前は、安全のため従来どおり
    UTF-8名＋フラグにフォールバックする。
    """

    def _encodeFilenameFlags(self):
        try:
            return self.filename.encode("cp932"), self.flag_bits & ~UTF8_FLAG
        except UnicodeEncodeError:
            print(f"警告: CP932で表現できない名前のためUTF-8で格納します: {self.filename}")
            return self.filename.encode("utf-8"), self.flag_bits | UTF8_FLAG


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
            # CP932名・UTF-8フラグなしで格納（Windows標準解凍での文字化け防止）
            info = CP932ZipInfo(arcname)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(full, "rb") as f:
                zf.writestr(info, f.read())
        if editor_html is not None:
            info = CP932ZipInfo(EDITOR_ARCNAME)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, editor_html.encode("utf-8"))

    extra = 1 if editor_html is not None else 0
    print(f"生成完了: {OUTPUT}（テキスト{len(files)}ファイル + ツール{extra}）")


if __name__ == "__main__":
    build_zip()

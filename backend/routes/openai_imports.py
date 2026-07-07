"""
OpenAI 用量/名單手動上傳。一次可多檔，依檔名分類：
  users*.xlsx      -> 名單
  codex*.csv       -> Codex
  leaderboard*.csv -> 網頁版（日期從檔名 YYYY-MM-DD 抓）
檔名不符規則者，整批擋下並回報，請改名重傳。
openai_import / openai_process 為專案根目錄的 top-level module。
"""
from flask import Blueprint, jsonify, request
import re, os, tempfile
from pathlib import Path

from ..importers.openai_import import parse_codex_csv, parse_web_csv, import_roster_xlsx, extract_date_from_filename
from ..importers.openai_process import init_db, import_codex_daily, import_web_daily

openai_imports_bp = Blueprint("openai_imports", __name__)

HINT = "檔名規則：users*.xlsx（名單）、codex*.csv（Codex）、leaderboard*.csv（網頁版，需含日期如 leaderboard-2026-06-22.csv）"


def classify_upload(filename: str) -> str:
    """依使用者定的規則嚴格分類；不符回 'unknown'。"""
    n = (filename or "").lower()
    if re.match(r"^users.*\.xlsx?$", n):
        return "roster"
    if re.match(r"^codex.*\.csv$", n):
        return "codex"
    if re.match(r"^leaderboard.*\.csv$", n):
        return "web"
    return "unknown"


@openai_imports_bp.route("/api/openai/import", methods=["POST"])
def import_openai():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "沒有收到檔案"}), 400

    # 先驗證全部檔名，有一個不對就整批擋下
    bad = []
    for f in files:
        kind = classify_upload(f.filename)
        if kind == "unknown":
            bad.append(f.filename)
        elif kind == "web" and not extract_date_from_filename(Path(f.filename)):
            bad.append(f.filename)   # 網頁版但檔名沒日期
    if bad:
        return jsonify({"error": "以下檔名不符規則，請改名後重傳", "bad_files": bad, "hint": HINT}), 400

    init_db()

    # 名單先處理（母體要先進），再 codex，再 web
    order = {"roster": 0, "codex": 1, "web": 2}
    files.sort(key=lambda f: order[classify_upload(f.filename)])

    results = []
    for f in files:
        kind = classify_upload(f.filename)
        suffix = Path(f.filename).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            f.save(tmp.name)
            tmp.close()
            p = Path(tmp.name)
            if kind == "roster":
                r = import_roster_xlsx(p)
                results.append({"file": f.filename, "type": "名單", **r})
            elif kind == "codex":
                r = import_codex_daily(parse_codex_csv(p))
                results.append({"file": f.filename, "type": "Codex", **r})
            else:  # web —— 日期一定從「原始檔名」抓，不是暫存檔名
                date = extract_date_from_filename(Path(f.filename))
                r = import_web_daily(parse_web_csv(p, date))
                results.append({"file": f.filename, "type": f"網頁版 {date}", **r})
        except Exception as e:
            results.append({"file": f.filename, "error": str(e)})
        finally:
            os.unlink(tmp.name)

    return jsonify({"success": True, "results": results})

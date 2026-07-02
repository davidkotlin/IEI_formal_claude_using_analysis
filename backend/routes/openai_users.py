"""
名單 CRUD API（sidebar 的匯入/名單管理）。
寫入走 openai_process 的原生 sqlite3 CRUD（與 importer 同一套），
維持你「寫用 raw、讀用 ORM」的原則。
openai_process 為專案根目錄的 top-level module（與 openai_import.py 同層）。
"""
from flask import Blueprint, jsonify, request
import openai_process as op

openai_users_bp = Blueprint("openai_users", __name__)


@openai_users_bp.route("/api/openai/users", methods=["GET"])
def list_users():
    return jsonify({"data": op.get_all_users()})


@openai_users_bp.route("/api/openai/users", methods=["POST"])
def create_user():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip()
    if not email:
        return jsonify({"error": "email 必填"}), 400
    ok = op.add_user(
        email,
        body.get("name", ""),
        body.get("user_id"),
        int(body.get("active", 1)),
    )
    if not ok:
        return jsonify({"error": "email 已存在"}), 409
    return jsonify({"ok": True}), 201


@openai_users_bp.route("/api/openai/users/<email>", methods=["PUT"])
def update_user(email):
    body = request.get_json(silent=True) or {}
    ok = op.update_user(email, name=body.get("name"), active=body.get("active"))
    if not ok:
        return jsonify({"error": "查無此人或無可更新欄位"}), 404
    return jsonify({"ok": True})


@openai_users_bp.route("/api/openai/users/<email>", methods=["DELETE"])
def delete_user(email):
    cascade = request.args.get("cascade") == "1"   # 連用量一起刪
    ok = op.delete_user(email, cascade=cascade)
    if not ok:
        return jsonify({"error": "查無此人"}), 404
    return jsonify({"ok": True})

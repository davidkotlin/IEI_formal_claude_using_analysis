from flask import Blueprint, jsonify, request
from ..importers.claude_process import import_from_bytes, init_db

imports_bp = Blueprint("imports", __name__)


@imports_bp.route("/api/import", methods=["POST"])
def import_data():
    # group 從 form 取（POST 上傳），必填、只接受 1/2/3
    raw_group = request.form.get("group")
    if raw_group not in ("1", "2", "3"):
        return jsonify({"error": "group 必須是 1 / 2 / 3"}), 400
    group = int(raw_group)

    if "users" not in request.files or "conversations" not in request.files:
        return jsonify({"error": "請同時上傳 users.json 與 conversations.json"}), 400

    users_bytes = request.files["users"].read()
    conv_bytes  = request.files["conversations"].read()

    try:
        init_db()
        result = import_from_bytes(users_bytes, conv_bytes, group)

        # 防呆拒絕（疑似匯錯組）→ 回 409，帶訊息與符合率
        if not result.get("ok", True):
            return jsonify({
                "success": False,
                "error": result["message"],
                "group": result["group"],
                "match_rate": result["match_rate"],
                "existing_roster": result.get("existing_roster"),
                "incoming": result.get("incoming"),
            }), 409

        return jsonify({
            "success": True,
            "group":                result["group"],
            "first_import":         result["first_import"],
            "match_rate":           result["match_rate"],
            "users_excluded":       result["users_excluded"],
            "conv_inserted":        result["conv_inserted"],
            "conv_skipped_dup":     result["conv_skipped_dup"],
            "conv_skipped_unknown": result["conv_skipped_unknown"],
            "conv_skipped_weekend": result["conv_skipped_weekend"],
            "conv_skipped_empty":   result["conv_skipped_empty"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

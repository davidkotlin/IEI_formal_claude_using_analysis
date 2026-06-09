from flask import Blueprint, jsonify, request
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from db_process import import_from_bytes, init_db

imports_bp = Blueprint("imports", __name__)


@imports_bp.route("/api/import", methods=["POST"])
def import_data():
    if "users" not in request.files or "conversations" not in request.files:
        return jsonify({"error": "請同時上傳 users.json 與 conversations.json"}), 400

    users_bytes = request.files["users"].read()
    conv_bytes  = request.files["conversations"].read()

    try:
        init_db()
        result = import_from_bytes(users_bytes, conv_bytes)
        return jsonify({
            "success": True,
            "conv_inserted":        result["conv_inserted"],
            "conv_skipped_dup":     result["conv_skipped_dup"],
            "conv_skipped_unknown": result["conv_skipped_unknown"],
            "conv_skipped_weekend": result["conv_skipped_weekend"],
            "conv_skipped_empty":   result["conv_skipped_empty"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

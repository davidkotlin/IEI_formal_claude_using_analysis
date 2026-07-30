from flask import Blueprint, jsonify, request
from ..services.analytics import get_all_users, get_inactive_split
from ..importers.claude_process import update_user_name, delete_user_cascade, update_user_department

users_bp = Blueprint("users", __name__)


def _parse_group(req):
    raw = req.args.get("group")
    if raw not in ("1", "2", "3"):
        return None, (jsonify({"error": "group 必須是 1 / 2 / 3"}), 400)
    return int(raw), None


@users_bp.route("/api/users", methods=["GET"])
def list_users():
    group, err = _parse_group(request)
    if err:
        return err
    users = get_all_users(group)   # [{uuid, name, email}]
    return jsonify({
        "total": len(users),
        "users": users,            # 回傳完整物件（uuid 當身份、name 供顯示）
    })


@users_bp.route("/api/users/inactive", methods=["GET"])
def inactive_users():
    group, err = _parse_group(request)
    if err:
        return err
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    if not start_date or not end_date:
        return jsonify({"error": "請指定日期範圍（start_date 與 end_date）"}), 400
    inactive_str  = request.args.get("users", "")
    users      = [u.strip() for u in inactive_str.split(",") if u.strip()] if inactive_str else None

    split = get_inactive_split(start_date, end_date, users, group)
    return jsonify({
        "count": len(split["inactive"]),
        "inactive": split["inactive"],
        "independent": split["independent"],   # 獨立區：json 漏抓、後台顯示有活動
        "csv_window": split["csv_window"],      # CSV 涵蓋窗口（顯示用），沒上傳過 CSV 為 null
    })


@users_bp.route("/api/users/<uuid>", methods=["PUT"])
def rename_user(uuid):
    """改名：body 帶 full_name，query 帶 group。"""
    group, err = _parse_group(request)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    full_name = (body.get("full_name") or "").strip()
    if not full_name:
        return jsonify({"error": "full_name 不可為空"}), 400
    ok = update_user_name(uuid, full_name, group)
    if not ok:
        return jsonify({"error": "找不到該用戶（uuid 或 group 不符）"}), 404
    return jsonify({"success": True, "uuid": uuid, "full_name": full_name})


@users_bp.route("/api/users/<uuid>/department", methods=["PUT"])
def set_department(uuid):
    """手動改單筆部門：body 帶 department（空字串=清空），query 帶 group。"""
    group, err = _parse_group(request)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    department = (body.get("department") or "").strip()
    ok = update_user_department(uuid, department, group)
    if not ok:
        return jsonify({"error": "找不到該用戶（uuid 或 group 不符）"}), 404
    return jsonify({"success": True, "uuid": uuid, "department": department})


@users_bp.route("/api/users/<uuid>", methods=["DELETE"])
def remove_user(uuid):
    """級聯全刪：刪這人在該組的 messages/conversations/user。query 帶 group。"""
    group, err = _parse_group(request)
    if err:
        return err
    result = delete_user_cascade(uuid, group)
    if result["user_deleted"] == 0:
        return jsonify({"error": "找不到該用戶（uuid 或 group 不符）"}), 404
    return jsonify({"success": True, "uuid": uuid, **result})

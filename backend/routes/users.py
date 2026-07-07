from flask import Blueprint, jsonify, request
from ..services.analytics import get_all_users, get_inactive_users

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
    users = get_all_users(group)
    return jsonify({
        "total": len(users),
        "users": [u["full_name"] for u in users]
    })


@users_bp.route("/api/users/inactive", methods=["GET"])
def inactive_users():
    group, err = _parse_group(request)
    if err:
        return err
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users_str  = request.args.get("users", "")
    users      = [u.strip() for u in users_str.split(",") if u.strip()] if users_str else None

    inactive = get_inactive_users(start_date, end_date, users, group)
    return jsonify({
        "count": len(inactive),
        "inactive": inactive
    })

from flask import Blueprint, jsonify, request
from ..services.analytics import get_summary, get_ranking, get_hourly

stats_bp = Blueprint("stats", __name__)


def _parse_users(users_str):
    return [u.strip() for u in users_str.split(",") if u.strip()] if users_str else None


def _parse_group(req):
    """取 group（1/2/3）。必填、且只接受 1/2/3，否則回 (None, 錯誤回應)。"""
    raw = req.args.get("group")
    if raw not in ("1", "2", "3"):
        return None, (jsonify({"error": "group 必須是 1 / 2 / 3"}), 400)
    return int(raw), None


@stats_bp.route("/api/stats/summary", methods=["GET"])
def summary():
    group, err = _parse_group(request)
    if err:
        return err
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users      = _parse_users(request.args.get("users", ""))

    return jsonify(get_summary(start_date, end_date, users, group))


@stats_bp.route("/api/stats/ranking", methods=["GET"])
def ranking():
    group, err = _parse_group(request)
    if err:
        return err
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users      = _parse_users(request.args.get("users", ""))
    metric     = request.args.get("metric", "messages")

    if metric not in ("messages", "duration", "tools"):
        return jsonify({"error": "metric 必須是 messages / duration / tools"}), 400

    return jsonify({
        "metric": metric,
        "data": get_ranking(metric, start_date, end_date, users, group)
    })


@stats_bp.route("/api/stats/hourly", methods=["GET"])
def hourly():
    group, err = _parse_group(request)
    if err:
        return err
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users      = _parse_users(request.args.get("users", ""))

    return jsonify({
        "data": get_hourly(start_date, end_date, users, group)
    })

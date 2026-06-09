from flask import Blueprint, jsonify, request
from ..services.analytics import get_summary, get_ranking, get_hourly

stats_bp = Blueprint("stats", __name__)


def _parse_users(users_str):
    return [u.strip() for u in users_str.split(",") if u.strip()] if users_str else None


@stats_bp.route("/api/stats/summary", methods=["GET"])
def summary():
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users      = _parse_users(request.args.get("users", ""))

    return jsonify(get_summary(start_date, end_date, users))


@stats_bp.route("/api/stats/ranking", methods=["GET"])
def ranking():
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users      = _parse_users(request.args.get("users", ""))
    metric     = request.args.get("metric", "messages")

    if metric not in ("messages", "duration", "tools"):
        return jsonify({"error": "metric 必須是 messages / duration / tools"}), 400

    return jsonify({
        "metric": metric,
        "data": get_ranking(metric, start_date, end_date, users)
    })


@stats_bp.route("/api/stats/hourly", methods=["GET"])
def hourly():
    start_date = request.args.get("start_date")
    end_date   = request.args.get("end_date")
    users      = _parse_users(request.args.get("users", ""))

    return jsonify({
        "data": get_hourly(start_date, end_date, users)
    })

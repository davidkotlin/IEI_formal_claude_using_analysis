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


def _require_dates(req):
    """效能守衛：start_date 與 end_date 必填，否則回 (None, None, 錯誤回應)。
    避免資料累積後，未指定時間範圍就對全量下查詢。"""
    start_date = req.args.get("start_date")
    end_date   = req.args.get("end_date")
    if not start_date or not end_date:
        return None, None, (jsonify({"error": "請指定日期範圍（start_date 與 end_date）"}), 400)
    return start_date, end_date, None


@stats_bp.route("/api/stats/summary", methods=["GET"])
def summary():
    group, err = _parse_group(request)
    if err:
        return err
    start_date, end_date, derr = _require_dates(request)
    if derr:
        return derr
    users = _parse_users(request.args.get("users", ""))

    return jsonify(get_summary(start_date, end_date, users, group))


@stats_bp.route("/api/stats/ranking", methods=["GET"])
def ranking():
    group, err = _parse_group(request)
    if err:
        return err
    start_date, end_date, derr = _require_dates(request)
    if derr:
        return derr
    users  = _parse_users(request.args.get("users", ""))
    metric = request.args.get("metric", "messages")

    if metric not in ("messages", "duration", "tools", "conversations"):
        return jsonify({"error": "metric 必須是 messages / duration / tools / conversations"}), 400

    return jsonify({
        "metric": metric,
        "data": get_ranking(metric, start_date, end_date, users, group)
    })


@stats_bp.route("/api/stats/hourly", methods=["GET"])
def hourly():
    group, err = _parse_group(request)
    if err:
        return err
    start_date, end_date, derr = _require_dates(request)
    if derr:
        return derr
    users = _parse_users(request.args.get("users", ""))

    return jsonify({
        "data": get_hourly(start_date, end_date, users, group)
    })

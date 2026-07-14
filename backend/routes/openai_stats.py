from flask import Blueprint, jsonify, request
from ..services.openai_analytics import (
    get_summary, get_ranking, get_inactive_users, get_matrix, valid_metric,
)

openai_stats_bp = Blueprint("openai_stats", __name__)


def _parse_emails(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


def _common():
    """抽出共用參數並做基本驗證，回傳 (params, error_response)。"""
    source = request.args.get("source", "codex")
    if source not in ("codex", "web"):
        return None, (jsonify({"error": "source 必須是 codex / web"}), 400)
    default_metric = "codex_total" if source == "codex" else "web_tokens"
    metric = request.args.get("metric", default_metric)
    if not valid_metric(source, metric):
        return None, (jsonify({"error": "metric 不適用於此 source"}), 400)
    # 效能守衛：日期必填（避免資料累積後對全量下查詢）
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if not start_date or not end_date:
        return None, (jsonify({"error": "請指定日期範圍（start_date 與 end_date）"}), 400)
    return {
        "source": source,
        "metric": metric,
        "start_date": start_date,
        "end_date": end_date,
        "emails": _parse_emails(request.args.get("emails", "")),
    }, None


@openai_stats_bp.route("/api/openai/stats/summary", methods=["GET"])
def summary():
    p, err = _common()
    if err:
        return err
    return jsonify(get_summary(p["source"], p["metric"], p["start_date"], p["end_date"], p["emails"]))


@openai_stats_bp.route("/api/openai/stats/ranking", methods=["GET"])
def ranking():
    p, err = _common()
    if err:
        return err
    return jsonify({
        "source": p["source"], "metric": p["metric"],
        "data": get_ranking(p["source"], p["metric"], p["start_date"], p["end_date"], p["emails"]),
    })


@openai_stats_bp.route("/api/openai/stats/inactive", methods=["GET"])
def inactive():
    source = request.args.get("source", "codex")
    if source not in ("codex", "web", "both"):
        return jsonify({"error": "source 必須是 codex / web / both"}), 400
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if not start_date or not end_date:
        return jsonify({"error": "請指定日期範圍（start_date 與 end_date）"}), 400
    emails = _parse_emails(request.args.get("emails", ""))
    return jsonify({
        "source": source,
        "data": get_inactive_users(source, start_date, end_date, emails),
    })


@openai_stats_bp.route("/api/openai/stats/matrix", methods=["GET"])
def matrix():
    p, err = _common()
    if err:
        return err
    return jsonify(get_matrix(p["source"], p["metric"], p["start_date"], p["end_date"], p["emails"]))

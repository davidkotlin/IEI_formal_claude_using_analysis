from statistics import mean, median, multimode
from collections import defaultdict

from ..models import db
from ..models.openai_user import OpenAIUser
from ..models.codex_daily import CodexDaily
from ..models.web_daily import WebDaily

# 每個來源可用的 metric。Codex 的 cached / uncached 刻意分開，不混成單一 total。
CODEX_METRICS = ("codex_total", "uncached", "cached", "output", "sessions", "messages")
WEB_METRICS = ("web_tokens",)


def valid_metric(source: str, metric: str) -> bool:
    return metric in (CODEX_METRICS if source == "codex" else WEB_METRICS)


def _cell_value(row, metric: str) -> int:
    """把一列每日用量依 metric 取出單一數值。"""
    if metric == "codex_total":
        return (row.uncached_input or 0) + (row.cached_input or 0) + (row.output or 0)
    if metric == "uncached":
        return row.uncached_input or 0
    if metric == "cached":
        return row.cached_input or 0
    if metric == "output":
        return row.output or 0
    if metric == "sessions":
        return row.n_sessions or 0
    if metric == "messages":
        return row.n_messages or 0
    if metric == "web_tokens":
        return row.tokens or 0
    return 0


def _daily_rows(source, start_date, end_date, emails):
    """
    取區間內、active 使用者的每日用量列。
    回傳 list of (每日用量物件, 使用者姓名)。
    只有「有用過」的人才會有列，這是 active / inactive 判斷的來源。
    """
    Model = CodexDaily if source == "codex" else WebDaily
    q = (db.session.query(Model, OpenAIUser.name)
         .join(OpenAIUser, Model.email == OpenAIUser.email)
         .filter(OpenAIUser.active == 1))
    if start_date:
        q = q.filter(Model.date >= start_date)
    if end_date:
        q = q.filter(Model.date <= end_date)
    if emails:
        q = q.filter(Model.email.in_(emails))
    return q.all()


def _roster(emails):
    """母體：active 名單（受 emails 篩選影響）。"""
    q = db.session.query(OpenAIUser).filter(OpenAIUser.active == 1)
    if emails:
        q = q.filter(OpenAIUser.email.in_(emails))
    return q.order_by(OpenAIUser.email).all()


def _per_user_totals(rows, metric):
    """把每日列彙總成每人總量。回傳 (totals: {email: 總量}, names: {email: 姓名})。"""
    totals = defaultdict(int)
    names = {}
    for obj, name in rows:
        totals[obj.email] += _cell_value(obj, metric)
        names[obj.email] = name
    return totals, names


# ---------------------------------------------------------------------------
# 對外：對應前端三個區塊 + sidebar
# ---------------------------------------------------------------------------

def get_all_users():
    """sidebar 帳號篩選用；也可當 CRUD 讀取（唯讀走 ORM）。"""
    users = db.session.query(OpenAIUser).order_by(OpenAIUser.name).all()
    return [{"email": u.email, "name": u.name, "active": u.active} for u in users]


def get_summary(source, metric, start_date, end_date, emails):
    """
    區塊1：多少 % 的人在用（真實比例 + 百分比），以及每人用量的平均/中位/眾數。
    集中趨勢只計「有用過的人」，避免大量 0 把平均與眾數拉垮。
    """
    roster = _roster(emails)
    total_users = len(roster)

    rows = _daily_rows(source, start_date, end_date, emails)
    totals, _ = _per_user_totals(rows, metric)

    active_count = len(totals)
    active_pct = round(active_count / total_users * 100, 1) if total_users else 0

    vals = list(totals.values())
    if vals:
        token = {
            "mean": round(mean(vals), 1),
            "median": round(median(vals), 1),
            "mode": int(max(multimode(vals))),
        }
    else:
        token = {"mean": 0, "median": 0, "mode": 0}

    return {
        "source": source,
        "metric": metric,
        "active_users": active_count,   # 真實比例的分子
        "total_users": total_users,     # 真實比例的分母
        "active_pct": active_pct,       # 百分比
        "token": token,
    }


def get_ranking(source, metric, start_date, end_date, emails):
    """區塊2：長條圖，有用的人依 metric 由高到低。"""
    rows = _daily_rows(source, start_date, end_date, emails)
    totals, names = _per_user_totals(rows, metric)
    result = [{"email": e, "name": names[e], "value": v} for e, v in totals.items()]
    result.sort(key=lambda x: x["value"], reverse=True)
    return result


def _lifetime_tokens(emails):
    """
    一次算出每個人「全時段（不分日期）」的 codex 總 token 與 web 總 token。
    回傳對照表：{ email: {"codex": codex總token, "web": web總token} }
    codex_total = uncached + cached + output；web = tokens。只查兩次（各來源一次 group by）。
    """
    from sqlalchemy import func
    table = defaultdict(lambda: {"codex": 0, "web": 0})

    # codex 全時段
    cq = db.session.query(
            CodexDaily.email,
            func.coalesce(func.sum(CodexDaily.uncached_input), 0),
            func.coalesce(func.sum(CodexDaily.cached_input), 0),
            func.coalesce(func.sum(CodexDaily.output), 0),
         )
    if emails:
        cq = cq.filter(CodexDaily.email.in_(emails))
    for email, unc, cac, out in cq.group_by(CodexDaily.email).all():
        table[email]["codex"] = int((unc or 0) + (cac or 0) + (out or 0))

    # web 全時段
    wq = db.session.query(
            WebDaily.email,
            func.coalesce(func.sum(WebDaily.tokens), 0),
         )
    if emails:
        wq = wq.filter(WebDaily.email.in_(emails))
    for email, tok in wq.group_by(WebDaily.email).all():
        table[email]["web"] = int(tok or 0)

    return table


def get_inactive_users(source, start_date, end_date, emails):
    """
    區塊2 的切換：區間內完全沒用的人。
    source='codex'/'web' → 該來源沒用；source='both' → 兩個來源都沒用。
    每人附全時段 codex / web 總 token（供 hover 判斷是否死號）。
    """
    if source == "both":
        codex_used = {obj.email for obj, _ in _daily_rows("codex", start_date, end_date, emails)}
        web_used = {obj.email for obj, _ in _daily_rows("web", start_date, end_date, emails)}
        used = codex_used | web_used          # 用過任一個
    else:
        used = {obj.email for obj, _ in _daily_rows(source, start_date, end_date, emails)}

    lifetime = _lifetime_tokens(emails)
    empty = {"codex": 0, "web": 0}

    return [
        {
            "email": u.email,
            "name": u.name,
            "lifetime": lifetime.get(u.email, empty),   # 全時段 codex / web 總 token
        }
        for u in _roster(emails)
        if u.email not in used                 # 不在「用過」裡的 = 沒用（both 時＝兩個都沒用）
    ]


def get_matrix(source, metric, start_date, end_date, emails):
    """
    區塊3：逐日矩陣，只放有用過的人。
    dates 只含資料裡真的出現的日期（不硬塞沒資料的日子）；
    cells 對齊 dates，null = 那天沒用。
    """
    rows = _daily_rows(source, start_date, end_date, emails)

    date_set = set()
    cell = defaultdict(dict)   # email -> {date: value}
    names = {}
    for obj, name in rows:
        cell[obj.email][obj.date] = _cell_value(obj, metric)
        date_set.add(obj.date)
        names[obj.email] = name

    dates = sorted(date_set)
    result_rows = []
    for email, dmap in cell.items():
        cells = [dmap.get(d) for d in dates]   # 缺的日子為 None
        total = sum(v for v in cells if v is not None)
        result_rows.append({
            "email": email,
            "name": names[email],
            "cells": cells,
            "total": total,
        })
    result_rows.sort(key=lambda r: r["total"], reverse=True)

    return {"source": source, "metric": metric, "dates": dates, "rows": result_rows}

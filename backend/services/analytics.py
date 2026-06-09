from statistics import median, mode, mean, multimode
from collections import defaultdict
from ..models import db
from ..models.user import User
from ..models.conversation import Conversation


def _base_query(start_date, end_date, users):
    """建立基礎查詢，套用日期與用戶篩選"""
    q = db.session.query(Conversation).join(User)
    if start_date:
        q = q.filter(Conversation.date >= start_date)
    if end_date:
        q = q.filter(Conversation.date <= end_date)
    if users:
        q = q.filter(User.full_name.in_(users))
    return q


def get_all_users():
    """取得所有用戶名單"""
    users = db.session.query(User).order_by(User.full_name).all()
    return [{"uuid": u.uuid, "full_name": u.full_name, "email": u.email} for u in users]


def get_inactive_users(start_date, end_date, users):
    """取得未使用者名單"""
    active = {
        row.full_name
        for row in _base_query(start_date, end_date, users).with_entities(User.full_name).all()
    }
    selected = set(users) if users else {u["full_name"] for u in get_all_users()}
    return sorted(selected - active)


def get_summary(start_date, end_date, users):
    """計算區間總結指標"""
    total_users = db.session.query(User).count()
    convs = _base_query(start_date, end_date, users).all()

    if not convs:
        return {
            "active_users": 0,
            "total_users": total_users,
            "active_pct": 0,
            "rounds": {"mean": 0, "median": 0, "mode": 0},
            "duration_median": 0,
        }

    # 活躍人數
    active_names = {c.user.full_name for c in convs}
    active_count = len(active_names)
    active_pct = round(active_count / total_users * 100, 1) if total_users else 0

    # 對話來回數：以人為單位加總後再統計
    user_totals = defaultdict(int)
    for c in convs:
        user_totals[c.user.full_name] += c.total_messages
    totals = list(user_totals.values())

    rounds_mean   = round(mean(totals), 1) if totals else 0
    rounds_median = round(median(totals), 1) if totals else 0
    modes = multimode(totals)
    rounds_mode   = int(max(modes)) if modes else 0

    # 時長中位數
    durations = [c.duration_min for c in convs if c.duration_min is not None]
    duration_median = round(median(durations), 1) if durations else 0

    return {
        "active_users": active_count,
        "total_users": total_users,
        "active_pct": active_pct,
        "rounds": {
            "mean": rounds_mean,
            "median": rounds_median,
            "mode": rounds_mode,
        },
        "duration_median": duration_median,
    }


def get_ranking(metric, start_date, end_date, users):
    """計算各人排名"""
    convs = _base_query(start_date, end_date, users).all()

    user_data = defaultdict(list)
    for c in convs:
        name = c.user.full_name
        if metric == "messages":
            user_data[name].append(c.total_messages)
        elif metric == "duration":
            if c.duration_min is not None:
                user_data[name].append(c.duration_min)
        elif metric == "tools":
            user_data[name].append(c.tool_use_count or 0)

    result = []
    for name, values in user_data.items():
        if metric == "duration":
            value = round(median(values), 1) if values else 0
        else:
            value = sum(values)
        result.append({"name": name, "value": value})

    result.sort(key=lambda x: x["value"], reverse=True)
    return result


def get_hourly(start_date, end_date, users):
    """計算時段分析（只回傳有資料的人）"""
    convs = _base_query(start_date, end_date, users).all()

    # 只統計有對話的人
    user_hours = defaultdict(lambda: [0] * 24)
    for c in convs:
        name = c.user.full_name
        if c.hour is not None:
            user_hours[name][c.hour] += 1

    return [
        {"name": name, "hours": hours}
        for name, hours in sorted(user_hours.items())
    ]

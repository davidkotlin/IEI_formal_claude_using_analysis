from statistics import median, mode, mean, multimode
from collections import defaultdict
from ..models import db
from ..models.user import User
from ..models.conversation import Conversation
from ..models.message import Message


def _conv_query(start_date, end_date, users, group):
    """對話層級的基礎查詢（用於取得對話清單）"""
    q = db.session.query(Conversation).join(User)
    q = q.filter(Conversation.group_id == group)          # 只看這一組
    if start_date:
        q = q.filter(Conversation.date >= start_date)
    if end_date:
        q = q.filter(Conversation.date <= end_date)
    if users:
        q = q.filter(User.full_name.in_(users))
    return q


def _msg_query(start_date, end_date, users, group):
    """訊息層級的基礎查詢（用於準確計算訊息數、工具數、時長）"""
    q = (db.session.query(Message)
         .join(Conversation, Message.conversation_uuid == Conversation.uuid)
         .join(User, Conversation.user_uuid == User.uuid))
    q = q.filter(Conversation.group_id == group)          # 只看這一組
    if start_date:
        q = q.filter(Message.date >= start_date)
    if end_date:
        q = q.filter(Message.date <= end_date)
    if users:
        q = q.filter(User.full_name.in_(users))
    return q


def get_all_users(group):
    users = (db.session.query(User)
             .filter(User.group_id == group)          # 這組的名單
             .order_by(User.full_name).all())
    return [{"uuid": u.uuid, "full_name": u.full_name, "email": u.email} for u in users]


def get_inactive_users(start_date, end_date, users, group):
    active = {
        row.full_name
        for row in _msg_query(start_date, end_date, users, group)
        .with_entities(User.full_name).distinct().all()
    }
    selected = set(users) if users else {u["full_name"] for u in get_all_users(group)}
    return sorted(selected - active)


def get_summary(start_date, end_date, users, group):
    total_users = db.session.query(User).filter(User.group_id == group).count()
    msgs = _msg_query(start_date, end_date, users, group).all()

    if not msgs:
        return {
            "active_users": 0,
            "total_users": total_users,
            "active_pct": 0,
            "rounds": {"mean": 0, "median": 0, "mode": 0},
            "duration_mean": 0,
        }

    # 活躍人數（有訊息的人）
    active_names = set()
    for m in msgs:
        active_names.add(m.conversation.user.full_name)
    active_count = len(active_names)
    active_pct = round(active_count / total_users * 100, 1) if total_users else 0

    # 對話來回數：以人為單位，只算 human 訊息，在篩選時間內
    user_msg_totals = defaultdict(int)
    for m in msgs:
        if m.sender == "human":
            user_msg_totals[m.conversation.user.full_name] += 1
    totals = list(user_msg_totals.values())

    rounds_mean   = round(mean(totals), 1) if totals else 0
    rounds_median = round(median(totals), 1) if totals else 0
    modes = multimode(totals)
    rounds_mode   = int(max(modes)) if modes else 0

    # 每次對話時長：只取篩選時間內有訊息的對話，算首尾訊息時間差
    conv_durations = defaultdict(list)
    for m in msgs:
        conv_durations[m.conversation_uuid].append(m.created_at_tw)

    durations = []
    for times in conv_durations.values():
        sorted_times = sorted(times)
        if len(sorted_times) >= 2:
            t_first = sorted_times[0]
            t_last = sorted_times[-1]
            from datetime import datetime
            fmt = "%Y-%m-%d %H:%M:%S"
            diff = (datetime.strptime(t_last, fmt) - datetime.strptime(t_first, fmt)).total_seconds() / 60
            durations.append(round(diff, 1))

    duration_mean = round(mean(durations), 1) if durations else 0

    return {
        "active_users": active_count,
        "total_users": total_users,
        "active_pct": active_pct,
        "rounds": {
            "mean": rounds_mean,
            "median": rounds_median,
            "mode": rounds_mode,
        },
        "duration_mean": duration_mean,
    }


def get_ranking(metric, start_date, end_date, users, group):
    msgs = _msg_query(start_date, end_date, users, group).all()

    user_data = defaultdict(list)
    for m in msgs:
        name = m.conversation.user.full_name
        if metric == "messages":
            if m.sender == "human":
                user_data[name].append(1)
        elif metric == "duration":
            user_data[name].append(m.created_at_tw)
        elif metric == "tools":
            user_data[name].append(m.tool_use_count or 0)

    result = []
    if metric == "duration":
        # 每人的對話時長平均
        from datetime import datetime
        fmt = "%Y-%m-%d %H:%M:%S"
        conv_user = defaultdict(lambda: defaultdict(list))
        for m in msgs:
            name = m.conversation.user.full_name
            conv_user[name][m.conversation_uuid].append(m.created_at_tw)
        for name, convs in conv_user.items():
            durs = []
            for times in convs.values():
                sorted_times = sorted(times)
                if len(sorted_times) >= 2:
                    diff = (datetime.strptime(sorted_times[-1], fmt) -
                            datetime.strptime(sorted_times[0], fmt)).total_seconds() / 60
                    durs.append(round(diff, 1))
            value = round(mean(durs), 1) if durs else 0
            result.append({"name": name, "value": value})
    else:
        for name, values in user_data.items():
            result.append({"name": name, "value": sum(values)})

    result.sort(key=lambda x: x["value"], reverse=True)
    return result


def get_hourly(start_date, end_date, users, group):
    msgs = _msg_query(start_date, end_date, users, group).all()

    user_hours = defaultdict(lambda: [0] * 24)
    seen = defaultdict(set)  # 同一對話同一小時只算一次

    for m in msgs:
        name = m.conversation.user.full_name
        key = (m.conversation_uuid, m.hour)
        if key not in seen[name]:
            seen[name].add(key)
            if m.hour is not None:
                user_hours[name][m.hour] += 1

    return [
        {"name": name, "hours": hours}
        for name, hours in sorted(user_hours.items())
    ]

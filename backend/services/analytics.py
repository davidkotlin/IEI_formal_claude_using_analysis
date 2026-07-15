from statistics import median, mode, mean, multimode
from collections import defaultdict
from ..models import db
from ..models.user import User
from ..models.conversation import Conversation
from ..models.message import Message


def _display_name(user):
    """顯示名：full_name 有值就用，否則用 email @ 前綴（供人判讀，不作為身份）。"""
    fn = (user.full_name or "").strip()
    if fn:
        return fn
    email = (user.email or "").strip()
    return email.split("@")[0] if email else user.uuid


def _conv_query(start_date, end_date, users, group):
    """對話層級的基礎查詢。users = uuid 清單。"""
    q = db.session.query(Conversation).join(User)
    q = q.filter(Conversation.group_id == group)          # 只看這一組
    if start_date:
        q = q.filter(Conversation.date >= start_date)
    if end_date:
        q = q.filter(Conversation.date <= end_date)
    if users:
        q = q.filter(User.uuid.in_(users))                # 用 uuid 篩選（唯一，不怕空名/重名）
    return q


def _msg_query(start_date, end_date, users, group):
    """訊息層級的基礎查詢。users = uuid 清單。"""
    q = (db.session.query(Message)
         .join(Conversation, Message.conversation_uuid == Conversation.uuid)
         .join(User, Conversation.user_uuid == User.uuid))
    q = q.filter(Conversation.group_id == group)          # 只看這一組
    if start_date:
        q = q.filter(Message.date >= start_date)
    if end_date:
        q = q.filter(Message.date <= end_date)
    if users:
        q = q.filter(User.uuid.in_(users))                # 用 uuid 篩選
    return q


def get_all_users(group):
    users = (db.session.query(User)
             .filter(User.group_id == group)
             .order_by(User.full_name).all())
    return [{"uuid": u.uuid, "name": _display_name(u), "email": u.email,
             "department": u.department} for u in users]


def _lifetime_stats(group):
    """
    一次算出這組「每個人全時段（不分日期）」的累積用量，回傳對照表：
      { uuid: {"conversations": 對話數, "duration_min": 總時長, "tool_use": 工具數} }
    只查一次 db（group by uuid），未使用者直接查表取值，不逐人查詢。
    """
    from sqlalchemy import func
    rows = (db.session.query(
                Conversation.user_uuid,
                func.count(Conversation.uuid),                 # 對話數
                func.coalesce(func.sum(Conversation.duration_min), 0.0),  # 總時長
                func.coalesce(func.sum(Conversation.tool_use_count), 0),  # 工具數
            )
            .filter(Conversation.group_id == group)
            .group_by(Conversation.user_uuid)
            .all())
    table = {}
    for uid, conv_cnt, dur_sum, tool_sum in rows:
        table[uid] = {
            "conversations": int(conv_cnt or 0),
            "duration_min": round(float(dur_sum or 0), 1),
            "tool_use": int(tool_sum or 0),
        }
    return table


def get_inactive_users(start_date, end_date, users, group):
    # 這段篩選時間內有活動的人（uuid）
    active_uuids = {
        row.uuid
        for row in _msg_query(start_date, end_date, users, group)
        .with_entities(User.uuid).distinct().all()
    }
    roster = get_all_users(group)   # [{uuid, name, email}]
    if users:
        selected = [u for u in roster if u["uuid"] in set(users)]
    else:
        selected = roster

    # 全時段累積用量對照表（一次算好）
    lifetime = _lifetime_stats(group)
    empty = {"conversations": 0, "duration_min": 0, "tool_use": 0}

    result = []
    for u in selected:
        if u["uuid"] in active_uuids:
            continue   # 這段時間有用 → 不是未使用者
        result.append({
            "uuid": u["uuid"],
            "name": u["name"],
            "email": u["email"],
            "lifetime": lifetime.get(u["uuid"], empty),   # 全時段用量（沒紀錄就 0）
        })
    result.sort(key=lambda x: x["name"])
    return result


def get_summary(start_date, end_date, users, group):
    # 分母：有篩選特定用戶（例如選了部門）→ 用篩選的人數；否則用整組人數
    if users:
        total_users = len(set(users))
    else:
        total_users = db.session.query(User).filter(User.group_id == group).count()
    msgs = _msg_query(start_date, end_date, users, group).all()

    if not msgs:
        return {
            "active_users": 0,
            "total_users": total_users,
            "active_pct": 0,
            "rounds": {"mean": 0, "median": 0, "mode": 0},
            "duration_mean": 0,
            "conversation_count": 0,
        }

    # 活躍人數（有訊息的人）—— 用 uuid 當身份
    active_uuids = set()
    for m in msgs:
        active_uuids.add(m.conversation.user.uuid)
    active_count = len(active_uuids)
    active_pct = round(active_count / total_users * 100, 1) if total_users else 0

    # 對話來回數：以人（uuid）為單位，只算 human 訊息
    user_msg_totals = defaultdict(int)
    for m in msgs:
        if m.sender == "human":
            user_msg_totals[m.conversation.user.uuid] += 1
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

    # 對話數（標準A）：範圍內有訊息活動的不同對話（conversation_uuid）數量
    conversation_count = len(conv_durations)

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
        "conversation_count": conversation_count,
    }


def get_ranking(metric, start_date, end_date, users, group):
    msgs = _msg_query(start_date, end_date, users, group).all()

    # uuid -> 顯示名 對照（供輸出）
    name_of = {}
    user_data = defaultdict(list)
    conv_sets = defaultdict(set)   # uuid -> 該人不同對話 uuid 集合（供對話數）
    for m in msgs:
        u = m.conversation.user
        uid = u.uuid
        name_of[uid] = _display_name(u)
        conv_sets[uid].add(m.conversation_uuid)
        if metric == "messages":
            if m.sender == "human":
                user_data[uid].append(1)
        elif metric == "duration":
            user_data[uid].append(m.created_at_tw)
        elif metric == "tools":
            user_data[uid].append(m.tool_use_count or 0)

    result = []
    if metric == "duration":
        from datetime import datetime
        fmt = "%Y-%m-%d %H:%M:%S"
        conv_user = defaultdict(lambda: defaultdict(list))
        for m in msgs:
            uid = m.conversation.user.uuid
            conv_user[uid][m.conversation_uuid].append(m.created_at_tw)
        for uid, convs in conv_user.items():
            durs = []
            for times in convs.values():
                sorted_times = sorted(times)
                if len(sorted_times) >= 2:
                    diff = (datetime.strptime(sorted_times[-1], fmt) -
                            datetime.strptime(sorted_times[0], fmt)).total_seconds() / 60
                    durs.append(round(diff, 1))
            value = round(mean(durs), 1) if durs else 0
            result.append({"uuid": uid, "name": name_of[uid], "value": value})
    elif metric == "conversations":
        # 對話數：該人在範圍內有訊息活動的不同對話數
        for uid, cset in conv_sets.items():
            result.append({"uuid": uid, "name": name_of[uid], "value": len(cset)})
    else:
        for uid, values in user_data.items():
            result.append({"uuid": uid, "name": name_of[uid], "value": sum(values)})

    result.sort(key=lambda x: x["value"], reverse=True)
    return result


def get_hourly(start_date, end_date, users, group):
    msgs = _msg_query(start_date, end_date, users, group).all()

    name_of = {}
    user_hours = defaultdict(lambda: [0] * 24)
    seen = defaultdict(set)  # 同一對話同一小時只算一次

    for m in msgs:
        u = m.conversation.user
        uid = u.uuid
        name_of[uid] = _display_name(u)
        key = (m.conversation_uuid, m.hour)
        if key not in seen[uid]:
            seen[uid].add(key)
            if m.hour is not None:
                user_hours[uid][m.hour] += 1

    return [
        {"uuid": uid, "name": name_of[uid], "hours": hours}
        for uid, hours in sorted(user_hours.items(), key=lambda kv: name_of[kv[0]])
    ]

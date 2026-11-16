"""Analyse de la charge d'entraînement à partir des activités Strava."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def _week_start(dt):
    """Lundi 00:00 (UTC) de la semaine de dt."""
    day = dt.astimezone(timezone.utc)
    monday = day - timedelta(days=day.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_date(activity):
    return datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00"))


def weekly_summary(activities, weeks=6):
    """Volume (h et km) par semaine et par sport pour les N dernières semaines."""
    now = datetime.now(timezone.utc)
    current = _week_start(now)
    buckets = {}
    for i in range(weeks - 1, -1, -1):
        start = current - timedelta(weeks=i)
        buckets[start] = defaultdict(lambda: {"hours": 0.0, "km": 0.0, "sessions": 0})

    for act in activities:
        start = _week_start(parse_date(act))
        if start not in buckets:
            continue
        sport = act.get("sport_type", act.get("type", "Autre"))
        hours = act.get("elapsed_time", 0) / 3600
        km = act.get("distance", 0) / 1000
        b = buckets[start][sport]
        b["hours"] += hours
        b["km"] += km
        b["sessions"] += 1

    summary = []
    for start, sports in buckets.items():
        total_h = sum(s["hours"] for s in sports.values())
        total_km = sum(s["km"] for s in sports.values())
        sessions = sum(s["sessions"] for s in sports.values())
        summary.append({
            "week_start": start.strftime("%d/%m"),
            "hours": round(total_h, 1),
            "km": round(total_km, 1),
            "sessions": sessions,
            "by_sport": {k: {"hours": round(v["hours"], 1), "km": round(v["km"], 1)}
                         for k, v in sorted(sports.items(), key=lambda x: -x[1]["hours"])},
        })
    return summary


def fatigue_indicators(activities):
    """Charge récente vs charge habituelle (ratio aigu/chronique simplifié)."""
    now = datetime.now(timezone.utc)
    loads = defaultdict(float)  # charge = heures pondérées par intensité estimée
    for act in activities:
        d = parse_date(act)
        days_ago = (now - d).days
        if days_ago > 28:
            continue
        hours = act.get("elapsed_time", 0) / 3600
        intensity = 1.0
        avg_hr = act.get("average_heartrate")
        if avg_hr:
            intensity = min(max(avg_hr / 140, 0.7), 1.4)
        loads[days_ago] += hours * intensity

    acute = sum(v for k, v in loads.items() if k < 7)
    chronic = sum(v for k, v in loads.items()) / 4
    if chronic == 0:
        ratio = 0.0
    else:
        ratio = acute / chronic
    status = "détente"
    if ratio >= 1.5:
        status = "surcharge — allège cette semaine"
    elif ratio >= 1.3:
        status = "charge élevée — prudence"
    elif ratio >= 0.8:
        status = "charge équilibrée"
    elif ratio > 0:
        status = "reprise / faible charge"
    return {"acute": round(acute, 1), "chronic": round(chronic, 1),
            "ratio": round(ratio, 2), "status": status}


def main_sport(activities):
    counts = defaultdict(float)
    for act in activities:
        counts[act.get("sport_type", act.get("type", "Autre"))] += act.get("elapsed_time", 0)
    return max(counts, key=counts.get) if counts else None

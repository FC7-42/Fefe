"""Modèle de Banister (fitness–fatigue / impulse-response).

Charge d'entraînement : TRIMP banister quand la FC moyenne/max est
disponible, sinon estimation pondérée par le sport et la durée.

  ATL(k) = ATL(k-1) + (Load(k) - ATL(k-1)) * (1 - exp(-1/7))
  CTL(k) = CTL(k-1) + (Load(k) - CTL(k-1)) * (1 - exp(-1/42))
  TSB(k) = CTL(k) - ATL(k)   (forme / fraîcheur, positif = reposé)

ATL = fatigue aiguë, CTL = fitness chronique, TSB = adaptation nette.
"""
import math
from datetime import datetime, timedelta, timezone

ATL_TAU = 7.0
CTL_TAU = 42.0

# Charge par minute en l'absence de FC (ordres de grandeur pragmatiques)
DEFAULT_LOAD_PER_MIN = {
    "ride": 5.5, "virtualride": 6.0, "gravelride": 6.0,
    "run": 9.0, "trailrun": 10.5, "treadmill": 9.0,
    "swim": 8.0, "walk": 3.5, "hike": 5.0,
    "weighttraining": 5.0, "yoga": 2.5, "ebikeride": 3.0,
}
FALLBACK_LOAD_PER_MIN = 6.0


def sport_key(activity):
    return str(activity.get("sport_type", activity.get("type", ""))).lower().replace(" ", "")


def activity_load(activity):
    """Charge d'une séance : TRIMP banister si FC dispo, sinon estimation."""
    minutes = activity.get("elapsed_time", 0) / 60
    if minutes <= 0:
        return 0.0
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    if avg_hr and max_hr and max_hr > avg_hr > 0:
        ratio = avg_hr / max_hr
        y = ratio / (1 - ratio)  # facteur de Banister (HRrel)
        return minutes * y * 0.64 * math.e ** (1.92 * ratio)
    per_min = DEFAULT_LOAD_PER_MIN.get(sport_key(activity), FALLBACK_LOAD_PER_MIN)
    return minutes * per_min


def _day_key(dt):
    return dt.astimezone(timezone.utc).date()


def daily_loads(activities, days=90):
    """Charge totale par jour sur les N derniers jours (dict date -> load)."""
    today = datetime.now(timezone.utc).date()
    loads = {}
    for act in activities:
        d = datetime.fromisoformat(act["start_date"].replace("Z", "+00:00")).astimezone(timezone.utc).date()
        if (today - d).days < days:
            loads[d] = loads.get(d, 0.0) + activity_load(act)
    return loads


def banister_series(activities, days=90):
    """Séries journalières ATL/CTL/TSB sur les N derniers jours."""
    loads = daily_loads(activities, days)
    start = (datetime.now(timezone.utc).date() - timedelta(days=days - 1))
    atl, ctl = 0.0, 0.0
    atl_gain = 1 - math.exp(-1 / ATL_TAU)
    ctl_gain = 1 - math.exp(-1 / CTL_TAU)
    series = []
    for i in range(days):
        day = start + timedelta(days=i)
        load = loads.get(day, 0.0)
        atl += (load - atl) * atl_gain
        ctl += (load - ctl) * ctl_gain
        series.append({
            "date": day.isoformat(),
            "load": round(load, 1),
            "atl": round(atl, 1),
            "ctl": round(ctl, 1),
            "tsb": round(ctl - atl, 1),
        })
    return series


def _tsb_status(tsb):
    if tsb > 25:
        return "très frais — idéal pour une séance de qualité ou une course"
    if tsb > 5:
        return "frais — bon moment pour pousser"
    if tsb > -10:
        return "zone neutre — entraînement productif"
    if tsb > -30:
        return "fatigue accumulée — privilégie l'endurance facile"
    return "fatigue élevée — allège fortement ou repose-toi"


def banister_state(activities):
    """État actuel + valeur de la veille pour visualiser la tendance."""
    series = banister_series(activities, days=90)
    today = series[-1]
    yesterday = series[-2] if len(series) > 1 else today
    return {
        "atl": today["atl"],
        "ctl": today["ctl"],
        "tsb": today["tsb"],
        "tsb_yesterday": yesterday["tsb"],
        "status": _tsb_status(today["tsb"]),
        "series": series,
    }

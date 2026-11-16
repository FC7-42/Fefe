"""Modèle de Banister (fitness–fatigue / impulse-response), personnalisable.

Charge d'entraînement : TRIMP banister quand la FC moyenne/max est
disponible, sinon estimation pondérée par le sport et la durée.

  ATL(k) = ATL(k-1) + (Load(k) - ATL(k-1)) * (1 - exp(-1/ATL_DAYS))
  CTL(k) = CTL(k-1) + (Load(k) - CTL(k-1)) * (1 - exp(-1/CTL_DAYS))
  TSB(k) = CTL(k) - ATL(k)   (forme / fraîcheur, positif = reposé)

Personnalisation (variables d'environnement, valeurs par défaut) :
  ATL_DAYS=7      constante de temps de la fatigue aiguë
  CTL_DAYS=42     constante de temps de la fitness chronique
  HRMAX=190       FC max connue ; sinon estimée sur tes activités
"""
import math
import os
from datetime import datetime, timedelta, timezone

ATL_TAU = float(os.environ.get("ATL_DAYS", 7))
CTL_TAU = float(os.environ.get("CTL_DAYS", 42))
HRMAX_OVERRIDE = float(os.environ["HRMAX"]) if os.environ.get("HRMAX") else None

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


def estimate_hrmax(activities):
    """FC max personnalisée : valeur explicite (HRMAX) sinon la plus haute
    FC max observée sur l'ensemble des activités, sinon 190 par défaut."""
    if HRMAX_OVERRIDE:
        return HRMAX_OVERRIDE
    observed = [a["max_heartrate"] for a in activities
                if a.get("max_heartrate")]
    return max(observed) if observed else 190.0


def activity_load(activity, hrmax=None):
    """Charge d'une séance : TRIMP de Banister si FC dispo, sinon estimation.

    TRIMP = durée(min) × HRrel × 0.64 × e^(1.92 × HRrel), avec
    HRrel = FC moyenne / FC max personnelle (estimée sur l'historique).
    Ordre de grandeur attendu : ~100-150 par heure de séance soutenue.
    """
    minutes = activity.get("elapsed_time", 0) / 60
    if minutes <= 0:
        return 0.0
    avg_hr = activity.get("average_heartrate")
    if avg_hr and hrmax and 0 < avg_hr < hrmax:
        ratio = min(avg_hr / hrmax, 0.95)
        return minutes * ratio * 0.64 * math.exp(1.92 * ratio)
    per_min = DEFAULT_LOAD_PER_MIN.get(sport_key(activity), FALLBACK_LOAD_PER_MIN)
    return minutes * per_min


def _day_key(dt):
    return dt.astimezone(timezone.utc).date()


def daily_loads(activities, days=90, hrmax=None):
    """Charge totale par jour sur les N derniers jours (dict date -> load)."""
    today = datetime.now(timezone.utc).date()
    loads = {}
    for act in activities:
        d = datetime.fromisoformat(act["start_date"].replace("Z", "+00:00")).astimezone(timezone.utc).date()
        if (today - d).days < days:
            loads[d] = loads.get(d, 0.0) + activity_load(act, hrmax)
    return loads


def banister_series(activities, days=90, hrmax=None):
    """Séries journalières ATL/CTL/TSB sur les N derniers jours."""
    loads = daily_loads(activities, days, hrmax)
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
    hrmax = estimate_hrmax(activities)
    series = banister_series(activities, days=90, hrmax=hrmax)
    today = series[-1]
    yesterday = series[-2] if len(series) > 1 else today
    return {
        "atl": today["atl"],
        "ctl": today["ctl"],
        "tsb": today["tsb"],
        "tsb_yesterday": yesterday["tsb"],
        "status": _tsb_status(today["tsb"]),
        "series": series,
        "hrmax": hrmax,
        "atl_days": int(ATL_TAU),
        "ctl_days": int(CTL_TAU),
    }

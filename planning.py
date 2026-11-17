"""Programmation orientée objectif : macrocycle vers l'événement cible.

L'événement se configure dans le .env :
  EVENT_NAME=Marathon des Blessés des Armées
  EVENT_DATE=2027-05-23
  EVENT_DISTANCE=marathon        (marathon | semi | 10km | 4km)
  EVENT_GOAL_TIME=3:00:00        (optionnel, format H:MM:SS)

Phases (semaines restantes -> phase) :
  > 22  préparation générale    construire la base, monter la CTL
  15-22 fondamental             volume, endurance, force
  9-14  développement           seuil, tempo
  4-8   spécifique               allure cible, sorties longues spécifiques
  1-3   affûtage                 volume réduit, fraîcheur maximale le jour J
  0     semaine de course
"""
import os
from datetime import date, timedelta

DISTANCES_KM = {"marathon": 42.195, "semi": 21.097, "10km": 10.0, "4km": 4.0}

PHASE_INFO = {
    "préparation générale": "Construire la base : volume progressif, tout en endurance, renforcement.",
    "fondamental": "Volume et endurance : sorties longues qui s'allongent, aisance aérobie.",
    "développement": "Développer le seuil : tempo et fractionnés longs, volume maintenu.",
    "spécifique": "Allure cible : blocs à l'allure marathon, sorties longues spécifiques.",
    "affûtage": "Affûtage : volume réduit, intensité légère maintenue, fraîcheur le jour J.",
    "semaine J": "Semaine de course : très léger, tout est déjà dans les jambes.",
}


def event_config():
    raw_date = os.environ.get("EVENT_DATE")
    if not raw_date:
        return None
    try:
        event_date = date.fromisoformat(raw_date)
    except ValueError:
        return None
    distance = os.environ.get("EVENT_DISTANCE", "marathon").strip().lower()
    km = DISTANCES_KM.get(distance, 42.195)
    goal_seconds = None
    raw_goal = os.environ.get("EVENT_GOAL_TIME", "").strip()
    if raw_goal:
        try:
            parts = [int(p) for p in raw_goal.split(":")]
            while len(parts) < 3:
                parts.insert(0, 0)
            h, m, s = parts[-3:]
            goal_seconds = h * 3600 + m * 60 + s
        except ValueError:
            goal_seconds = None
    return {
        "name": os.environ.get("EVENT_NAME", "Objectif"),
        "date": event_date,
        "distance": distance,
        "km": km,
        "goal_seconds": goal_seconds,
        "pace_seconds": round(goal_seconds / km) if goal_seconds else None,
    }


def weeks_until(event_date, today=None):
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    event_monday = event_date - timedelta(days=event_date.weekday())
    return round((event_monday - monday).days / 7)


def phase_for(weeks_left):
    if weeks_left <= 0:
        return "semaine J"
    if weeks_left <= 3:
        return "affûtage"
    if weeks_left <= 8:
        return "spécifique"
    if weeks_left <= 14:
        return "développement"
    if weeks_left <= 22:
        return "fondamental"
    return "préparation générale"


def format_pace(seconds_per_km):
    if not seconds_per_km:
        return None
    m, s = divmod(int(round(seconds_per_km)), 60)
    return f"{m}:{s:02d} /km"


def format_duration(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}" if h else f"{m}min{s:02d}"


def target_volume(weekly_hours, weeks_left, distance=None):
    """Volume cible de la semaine (heures) : montée progressive de base vers
    le pic à l'entrée en affûtage, décharge toutes les 4 semaines.

    Le volume est calibré sur l'objectif, pas seulement sur l'historique :
    un marathon se prépare avec 8-12 h/semaine au pic, quel que soit le
    point de départ (plancher ajusté à la hausse si nécessaire).
    """
    base = weekly_hours if weekly_hours > 0 else 4.0
    if distance == "marathon":
        base = max(base, 6.0)
        peak = min(max(base * 1.4, 8.0), 12.0)
    elif distance == "semi":
        base = max(base, 4.0)
        peak = min(max(base * 1.4, 5.5), 8.0)
    else:
        peak = min(max(base * 1.35, 6.0), 10.0)

    if weeks_left <= 0:
        return peak * 0.25
    if weeks_left <= 3:
        return {3: peak * 0.65, 2: peak * 0.50, 1: peak * 0.30}[weeks_left]

    progress = max(0.0, min(1.0, 1 - (weeks_left - 4) / 20))
    volume = base + (peak - base) * progress
    if weeks_left % 4 == 0:
        volume = max(volume * 0.7, base)
    return min(volume, peak)


def long_run_cap(weeks_left):
    """Durée maximale de la sortie longue selon la distance à l'objectif."""
    if weeks_left <= 3:
        return 60
    if weeks_left <= 8:
        return 165
    if weeks_left <= 14:
        return 150
    return 105


def phase_timeline(weekly_hours, event_date, today=None, distance=None):
    """Semaines de la semaine courante (première) à la semaine de course.
    Chaque entrée : lundi, phase, volume cible."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    weeks_left = weeks_until(event_date, today)
    out = []
    for offset in range(0, weeks_left + 1):
        wl = weeks_left - offset
        out.append({
            "week_start": monday + timedelta(weeks=offset),
            "phase": phase_for(wl),
            "target_hours": round(target_volume(weekly_hours, wl, distance), 1),
        })
    return out

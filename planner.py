"""Générateur de plan de séances hebdomadaire, orienté objectif.

Le volume et les séances dépendent :
  - du volume habituel (moyenne des semaines complètes) et du volume cible
    de la semaine (progression vers le pic, calculée par planning.py)
  - de la phase de préparation (fondamental, développement, spécifique…)
  - de la forme actuelle (TSB du modèle de Banister)
"""
from datetime import date, timedelta

from planning import format_pace


def _round5(minutes):
    return max(int(round(minutes / 5.0)) * 5, 10)


def _fmt_duration(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"


def build_plan(main_sport, weekly_hours, tsb, phase="préparation générale",
               weeks_left=None, pace_seconds=None, long_cap=None):
    """Retourne (plan, note). weekly_hours = volume cible de la semaine."""
    if weekly_hours <= 0:
        weekly_hours = 4.0
    total_min = weekly_hours * 60

    if tsb < -30:
        factor = 0.7
        note = ("Forme très négative (TSB < -30) : décharge improvisée — "
                "volume réduit, aucune intensité, même en pleine préparation.")
        with_quality = False
    elif tsb < -10:
        factor = 0.85
        note = ("Fatigue accumulée (TSB négatif) : volume allégé de 15 %, "
                "qualité raccourcie.")
        with_quality = True
    else:
        factor = 1.0
        note = ""
        with_quality = True

    total_min = max(total_min * factor, 120)
    sport = main_sport or "Course"
    pace = format_pace(pace_seconds) if isinstance(pace_seconds, (int, float)) else pace_seconds
    plan = []

    if phase == "semaine J":
        plan.append({
            "day": "Mardi",
            "type": "Déverrouillage",
            "duration": "25 min",
            "description": "20 min très facile + 4 lignes droites de 15 s.",
        })
        plan.append({
            "day": "Jeudi",
            "type": "Activation",
            "duration": "20 min",
            "description": "15 min très facile + 2 min à l'allure de course + 3 min facile.",
        })
        plan.append({
            "day": "Jour de course",
            "type": "🏁 Objectif",
            "duration": "—",
            "description": "Parti prudent, hydratation toutes les 20 min, "
                           "garde l'allure cible jusqu'au 30e km, puis tout ce que tu as.",
        })
        return _sorted(plan), "Semaine de course : repos, sommeil, glucides. Le travail est fait."

    long_min = min(total_min * 0.40, float(long_cap or 105))
    plan.append({
        "day": "Samedi ou dimanche",
        "type": "Sortie longue",
        "duration": _fmt_duration(long_min),
        "description": _long_run_session(phase, pace),
    })

    if with_quality:
        plan.append({
            "day": "Jeudi",
            "type": "Qualité",
            "duration": _fmt_duration(total_min * 0.25),
            "description": _quality_session(sport, phase, pace),
        })

    plan.append({
        "day": "Mardi",
        "type": "Endurance fondamentale",
        "duration": _fmt_duration(total_min * 0.30),
        "description": f"{sport} facile, cardio bas, tu dois pouvoir parler en courant.",
    })

    if total_min >= 300:
        plan.append({
            "day": "Vendredi",
            "type": "Récupération",
            "duration": _fmt_duration(total_min * 0.10),
            "description": "Sortie très facile ou mobilité/renforcement léger.",
        })

    plan.append({
        "day": "Lundi",
        "type": "Repos",
        "duration": "—",
        "description": "Repos complet ou 20 min de mobilité.",
    })

    if note:
        note = note + " " + _phase_note(phase, pace)
    else:
        note = _phase_note(phase, pace)
    return _sorted(plan), note


def _sorted(plan):
    order = {"Lundi": 0, "Mardi": 1, "Mercredi": 2, "Jeudi": 3, "Vendredi": 4,
             "Samedi ou dimanche": 5, "Jour de course": 6}
    plan.sort(key=lambda s: order[s["day"]])
    return plan


def _phase_note(phase, pace):
    pace_txt = f" à {pace} " if pace else " "
    return {
        "préparation générale": "Phase de base : la régularité prime sur l'intensité.",
        "fondamental": "Phase fondamentale : on allonge la sortie longue chaque semaine.",
        "développement": "Phase développement : le seuil monte, l'allure de course devient plus facile.",
        "spécifique": f"Phase spécifique : les blocs{pace_txt}impriment l'allure de course dans les jambes.",
        "affûtage": "Affûtage : moins de volume, zéro fatigue inutile, fraîcheur maximale le jour J.",
    }.get(phase, "")


def _long_run_session(phase, pace):
    if phase == "spécifique" and pace:
        return ("Sortie longue spécifique : partie centrale de 40-60 min à "
                f"l'allure cible ({pace}), le reste en endurance facile.")
    if phase in ("spécifique", "développement"):
        return "Sortie longue en endurance, finissez les 20 dernières minutes à allure semi."
    return "Sortie longue en endurance fondamentale, allure conversationnelle."


def _quality_session(sport, phase, pace):
    key = sport.lower()
    if not key.startswith(("run", "trail", "treadmill")):
        return ("Séance de qualité adaptée à ton sport : échauffement 15 min, "
                "travail par intervalles, retour au calme 10 min.")
    if phase == "spécifique":
        if pace:
            return (f"Allure cible : 3 x 8 min{f' à {pace}' if pace else ''} "
                    "(récup 2 min en trottinant), après 15 min d'échauffement.")
        return "Allure cible : 3 x 8 min à l'allure de course, récup 2 min."
    if phase == "développement":
        return "Seuil : 2 x 12 min à allure semi (récup 3 min), après 15 min d'échauffement."
    if phase == "affûtage":
        return "Entretien : 4 x 2 min à allure cible (récup 90 s), séance courte et vive."
    return "Côtes : 8 x 45 s en montée, redescente en récupération, après 15 min d'échauffement."


def next_week_dates():
    """Date du lundi de la semaine à venir."""
    today = date.today()
    return today - timedelta(days=today.weekday()) + timedelta(weeks=1)

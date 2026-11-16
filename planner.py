"""Générateur de plan de séances hebdomadaire basé sur l'historique Strava."""
from datetime import date, timedelta


def _fmt_duration(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"


def build_plan(main_sport, weekly_hours, tsb):
    """Retourne une liste de séances (jour, type, description, durée).

    tsb : forme actuelle du modèle de Banister (CTL - ATL).
    Positif = reposé, négatif = fatigué.
    """
    if weekly_hours <= 0:
        weekly_hours = 4.0
    total_min = weekly_hours * 60

    if tsb < -30:
        intensity_share = 0.0
        note = "Forme très négative (TSB < -30) : semaine de récupération."
    elif tsb < -10:
        intensity_share = 0.10
        note = "Fatigue accumulée (TSB négatif) : semaine allégée."
    elif tsb > 5:
        intensity_share = 0.20
        note = "Tu es frais (TSB positif) : bonne semaine pour du travail de qualité."
    else:
        intensity_share = 0.15
        note = "Zone neutre : entraînement productif, une séance de qualité."

    easy_min = total_min * (1 - intensity_share)
    quality_min = total_min * intensity_share

    sport = main_sport or "Course"
    plan = []

    plan.append({
        "day": "Mardi",
        "type": "Endurance fondamentale",
        "duration": _fmt_duration(easy_min * 0.45),
        "description": f"{sport} facile, allure conversationnelle, cardio bas.",
    })
    plan.append({
        "day": "Jeudi",
        "type": "Qualité",
        "duration": _fmt_duration(quality_min + easy_min * 0.15),
        "description": _quality_session(sport, tsb),
    })
    plan.append({
        "day": "Samedi ou dimanche",
        "type": "Sortie longue",
        "duration": _fmt_duration(easy_min * 0.40),
        "description": f"{sport} en endurance, terrain vallonné si possible.",
    })
    if weekly_hours >= 6:
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
    return plan, note


def _quality_session(sport, tsb):
    if tsb < -10:
        return "Fractionné court et doux : 6 x 1 min rapide / 1 min lent."
    if sport.lower().startswith(("ride", "cycl", "velo", "vélo", "virtualride")):
        return "Vélo : 4 x 5 min seuil (RPE 7/10) avec 3 min de récupération."
    if sport.lower().startswith(("swim", "nag")):
        return "Natation : 8 x 100 m à rythme soutenu, 20 s de récup."
    return "Course : 5 x 3 min à allure seuil, 90 s de récupération en trottinant."


def next_week_dates():
    """Date du lundi de la semaine à venir."""
    today = date.today()
    return today - timedelta(days=today.weekday()) + timedelta(weeks=1)

"""Générateur de plan de séances hebdomadaire basé sur l'historique Strava."""
from datetime import date, timedelta


def _round5(minutes):
    return max(int(round(minutes / 5.0)) * 5, 10)


def _fmt_duration(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"


def build_plan(main_sport, weekly_hours, tsb):
    """Retourne (plan, note).

    weekly_hours : volume hebdomadaire habituel (moyenne des semaines
    complètes récentes, calculée côté dashboard — jamais la semaine
    en cours qui est incomplète).
    tsb : forme actuelle du modèle de Banister (CTL - ATL).
    """
    if weekly_hours <= 0:
        weekly_hours = 4.0
    total_min = weekly_hours * 60

    if tsb < -30:
        factor = 0.6
        with_quality = False
        note = ("Forme très négative (TSB < -30) : semaine de décharge — "
                "volume réduit d'environ 40 %, aucune intensité.")
    elif tsb < -10:
        factor = 0.8
        with_quality = False
        note = ("Fatigue accumulée (TSB négatif) : volume réduit d'environ 20 %, "
                "tout en endurance facile cette semaine.")
    elif tsb > 5:
        factor = 1.0
        with_quality = True
        note = ("Tu es frais (TSB positif) : semaine normale avec du travail "
                "de qualité — profites-en.")
    else:
        factor = 1.0
        with_quality = True
        note = "Zone neutre : semaine normale, une séance de qualité."

    total_min = max(total_min * factor, 150)

    sport = main_sport or "Course"
    plan = []

    plan.append({
        "day": "Samedi ou dimanche",
        "type": "Sortie longue",
        "duration": _fmt_duration(total_min * 0.40),
        "description": f"{sport} en endurance fondamentale, allure conversationnelle, terrain vallonné si possible.",
    })

    if with_quality:
        plan.append({
            "day": "Jeudi",
            "type": "Qualité",
            "duration": _fmt_duration(total_min * 0.25),
            "description": _quality_session(sport, tsb),
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

    order = {"Lundi": 0, "Mardi": 1, "Mercredi": 2, "Jeudi": 3, "Vendredi": 4, "Samedi ou dimanche": 5}
    plan.sort(key=lambda s: order[s["day"]])
    return plan, note


def _quality_session(sport, tsb):
    key = sport.lower()
    if key.startswith(("ride", "cycl", "velo", "vélo", "virtualride", "gravel")):
        return ("Vélo — échauffement 15 min, puis 4 x 5 min à allure seuil "
                "(effort 7/10) avec 3 min de récupération, retour au calme 10 min.")
    if key.startswith(("swim", "nag")):
        return ("Natation — 400 m d'échauffement, puis 8 x 100 m à rythme soutenu "
                "(20 s de récup), 200 m de retour au calme.")
    if key.startswith(("trail", "randon")):
        return ("Trail — côte : 8 x 1 min en montée soutenue, redescente en récup, "
                "sur un circuit vallonné.")
    return ("Course — échauffement 15 min, puis 5 x 3 min à allure seuil "
            "(récupération 90 s en trottinant), retour au calme 10 min.")


def next_week_dates():
    """Date du lundi de la semaine à venir."""
    today = date.today()
    return today - timedelta(days=today.weekday()) + timedelta(weeks=1)

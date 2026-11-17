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
    """Retourne (plan, note). weekly_hours = volume cible de la semaine.

    Structure fixe de la semaine (rythme réel de l'athlète) :
      Lundi    footing facile
      Mardi    musculation/renforcement
      Mercredi piste — qualité 1
      Jeudi    footing facile
      Vendredi piste — qualité 2
      Samedi   renforcement (optionnel) ou repos
      Dimanche sortie longue
    """
    if weekly_hours <= 0:
        weekly_hours = 4.0
    total_min = weekly_hours * 60

    if tsb < -30:
        factor = 0.7
        note = ("Forme très négative (TSB < -30) : décharge improvisée — "
                "volume réduit, une seule séance de piste, même en pleine préparation.")
        with_quality = False
    elif tsb < -10:
        factor = 0.85
        note = ("Fatigue accumulée (TSB négatif) : volume allégé de 15 %, "
                "qualités raccourcies.")
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
            "day": "Lundi",
            "type": "Footing",
            "duration": "25 min",
            "description": "Très facile, décontracté.",
        })
        plan.append({
            "day": "Mardi",
            "type": "Muscles",
            "duration": "30 min",
            "description": "Renforcement léger, sans charge lourde.",
        })
        plan.append({
            "day": "Mercredi",
            "type": "Piste — activation",
            "duration": "30 min",
            "description": "20 min facile + 4 lignes droites de 15 s.",
        })
        plan.append({
            "day": "Jeudi",
            "type": "Footing",
            "duration": "20 min",
            "description": "15 min très facile + 2 min à l'allure de course.",
        })
        plan.append({
            "day": "Vendredi",
            "type": "Repos",
            "duration": "—",
            "description": "Repos complet, sommeil, glucides.",
        })
        plan.append({
            "day": "Samedi",
            "type": "Déverrouillage",
            "duration": "15 min",
            "description": "10 min très facile + 3 lignes droites.",
        })
        plan.append({
            "day": "Dimanche",
            "type": "🏁 Marathon",
            "duration": "—",
            "description": "Parti prudent, hydratation toutes les 20 min, "
                           "allure cible jusqu'au 30e km, puis tout ce que tu as.",
        })
        return _sorted(plan), "Semaine de course : tout est déjà dans les jambes."

    long_min = min(total_min * 0.38, float(long_cap or 105))
    q1_min = total_min * 0.22
    q2_min = total_min * 0.18 if with_quality else 0
    jog_min = max((total_min - long_min - q1_min - q2_min) / 2, 20)

    near_race = weeks_left is not None and weeks_left <= 3
    muscles_min = "30 min" if near_race else "45 min"
    muscles_desc = ("Renforcement léger : gainage, mollets, mobilité."
                    if near_race else
                    "Renforcement : gainage, squats, fentes, mollets. "
                    "Pas de course ce jour-là.")

    plan.append({
        "day": "Lundi",
        "type": "Footing",
        "duration": _fmt_duration(jog_min),
        "description": f"{sport} très facile, cardio bas, tu dois pouvoir parler.",
    })
    plan.append({
        "day": "Mardi",
        "type": "Muscles",
        "duration": muscles_min,
        "description": muscles_desc,
    })
    plan.append({
        "day": "Mercredi",
        "type": "Piste — qualité 1",
        "duration": _fmt_duration(q1_min),
        "description": _quality_session(sport, phase, pace),
    })
    plan.append({
        "day": "Jeudi",
        "type": "Footing",
        "duration": _fmt_duration(jog_min),
        "description": f"{sport} facile, récupération active de la séance de piste.",
    })
    if with_quality:
        plan.append({
            "day": "Vendredi",
            "type": "Piste — qualité 2",
            "duration": _fmt_duration(q2_min),
            "description": _second_quality_session(sport, phase, pace),
        })
    else:
        plan.append({
            "day": "Vendredi",
            "type": "Footing",
            "duration": _fmt_duration(jog_min),
            "description": "Footing facile à la place de la piste (semaine allégée).",
        })
    plan.append({
        "day": "Samedi",
        "type": "Renforcement (optionnel)",
        "duration": "30 min",
        "description": "Mobilité, gainage, étirements — ou repos complet si fatigue.",
    })
    plan.append({
        "day": "Dimanche",
        "type": "Sortie longue",
        "duration": _fmt_duration(long_min),
        "description": _long_run_session(phase, pace),
    })

    if note:
        note = note + " " + _phase_note(phase, pace)
    else:
        note = _phase_note(phase, pace)
    return _sorted(plan), note


def _sorted(plan):
    order = {"Lundi": 0, "Mardi": 1, "Mercredi": 2, "Jeudi": 3, "Vendredi": 4,
             "Samedi": 5, "Dimanche": 6, "Samedi ou dimanche": 5, "Jour de course": 6}
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
        return "Sortie longue en endurance, finis les 20 dernières minutes à allure semi."
    return "Sortie longue en endurance fondamentale, allure conversationnelle."


def _quality_session(sport, phase, pace):
    """Qualité 1 — mercredi : la séance clé de la semaine."""
    if phase == "spécifique":
        if pace:
            return (f"Allure cible : 3 x 8 min à {pace} "
                    "(récup 2 min en trottinant), après 15 min d'échauffement.")
        return "Allure cible : 3 x 8 min à l'allure de course, récup 2 min."
    if phase == "développement":
        return "Seuil : 2 x 12 min à allure semi (récup 3 min), après 15 min d'échauffement."
    if phase == "affûtage":
        return "Entretien : 4 x 2 min à allure cible (récup 90 s), séance courte et vive."
    return "Côtes : 8 x 45 s en montée, redescente en récupération, après 15 min d'échauffement."


def _second_quality_session(sport, phase, pace):
    """Qualité 2 — vendredi : plus courte, complémentaire de celle du mercredi."""
    if phase == "spécifique":
        if pace:
            return (f"Allure cible : 2 x 3 km à {pace} "
                    "(récup 2 min), après 15 min d'échauffement, retour au calme 10 min.")
        return "Allure cible : 2 x 3 km, récup 2 min, après échauffement."
    if phase == "développement":
        return "Fractionné court : 8 x 400 m à allure 10 km (récup 1 min en trottinant)."
    if phase == "affûtage":
        return "Foulées : 6 lignes droites de 20 s, le reste très facile."
    return "Foulées et gammes : 6 x 20 s rapides, gammes de course, le reste en facile."


def next_week_dates():
    """Date du lundi de la semaine à venir."""
    today = date.today()
    return today - timedelta(days=today.weekday()) + timedelta(weeks=1)

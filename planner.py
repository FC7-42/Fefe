"""Générateur de plan de séances hebdomadaire, orienté objectif.

Le volume et les séances dépendent :
  - du volume cible de la semaine (progression vers le pic, planning.py)
  - de la phase de préparation (fondamental, développement, spécifique…)
  - de la forme actuelle (TSB du modèle de Banister)

Les allures sont personnelles : dérivées de l'objectif (EVENT_GOAL_TIME).
Pour un 3h : marathon 4:16 · semi 4:02 · seuil 3:54 · 10 km 3:46 ·
VMA-based 3:36 · facile 5:06 (par km).
"""
from datetime import date, timedelta

from planning import format_pace


def training_paces(pace_seconds):
    """Allures d'entraînement (s/km) dérivées de l'allure marathon cible."""
    if not pace_seconds:
        return None
    return {
        "mp": pace_seconds,
        "semi": pace_seconds - 14,
        "seuil": pace_seconds - 22,
        "10k": pace_seconds - 30,
        "rapide": pace_seconds - 40,
        "easy": pace_seconds + 50,
    }


def _round5(minutes):
    return max(int(round(minutes / 5.0)) * 5, 10)


def _fmt_duration(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}" if h else f"{m} min"


def build_plan(main_sport, weekly_hours, tsb, phase="préparation générale",
               weeks_left=None, pace_seconds=None, long_cap=None):
    """Retourne (plan, note). weekly_hours = volume cible de la semaine.

    Structure fixe de la semaine (rythme réel de l'athlète) :
      Lundi footing · Mardi musculation · Mercredi piste (qualité 1)
      Jeudi footing · Vendredi piste (qualité 2) · Samedi renforcement
      optionnel · Dimanche sortie longue.
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
    paces = training_paces(pace_seconds)
    plan = []

    min_jog, min_q1, min_q2 = 45, 60, 45

    if phase == "semaine J":
        plan.append({"day": "Lundi", "type": "Footing", "duration": "25 min",
                     "description": "Très facile, décontracté."})
        plan.append({"day": "Mardi", "type": "Muscles", "duration": "30 min",
                     "description": "Renforcement léger, sans charge lourde."})
        plan.append({"day": "Mercredi", "type": "Piste — activation", "duration": "30 min",
                     "description": "20 min facile + 4 lignes droites de 15 s."})
        plan.append({"day": "Jeudi", "type": "Footing", "duration": "20 min",
                     "description": "15 min très facile + 2 min à l'allure de course."})
        plan.append({"day": "Vendredi", "type": "Repos", "duration": "—",
                     "description": "Repos complet, sommeil, glucides."})
        plan.append({"day": "Samedi", "type": "Déverrouillage", "duration": "15 min",
                     "description": "10 min très facile + 3 lignes droites."})
        plan.append({"day": "Dimanche", "type": "🏁 Marathon", "duration": "—",
                     "description": "Parti prudent, hydratation toutes les 20 min, "
                                    "allure cible jusqu'au 30e km, puis tout ce que tu as."})
        return _sorted(plan), "Semaine de course : tout est déjà dans les jambes."

    long_min = min(total_min * 0.38, float(long_cap or 105))
    q1_min = max(total_min * 0.22, min_q1)
    q2_min = max(total_min * 0.18, min_q2) if with_quality else 0
    jog_min = max((total_min - long_min - q1_min - q2_min) / 2, min_jog)

    near_race = weeks_left is not None and weeks_left <= 3
    muscles_min = "30 min" if near_race else "45 min"
    muscles_desc = ("Renforcement léger : gainage, mollets, mobilité."
                    if near_race else
                    "Renforcement : gainage, squats, fentes, mollets. "
                    "Pas de course ce jour-là.")

    easy_desc = (f"{sport} très facile (~{format_pace(paces['easy'])}), "
                 "tu dois pouvoir parler." if paces else
                 f"{sport} très facile, tu dois pouvoir parler.")

    plan.append({"day": "Lundi", "type": "Footing", "duration": _fmt_duration(jog_min),
                 "description": easy_desc})
    plan.append({"day": "Mardi", "type": "Muscles", "duration": muscles_min,
                 "description": muscles_desc})
    plan.append({"day": "Mercredi", "type": "Piste — qualité 1",
                 "duration": _fmt_duration(q1_min),
                 "description": _quality_session(phase, weeks_left, paces)})
    plan.append({"day": "Jeudi", "type": "Footing", "duration": _fmt_duration(jog_min),
                 "description": f"Footing de récupération, très facile"
                                + (f" (~{format_pace(paces['easy'])})." if paces else ".")})
    if with_quality:
        plan.append({"day": "Vendredi", "type": "Piste — qualité 2",
                     "duration": _fmt_duration(q2_min),
                     "description": _second_quality_session(phase, weeks_left, paces)})
    else:
        plan.append({"day": "Vendredi", "type": "Footing",
                     "duration": _fmt_duration(jog_min),
                     "description": "Footing facile à la place de la piste (semaine allégée)."})
    plan.append({"day": "Samedi", "type": "Renforcement (optionnel)", "duration": "30 min",
                 "description": "Mobilité, gainage, étirements — ou repos complet si fatigue."})
    plan.append({"day": "Dimanche", "type": "Sortie longue",
                 "duration": _fmt_duration(long_min),
                 "description": _long_run_session(phase, weeks_left, paces)})

    if note:
        note = note + " " + _phase_note(phase, pace)
    else:
        note = _phase_note(phase, pace)
    return _sorted(plan), note


def _sorted(plan):
    order = {"Lundi": 0, "Mardi": 1, "Mercredi": 2, "Jeudi": 3, "Vendredi": 4,
             "Samedi": 5, "Dimanche": 6}
    plan.sort(key=lambda s: order[s["day"]])
    return plan


def _phase_note(phase, pace):
    pace_txt = f" à {pace} " if pace else " "
    return {
        "préparation générale": "Phase de base : on construit le moteur aérobie et la résistance.",
        "fondamental": "Phase fondamentale : tempo à allure semi et volume qui s'installe.",
        "développement": "Phase développement : seuil et 10 km, l'allure marathon devient facile.",
        "spécifique": f"Phase spécifique : les blocs{pace_txt}impriment l'allure de course dans les jambes.",
        "affûtage": "Affûtage : moins de volume, zéro fatigue inutile, fraîcheur maximale le jour J.",
    }.get(phase, "")


def _p(paces, key):
    return format_pace(paces[key]) if paces else ""


def _long_run_session(phase, weeks_left, paces):
    if phase == "spécifique" and paces:
        return (f"Sortie longue spécifique : 40-60 min centrales à {_p(paces, 'mp')} "
                "(allure marathon), le reste en endurance facile.")
    if phase == "développement" and paces:
        return (f"Sortie longue : 30 dernières minutes à {_p(paces, 'semi')} "
                "(allure semi), le reste en facile.")
    if phase == "fondamental" and paces:
        return (f"Sortie longue en endurance, avec 6-8 accélérations de 1 min "
                f"à {_p(paces, 'semi')} réparties dans la seconde moitié.")
    return "Sortie longue en endurance fondamentale, allure conversationnelle."


def _quality_session(phase, weeks_left, paces):
    """Qualité 1 — mercredi : la séance clé de la semaine."""
    if phase == "spécifique" and paces:
        mp = _p(paces, "mp")
        tiers = [
            (8, f"Allure marathon : 3 x 10 min à {mp} (récup 2 min en "
                "trottinant), après 20 min d'échauffement progressif."),
            (7, f"Allure marathon : 3 x 12 min à {mp} (récup 2 min), "
                "après 20 min d'échauffement."),
            (6, f"Allure marathon : 3 x 5 km à {mp} (récup 3 min), "
                "après 20 min d'échauffement."),
            (5, f"Allure marathon : 2 x 7 km à {mp} (récup 3 min), "
                "après 20 min d'échauffement."),
            (4, f"Allure marathon : 12 km continus à {mp} — la séance de "
                "confiance, après 20 min d'échauffement."),
        ]
        for threshold, desc in tiers:
            if weeks_left is not None and weeks_left >= threshold:
                return desc
        return tiers[-1][1]
    if phase == "développement" and paces:
        if weeks_left is not None and weeks_left <= 11:
            return (f"Seuil long : 2 x 15 min à {_p(paces, 'seuil')} "
                    "(récup 3 min), après 20 min d'échauffement.")
        return (f"Seuil : 3 x 10 min à {_p(paces, 'seuil')} "
                "(récup 2 min 30), après 20 min d'échauffement.")
    if phase == "fondamental" and paces:
        return (f"Tempo progressif : 3 x 10 min de {_p(paces, 'semi')} à "
                f"{_p(paces, 'seuil')} (récup 2 min), après 20 min d'échauffement.")
    if phase == "affûtage" and paces:
        return (f"Rythme de course : 5 x 1000 m à {_p(paces, 'mp')} "
                "(récup 90 s), séance courte et nerveuse.")
    if paces:
        return (f"Côtes : 10 x 45 s en montée (effort fort, ~{_p(paces, 'rapide')} "
                "sur la pente), redescente en trottinant + 6 foulées de 20 s.")
    return "Côtes : 10 x 45 s en montée, redescente en récupération + 6 foulées."


def _second_quality_session(phase, weeks_left, paces):
    """Qualité 2 — vendredi : entretien du seuil et vitesse, sans concurrencer
    la séance clé du mercredi."""
    if phase == "spécifique" and paces:
        return (f"Entretien seuil : 2 x 10 min à {_p(paces, 'seuil')} "
                "(récup 2 min 30), après 15 min d'échauffement, retour au calme 10 min.")
    if phase == "développement" and paces:
        return (f"800 m : 6 x 800 m à {_p(paces, '10k')} "
                "(récup 1 min 30 en trottinant).")
    if phase == "fondamental" and paces:
        return (f"400 m : 10 x 400 m à {_p(paces, '10k')} "
                "(récup 1 min en trottinant), après 15 min d'échauffement.")
    if phase == "affûtage" and paces:
        return (f"Vitesse : 8 x 30 s à {_p(paces, 'rapide')} "
                "(récup 90 s), le reste très facile.")
    if paces:
        return (f"Foulées : 8 x 20 s à {_p(paces, 'rapide')}, "
                "gammes de course, le reste en facile.")
    return "Foulées : 8 x 20 s rapides, gammes de course, le reste en facile."


def next_week_dates():
    """Date du lundi de la semaine à venir."""
    today = date.today()
    return today - timedelta(days=today.weekday()) + timedelta(weeks=1)

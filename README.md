# 🏃 Strava Planificateur

Petite web app qui se connecte à ton compte Strava, calcule ta **fatigue**, ta
**fitness** et ton **niveau d'adaptation** avec le **modèle de Banister**
(fitness–fatigue), et génère un **plan de séances** pour la semaine.

## Le modèle de Banister

Chaque séance reçoit une **charge** (TRIMP de Banister : durée × facteur
d'intensité basé sur la FC moyenne/max ; estimation par sport si pas de FC).
Deux moyennes pondérées exponentielles sont ensuite calculées jour par jour :

| Indicateur | Nom | Constante de temps | Signification |
|---|---|---|---|
| **ATL** | Fatigue aiguë | 7 jours | charge des derniers jours |
| **CTL** | Fitness chronique | 42 jours | charge accumulée à long terme |
| **TSB** | Adaptation (forme) | CTL − ATL | positif = reposé, négatif = fatigué |

Lecture du TSB : `> +25` très frais · `+5 à +25` frais · `−10 à +5` zone
productive · `−30 à −10` fatigue accumulée · `< −30` récupération nécessaire.
Le plan de la semaine s'ajuste automatiquement à cette valeur.

## 1. Créer ton application API Strava

1. Va sur [strava.com/settings/api](https://www.strava.com/settings/api).
2. Remplis le formulaire :
   - **Application Name** : ce que tu veux (ex. `Planificateur perso`)
   - **Website** : `http://localhost:5000`
   - **Application Description** : libre
   - **Authorization Callback Domain** : `localhost`
3. Valide. Tu récupères **Client ID** et **Client Secret** en bas de page.
4. Copie `.env.example` en `.env` et remplis-le :

```bash
cp .env.example .env
```

> ⚠️ Les apps API Strava sont limitées à 200 appels / 15 min et 2000 / jour —
> largement suffisant ici (l'app ne fetch qu'au chargement du dashboard).

## 2. Lancer l'appli

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Ouvre [http://localhost:5000](http://localhost:5000), clique
**« Se connecter avec Strava »**, autorise l'accès (scope demandé :
`read,activity:read_all`) → tu arrives sur le tableau de bord.

## 3. Ce que tu vois

- **Modèle de Banister** : ATL (fatigue), CTL (fitness), TSB (adaptation),
  courbe de forme sur 90 jours.
- **Plan de la semaine** : séances endurance / qualité / sortie longue,
  dosées selon ton volume habituel et ton TSB.
- **Charge par semaine** : volume et répartition par sport sur 6 semaines.

## Structure

```
strava-planner/
├── app.py            # Routes Flask (OAuth, dashboard, rendu SVG du TSB)
├── strava_client.py  # Client API Strava v3 (OAuth + refresh + activités)
├── banister.py       # Modèle de Banister : TRIMP, ATL, CTL, TSB
├── analysis.py       # Volumes hebdomadaires, ratio aigu/chronique
├── planner.py        # Génération du plan hebdomadaire selon le TSB
└── templates/        # Pages HTML
```

## Idées d'évolution

- Persistance du refresh token (SQLite) pour éviter de re-connecter à chaque
  redémarrage.
- Calendrier des séances prévues vs réalisées.
- Import des seuils FC/power personnels pour un TRIMP plus précis.
- Projection TSB à J+7 selon le plan proposé.

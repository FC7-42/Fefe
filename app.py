import os
import secrets
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

from analysis import fatigue_indicators, main_sport, weekly_summary
from banister import banister_state
from planner import build_plan
from planning import (event_config, format_pace, long_run_cap, phase_for,
                      phase_timeline, target_volume, weeks_until)
from strava_client import StravaClient

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))

CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("STRAVA_REDIRECT_URI", "http://localhost:5000/callback")


def get_client():
    client = StravaClient(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    if "access_token" in session:
        client.access_token = session["access_token"]
        client.refresh_token = session["refresh_token"]
        client.expires_at = session["expires_at"]
    return client


X0, X1, Y0, Y1 = 50, 770, 10, 150  # zone de tracé du graphique (viewBox 780x180)


def _svg_points(series, key, lo, hi):
    """Convertit une série (ATL/CTL/TSB) en points SVG sur une échelle commune."""
    n = len(series)
    if n < 2:
        return ""
    span = (hi - lo) or 1
    pts = []
    for i, point in enumerate(series):
        x = X0 + i / (n - 1) * (X1 - X0)
        y = Y1 - (point[key] - lo) / span * (Y1 - Y0)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def _y_ticks(lo, hi, n=5):
    """Graduations verticales : (valeur, position y)."""
    span = (hi - lo) or 1
    out = []
    for i in range(n):
        v = lo + span * i / (n - 1)
        y = Y1 - (v - lo) / span * (Y1 - Y0)
        out.append({"label": f"{v:.0f}", "y": round(y, 1)})
    return out


def _x_ticks(series, every_days=14):
    """Graduations horizontales : (date, position x), une tous les N jours."""
    n = len(series)
    if n < 2:
        return []
    step_px = (X1 - X0) / (n - 1)
    first = datetime.strptime(series[0]["date"], "%Y-%m-%d").date()
    out = []
    for i, point in enumerate(series):
        d = datetime.strptime(point["date"], "%Y-%m-%d").date()
        if (d - first).days % every_days == 0:
            out.append({"label": d.strftime("%d/%m"), "x": round(X0 + i * step_px, 1)})
    return out


@app.route("/")
def index():
    connected = "access_token" in session
    return render_template("index.html", connected=connected,
                           configured=bool(CLIENT_ID and CLIENT_SECRET))


@app.route("/login")
def login():
    client = get_client()
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(client.auth_url(state))


@app.route("/callback")
def callback():
    if request.args.get("state") != session.get("oauth_state"):
        return "État OAuth invalide, réessaie.", 400
    code = request.args.get("code")
    if not code:
        error = request.args.get("error", "autorisation refusée")
        return f"Connexion Strava impossible : {error}", 400
    client = get_client()
    client.exchange_code(code)
    session["access_token"] = client.access_token
    session["refresh_token"] = client.refresh_token
    session["expires_at"] = client.expires_at
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "access_token" not in session:
        return redirect(url_for("index"))
    client = get_client()
    activities = client.activities(per_page=100, max_pages=5)

    weeks = weekly_summary(activities, weeks=6)
    fatigue = fatigue_indicators(activities)
    banister = banister_state(activities)
    sport = main_sport(activities)

    complete = [w["hours"] for w in weeks[:-1] if w["sessions"] > 0]
    recent_hours = sum(complete[-4:]) / len(complete[-4:]) if complete else 0

    event = event_config()
    phase = weeks_left = target_hours = pace = timeline = None
    long_cap = None
    if event:
        weeks_left = weeks_until(event["date"])
        phase = phase_for(weeks_left)
        floor = 6.0 if event["distance"] == "marathon" else (4.0 if event["distance"] == "semi" else 0)
        volume_gap = round(floor - recent_hours, 1) if floor and recent_hours < floor else 0
        target_hours = round(target_volume(recent_hours, weeks_left, event["distance"]), 1)
        pace = format_pace(event["pace_seconds"])
        long_cap = long_run_cap(weeks_left)
        timeline = phase_timeline(recent_hours, event["date"], distance=event["distance"])
        plan, note = build_plan(sport, target_hours, banister["tsb"],
                                phase=phase, weeks_left=weeks_left,
                                pace_seconds=event["pace_seconds"],
                                long_cap=long_cap)
    else:
        plan, note = build_plan(sport, recent_hours, banister["tsb"])

    series = banister["series"]
    lo = min(min(s["atl"], s["ctl"], s["tsb"]) for s in series)
    hi = max(max(s["atl"], s["ctl"], s["tsb"]) for s in series)
    pad = (hi - lo) * 0.05 or 1
    lo, hi = lo - pad, hi + pad
    atl_points = _svg_points(series, "atl", lo, hi)
    ctl_points = _svg_points(series, "ctl", lo, hi)
    tsb_points = _svg_points(series, "tsb", lo, hi)
    y_ticks = _y_ticks(lo, hi)
    x_ticks = _x_ticks(series)
    zero_y = round(Y1 - (0 - lo) / (hi - lo) * (Y1 - Y0)) if lo < 0 < hi else None

    athlete = client.athlete()
    return render_template("dashboard.html",
                           athlete=athlete, weeks=weeks, fatigue=fatigue,
                           banister=banister, atl_points=atl_points,
                           ctl_points=ctl_points, tsb_points=tsb_points,
                           y_ticks=y_ticks, x_ticks=x_ticks, zero_y=zero_y,
                           sport=sport, plan=plan, note=note,
                           event=event, phase=phase, weeks_left=weeks_left,
                           target_hours=target_hours, pace=pace,
                           actual_hours=round(recent_hours, 1), volume_gap=volume_gap,
                           timeline=timeline)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

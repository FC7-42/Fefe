import os
import secrets

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

from analysis import fatigue_indicators, main_sport, weekly_summary
from banister import banister_state
from planner import build_plan
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


def _tsb_svg_points(series, width=720, height=160, clamp=60):
    """Convertit la série TSB en points SVG (y = 80 - tsb, borné à ±clamp)."""
    n = len(series)
    if n < 2:
        return ""
    step = width / (n - 1)
    pts = []
    for i, point in enumerate(series):
        y = 80 - max(min(point["tsb"], clamp), -clamp) * (80 / clamp)
        pts.append(f"{i * step:.1f},{y:.1f}")
    return " ".join(pts)


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
    plan, note = build_plan(sport, recent_hours, banister["tsb"])
    tsb_points = _tsb_svg_points(banister["series"])

    athlete = client.athlete()
    return render_template("dashboard.html",
                           athlete=athlete, weeks=weeks, fatigue=fatigue,
                           banister=banister, tsb_points=tsb_points,
                           sport=sport, plan=plan, note=note)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

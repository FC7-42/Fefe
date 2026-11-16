"""Client minimal pour l'API Strava v3 (OAuth + activités)."""
import time

import requests

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.expires_at = 0

    def auth_url(self, state):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": "read,activity:read_all",
            "state": state,
        }
        query = "&".join(f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in params.items())
        return f"{AUTH_URL}?{query}"

    def exchange_code(self, code):
        data = self._token_request({"grant_type": "authorization_code", "code": code})
        self._store(data)

    def refresh(self):
        data = self._token_request({"grant_type": "refresh_token", "refresh_token": self.refresh_token})
        self._store(data)

    def _token_request(self, extra):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            **extra,
        }
        resp = requests.post(TOKEN_URL, data=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _store(self, data):
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.expires_at = data.get("expires_at", int(time.time()) + 3600)

    def _headers(self):
        if time.time() >= self.expires_at - 60:
            self.refresh()
        return {"Authorization": f"Bearer {self.access_token}"}

    def athlete(self):
        resp = requests.get(f"{API_BASE}/athlete", headers=self._headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()

    def activities(self, per_page=100, max_pages=5):
        """Activités récentes, les plus récentes d'abord."""
        out = []
        for page in range(1, max_pages + 1):
            resp = requests.get(
                f"{API_BASE}/athlete/activities",
                headers=self._headers(),
                params={"per_page": per_page, "page": page},
                timeout=15,
            )
            resp.raise_for_status()
            batch = resp.json()
            out.extend(batch)
            if len(batch) < per_page:
                break
        return out

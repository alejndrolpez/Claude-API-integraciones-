"""Cliente mínimo para la API de FatSecret Platform usando OAuth 2.0 (client credentials)."""

import os
import time
from pathlib import Path

import requests

TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
API_URL = "https://platform.fatsecret.com/rest/server.api"


class FatSecretError(Exception):
    pass


def load_dotenv(path=".env"):
    """Carga variables de un archivo .env sin sobrescribir las ya definidas."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class FatSecretClient:
    def __init__(self, client_id=None, client_secret=None, scope=None, timeout=20):
        load_dotenv()
        self.client_id = client_id or os.environ.get("FATSECRET_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("FATSECRET_CLIENT_SECRET")
        self.scope = scope or os.environ.get("FATSECRET_SCOPE", "basic")
        if not self.client_id or not self.client_secret:
            raise FatSecretError("Faltan FATSECRET_CLIENT_ID / FATSECRET_CLIENT_SECRET")
        self.timeout = timeout
        self._token = None
        self._expires_at = 0.0

    def get_token(self):
        # Renueva el token un minuto antes de que caduque (duran 24 h)
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        resp = requests.post(
            TOKEN_URL,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials", "scope": self.scope},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise FatSecretError(f"Error obteniendo token ({resp.status_code}): {resp.text}")
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 86400))
        return self._token

    def call(self, method, **params):
        """Llama a cualquier método de la API, p. ej. call("foods.search", search_expression="apple")."""
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {self.get_token()}"},
            data={"method": method, "format": "json", **params},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise FatSecretError(f"FatSecret error {err.get('code')}: {err.get('message')}")
        return data

    def search_foods(self, query, page=0, max_results=20):
        return self.call(
            "foods.search", search_expression=query, page_number=page, max_results=max_results
        )

    def get_food(self, food_id):
        return self.call("food.get.v4", food_id=food_id)

    def search_recipes(self, query, page=0, max_results=20):
        return self.call(
            "recipes.search.v3", search_expression=query, page_number=page, max_results=max_results
        )

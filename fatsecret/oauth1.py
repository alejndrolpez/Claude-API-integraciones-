"""OAuth 1.0 (3-legged) para métodos de perfil de FatSecret: diario, saved meals, etc.

FatSecret solo permite acceder a datos de una cuenta de usuario con OAuth 1.0;
OAuth 2.0 sirve únicamente para la base de datos pública.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode

import requests

from .client import API_URL, FatSecretError, load_dotenv

REQUEST_TOKEN_URL = "https://authentication.fatsecret.com/oauth/request_token"
AUTHORIZE_URL = "https://authentication.fatsecret.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://authentication.fatsecret.com/oauth/access_token"
TOKEN_FILE = Path(".fatsecret_token.json")


def _q(value):
    return quote(str(value), safe="~-._")


def _sign(http_method, url, params, consumer_secret, token_secret=""):
    norm = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(params.items()))
    base = "&".join([http_method, _q(url), _q(norm)])
    key = f"{_q(consumer_secret)}&{_q(token_secret)}".encode()
    return base64.b64encode(hmac.new(key, base.encode(), hashlib.sha1).digest()).decode()


class FatSecretUserClient:
    def __init__(self, consumer_key=None, consumer_secret=None, timeout=20):
        load_dotenv()
        # La Consumer Key de OAuth 1.0 es el mismo valor que el Client ID
        self.consumer_key = consumer_key or os.environ.get("FATSECRET_CLIENT_ID")
        self.consumer_secret = consumer_secret or os.environ.get("FATSECRET_CONSUMER_SECRET")
        if not self.consumer_key or not self.consumer_secret:
            raise FatSecretError(
                "Faltan FATSECRET_CLIENT_ID / FATSECRET_CONSUMER_SECRET en .env "
                "(el Consumer Secret de OAuth 1.0 es distinto del Client Secret de OAuth 2.0)"
            )
        self.timeout = timeout
        self.token = None
        self.token_secret = ""

    def _oauth_params(self, **extra):
        params = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": secrets.token_hex(16),
            "oauth_version": "1.0",
        }
        params.update(extra)
        return params

    def _signed(self, http_method, url, params, token_secret=""):
        params["oauth_signature"] = _sign(http_method, url, params, self.consumer_secret, token_secret)
        if http_method == "GET":
            resp = requests.get(url, params=params, timeout=self.timeout)
        else:
            resp = requests.post(url, data=params, timeout=self.timeout)
        if resp.status_code != 200:
            raise FatSecretError(f"{url} → {resp.status_code}: {resp.text}")
        return resp

    # ── Autorización ─────────────────────────────────────────────────

    def authorize(self, force=False):
        """Carga el token guardado o lanza el flujo 3-legged (con código de verificación)."""
        if not force and TOKEN_FILE.exists():
            data = json.loads(TOKEN_FILE.read_text())
            self.token, self.token_secret = data["oauth_token"], data["oauth_token_secret"]
            return

        resp = self._signed("POST", REQUEST_TOKEN_URL, self._oauth_params(oauth_callback="oob"))
        req = {k: v[0] for k, v in parse_qs(resp.text).items()}

        url = AUTHORIZE_URL + "?" + urlencode({"oauth_token": req["oauth_token"]})
        print(f"\n🌐  Abre este enlace, inicia sesión en FatSecret y autoriza la app:\n    {url}\n")
        webbrowser.open(url)
        verifier = input("🔑  Pega aquí el código de verificación que te muestra FatSecret: ").strip()

        params = self._oauth_params(oauth_token=req["oauth_token"], oauth_verifier=verifier)
        resp = self._signed("GET", ACCESS_TOKEN_URL, params, req["oauth_token_secret"])
        acc = {k: v[0] for k, v in parse_qs(resp.text).items()}
        self.token, self.token_secret = acc["oauth_token"], acc["oauth_token_secret"]
        TOKEN_FILE.write_text(json.dumps({"oauth_token": self.token, "oauth_token_secret": self.token_secret}))
        print("✅  Cuenta vinculada (token guardado en .fatsecret_token.json)\n")

    # ── Llamadas a la API ────────────────────────────────────────────

    def call(self, method, **params):
        extra = {"method": method, "format": "json", **{k: str(v) for k, v in params.items()}}
        if self.token:
            extra["oauth_token"] = self.token
        resp = self._signed("POST", API_URL, self._oauth_params(**extra), self.token_secret)
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise FatSecretError(f"{method}: error {err.get('code')}: {err.get('message')}")
        return data

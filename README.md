# Claude-API-integraciones-

## FatSecret Platform API

Cliente en Python para la [API de FatSecret](https://platform.fatsecret.com/docs/guides) con OAuth 2.0 (*client credentials*).

### Configuración

1. `pip install -r requirements.txt`
2. Copia `.env.example` a `.env` y rellena `FATSECRET_CLIENT_ID` y `FATSECRET_CLIENT_SECRET`.
   El archivo `.env` está en `.gitignore`: **nunca subas el secret al repositorio**.
3. En la consola de FatSecret (*Manage API Keys → IP Restrictions*) añade la IP pública
   desde la que vas a llamar a la API. Si no, la API responde
   `error 21: Invalid IP address detected`. (Puedes usar `0.0.0.0/0` solo para pruebas.)

### Uso

```bash
python -m fatsecret "apple"
```

```python
from fatsecret import FatSecretClient

fs = FatSecretClient()
fs.search_foods("banana")
fs.get_food(33691)
fs.call("foods.autocomplete.v2", expression="chick")  # cualquier método de la API
```

El token se pide a `https://oauth.fatsecret.com/connect/token`, dura 24 h y se renueva solo.

### Importar la dieta a tu cuenta (diario / Saved Meals)

FatSecret solo da acceso a los datos de **tu cuenta** mediante OAuth 1.0 (3-legged);
OAuth 2.0 sirve solo para la base de datos pública. Necesitas el **Consumer Secret**
(en *Manage API Keys*, distinto del Client Secret) en `FATSECRET_CONSUMER_SECRET`.

```bash
python fatsecret_import.py
```

La primera vez abre el navegador, autorizas la app y pegas el código de verificación
en la terminal. El token queda en `.fatsecret_token.json` (ignorado por git).
Recuerda que la IP desde la que lo ejecutas debe estar autorizada en FatSecret.

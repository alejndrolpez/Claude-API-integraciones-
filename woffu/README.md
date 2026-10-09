# Woffu: relleno de horas

`fill_month.py` rellena los días laborables pasados que estén vacíos en Woffu.

- Credenciales: variables de entorno `WOFFU_USER` y `WOFFU_PASS` (nunca en el código ni en el comando).
- Siempre se puede ensayar con `--dry-run`.
- Viernes: 7 h seguidas desde las 8:00. Lunes a jueves: lo que falte para `--weekly-hours` (40 por defecto), con una hora para comer.
- No toca fines de semana, festivos, hoy ni días que ya tienen fichajes.
- Requiere `requests`.

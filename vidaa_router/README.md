# Bloqueo DNS para Hisense VIDAA (nivel router)

Bloquea telemetría, seguimiento y anuncios de un TV Hisense VIDAA (probado en la idea
para el 85A6BG) desde el router o un bloqueador DNS. Es **complementario** a los ajustes
del propio TV (ACR, anuncios personalizados, consentimientos): hazlos primero.

Basado en la guía de <https://cleanyour.tv/not-android>. El proyecto principal de
cleanyourtv solo funciona en Android/Google TV, no en VIDAA.

## Qué bloquea y qué no

| Acción | Hosts (primera etiqueta) |
|---|---|
| Bloquear | `ter-jrnl-*`, `exc-jrnl-*`, `policy-jrnl-*` (telemetría), `tracking-vss`, `abtest-tv`, `recommend-ui-*`, `rsc-ads`, `rpt-mntz-azure` |
| Mantener | `ads-privacy`, `rsc-mntz` (si no, la app Ads Privacy no abre) |
| Mantener salvo prueba | `api.us`, `api.euro`, `api.eu` (actualizaciones) |
| Permitir si falla el inicio | `auth-*`, `api-gps-*`, `api-launcher-*`, `msg-*` |

Solo se bloquean hosts concretos, nunca el dominio entero.

## Generar la lista

```bash
cd vidaa_router
python3 generate_blocklist.py            # descarga HaGeZi Pro y filtra los hosts VIDAA
# o con una lista local:
python3 generate_blocklist.py --source mi_lista.txt
```

El script no trae nombres escritos a mano: los toma de la lista HaGeZi real y aplica los
prefijos de arriba (ver `BLOCK_PREFIXES` / `KEEP_PREFIXES` en el script). Genera en `dist/`:

| Archivo | Para |
|---|---|
| `vidaa-dnsmasq.conf` | OpenWrt, DD-WRT, Asuswrt-Merlin (dnsmasq) |
| `vidaa-adguard.txt` | AdGuard Home (filtro personalizado) |
| `vidaa-pihole-regex.txt` | Pi-hole (regex) |
| `vidaa-hosts.txt` | Cualquier sistema con fichero `hosts` |
| `vidaa-domains.txt` | Lista simple (NextDNS, otros) |

Si el script dice que no hay coincidencias, la lista elegida no incluye hosts VIDAA:
prueba con otra de HaGeZi (Multi o Pro) mediante `--source`.

## Instalar

- **OpenWrt:** copia `vidaa-dnsmasq.conf` a `/etc/dnsmasq.d/` (o añade el contenido en
  *Red → DHCP y DNS → Configuración avanzada → Archivos de configuración adicionales*) y
  reinicia `dnsmasq`.
- **Pi-hole:** *Domains → Add regex filter* con cada línea de `vidaa-pihole-regex.txt`.
- **AdGuard Home:** *Filtros → Reglas de filtrado personalizadas* y pega `vidaa-adguard.txt`.
- **NextDNS:** *Denylist* con `vidaa-domains.txt`. Su protección integrada no cubre VIDAA.
- **Router de operadora sin DNS configurable:** cambia el DNS del TV (Ajustes → Red →
  DNS manual) a la IP de tu Pi-hole/AdGuard, o instala uno en una Raspberry Pi.

Si el TV usa un DNS fijo ignorando el del router, redirige el puerto 53 a tu bloqueador y
bloquea el 853 (DNS sobre TLS). Muchos routers de operadora no lo permiten.

## Comprobar y deshacer

1. Reinicia el TV y comprueba que las apps, el inicio de sesión y las actualizaciones
   (*Ajustes → Soporte → Actualización*) siguen funcionando.
2. Si algo falla, mira el registro del bloqueador y permite primero `auth-*`, `api-gps-*`,
   `api-launcher-*` y `msg-*`.
3. Para deshacer, borra el archivo o las reglas añadidas.

Tras una actualización de firmware, vuelve a revisar los ajustes del TV.

## Pruebas

```bash
python3 generate_blocklist.py --source tests/sample_list.txt --out-dir /tmp/dist_test
```

`tests/sample_list.txt` usa nombres ficticios solo para comprobar el filtro.

# Prompt para una sesión local de Claude Code (Windows)

Copia todo lo que hay debajo de la línea en una sesión nueva de Claude Code abierta en tu
ordenador, dentro de la carpeta `Claude` (por ejemplo `C:\Users\TU_USUARIO\Documents\Claude`).
Requisitos: estar en la misma red Wi-Fi/cable que el router y los TVs, y tener `adb`
(Google SDK Platform Tools) y Python 3 instalados.

**No escribas la contraseña del router en este archivo ni la subas a git.** Dásela a Claude
solo si te la pide en la sesión local, o entra tú al router y dile lo que ves.

---

## Objetivo

Reducir anuncios y rastreo en mis TVs, sin romperlos y con todo reversible:

- **Hisense 85A6BG** (VIDAA, versión de software `V0000.06.12S.N0629`, idioma español).
- **Amazon Fire TV Stick 4K Max** (Fire OS 7.6.9.7, ya con depuración ADB activada).
- **Router** en `192.168.1.1` (marca y modelo por determinar).

## Contexto ya investigado

- El proyecto https://github.com/Gathin23/cleanyourtv solo funciona en Android TV y Google TV.
  Su `PROMPT.md` **excluye VIDAA y Fire TV**. No lo ejecutes tal cual en mis TVs.
- Guía para TVs no Android: https://cleanyour.tv/not-android
- En mi repo `alejndrolpez/Claude-API-integraciones-` (rama `claude/vidaa-router-blocklist`)
  está la carpeta `vidaa_router/` con `generate_blocklist.py`, que genera listas de bloqueo
  DNS para VIDAA (dnsmasq, AdGuard, Pi-hole, hosts) a partir de HaGeZi. No sirve para Fire TV.
- Del entorno en la nube no se pudo descargar la lista HaGeZi ni alcanzar mi red. Por eso
  esta sesión local debe verificar los nombres de host reales, no inventarlos.

## Reglas (importante)

1. Pregunta antes de cualquier acción que cambie algo (router, TV, DNS). Muestra el comando
   exacto y qué deshace.
2. **No desactives paquetes del Fire TV** (`pm disable-user`, `pm uninstall`) salvo que yo
   lo pida expresamente. El proyecto avisa de que puede dejar el dispositivo sin arrancar.
   Antes de cualquier cambio, guarda una copia: `adb shell pm list packages` y
   `adb shell getprop`.
3. No guardes contraseñas ni tokens en archivos, ni los imprimas en logs. Si necesitas una,
   pídemela por la sesión.
4. Al terminar, desactiva la depuración ADB del Fire TV y comprueba que el puerto 5555 no
   queda abierto.
5. Cuenta con que mi nombre y los números de serie son privados: no los subas a git.

## Tareas

1. **Diagnóstico del router.** Dime qué marca y modelo es (etiqueta o página de inicio en
   `http://192.168.1.1`) y si permite DNS personalizado o bloqueo de dominios. Si no se
   puede, propón alternativas (DNS manual en el TV, Pi-hole/AdGuard Home en una Raspberry,
   NextDNS).
2. **Fire TV.** Ejecuta `adb connect IP:5555` y `adb devices` y confirma que responde.
   Luego guíame por los ajustes de privacidad del propio dispositivo (datos de uso,
   anuncios basados en intereses, reproducción automática). Nada de desactivar paquetes.
3. **Hisense VIDAA.** Guíame por los ajustes de Enhanced Viewing/ACR, anuncios
   personalizados, consentimientos y voz. Si no aparece una opción, sáltala.
4. **Bloqueo DNS.** Ejecuta `vidaa_router/generate_blocklist.py` y revisa la lista que sale
   antes de aplicarla. Aplícala según lo que permita mi router o bloqueador DNS.
5. **Verificación.** Comprueba que apps, inicio de sesión y actualizaciones siguen
   funcionando en ambos TVs, y deja por escrito cómo deshacer cada cambio.

## Entrega

Un resumen corto con: qué cambió en cada dispositivo, cómo revertirlo, y qué quedó
pendiente.

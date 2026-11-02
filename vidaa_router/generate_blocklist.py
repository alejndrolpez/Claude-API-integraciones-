#!/usr/bin/env python3
"""Genera una lista de bloqueo DNS para TVs Hisense VIDAA (telemetría y anuncios).

No inventa dominios: descarga la lista HaGeZi (Pro por defecto), se queda solo con
los hosts de VIDAA/Hisense cuyo nombre empiece por los prefijos a bloquear y descarta
los de la lista de "mantener" (para no romper actualizaciones ni la app Ads Privacy).

Uso:
    python3 generate_blocklist.py                  # descarga la lista HaGeZi Pro
    python3 generate_blocklist.py --source lista.txt   # usa un archivo local
    python3 generate_blocklist.py --out-dir salida

Salida (en --out-dir): vidaa-domains.txt, vidaa-hosts.txt, vidaa-dnsmasq.conf,
vidaa-adguard.txt y vidaa-pihole-regex.txt.
"""
import argparse
import re
import sys
import urllib.request
from pathlib import Path

DEFAULT_SOURCE = "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/pro.txt"

# Dominios raíz donde viven los servicios de VIDAA / Hisense.
VIDAA_ROOTS = ("hismarttv.com", "vidaa.com", "hisense.com", "vidaahub.com")

# Primera etiqueta del host que se BLOQUEA (según la guía de cleanyour.tv).
BLOCK_PREFIXES = (
    "ter-jrnl", "exc-jrnl", "policy-jrnl",  # telemetría (uno por región)
    "tracking-vss", "abtest-tv",            # seguimiento y pruebas A/B
    "recommend-ui",                         # recomendaciones
    "rsc-ads", "rpt-mntz-azure",            # anuncios
)

# Primera etiqueta que NUNCA se bloquea aunque aparezca en la lista.
KEEP_PREFIXES = (
    "ads-privacy", "rsc-mntz",              # la app Ads Privacy deja de abrir
    "api", "api-us", "api-euro", "api-eu",  # posibles actualizaciones
    "auth", "api-gps", "api-launcher", "msg",  # inicio de sesión / pantalla de inicio
)


def fetch(source: str) -> str:
    if re.match(r"^https?://", source):
        with urllib.request.urlopen(source, timeout=60) as r:  # noqa: S310
            return r.read().decode("utf-8", "replace")
    return Path(source).read_text(encoding="utf-8")


def parse_domains(text: str):
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if not line:
            continue
        parts = line.split()
        host = parts[-1]  # sirve para "dominio" y para "0.0.0.0 dominio"
        if re.fullmatch(r"[a-z0-9._-]+", host) and "." in host:
            yield host


def first_label_matches(label: str, prefixes) -> bool:
    return any(label == p or label.startswith(p + "-") for p in prefixes)


def select(domains):
    out = set()
    for host in domains:
        if not host.endswith(VIDAA_ROOTS):
            continue
        label = host.split(".", 1)[0]
        if first_label_matches(label, KEEP_PREFIXES):
            continue
        if first_label_matches(label, BLOCK_PREFIXES):
            out.add(host)
    return sorted(out)


def write_outputs(hosts, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "vidaa-domains.txt").write_text("\n".join(hosts) + "\n")
    (out_dir / "vidaa-hosts.txt").write_text("".join(f"0.0.0.0 {h}\n" for h in hosts))
    # address=/host/ bloquea el host y sus subdominios (dnsmasq / OpenWrt).
    (out_dir / "vidaa-dnsmasq.conf").write_text("".join(f"address=/{h}/0.0.0.0\n" for h in hosts))
    # ||host^ es la sintaxis de AdGuard Home / uBlock.
    (out_dir / "vidaa-adguard.txt").write_text("".join(f"||{h}^\n" for h in hosts))
    (out_dir / "vidaa-pihole-regex.txt").write_text(
        "".join(f"(^|\\.){re.escape(h)}$\n" for h in hosts)
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="URL o archivo con la lista de dominios")
    ap.add_argument("--out-dir", default="dist", type=Path)
    args = ap.parse_args()

    try:
        hosts = select(parse_domains(fetch(args.source)))
    except Exception as exc:  # red caída, archivo inexistente...
        sys.exit(f"No se pudo leer la lista: {exc}")

    if not hosts:
        sys.exit("Ningún host VIDAA coincide. Prueba otra lista con --source (HaGeZi Multi o Pro).")
    write_outputs(hosts, args.out_dir)
    print(f"{len(hosts)} hosts bloqueados -> {args.out_dir}/")
    for h in hosts:
        print("  ", h)


if __name__ == "__main__":
    main()

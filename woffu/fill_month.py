#!/usr/bin/env python3
"""Rellena en Woffu los días laborables vacíos (solo pasados) con fichajes plausibles.

Credenciales por variables de entorno: WOFFU_USER, WOFFU_PASS
(opcional WOFFU_DOMAIN, por defecto krimdaconsulting.woffu.com).

Uso:
  python3 -I woffu/fill_month.py --dry-run
  python3 -I woffu/fill_month.py --from 2026-08-07 --to 2026-10-08
  python3 -I woffu/fill_month.py --weekly-hours 38.5

Reglas: nunca toca fines de semana, festivos, hoy ni días que ya tengan fichajes.
Viernes: jornada continua de --friday-hours. Lunes a jueves: lo que falta para
--weekly-hours, con una hora para comer. Entrada >= 8:00 y salida >= 16:00.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys

import requests

DOMAIN = os.environ.get("WOFFU_DOMAIN", "krimdaconsulting.woffu.com")
BASE = f"https://{DOMAIN}"
FMT = "%Y-%m-%dT%H:%M:%S"


def login():
    user, pw = os.environ.get("WOFFU_USER"), os.environ.get("WOFFU_PASS")
    if not user or not pw:
        sys.exit("Faltan WOFFU_USER / WOFFU_PASS en el entorno")
    r = requests.post(
        f"{BASE}/token",
        data={"grant_type": "password", "username": user, "password": pw},
        timeout=30,
    )
    r.raise_for_status()
    h = {"Authorization": "Bearer " + r.json()["access_token"], "Accept": "application/json"}
    me = requests.get(f"{BASE}/api/users", headers=h, timeout=30)
    me.raise_for_status()
    return h, me.json()["UserId"]


def sign(uid, ts, is_in):
    # Formato que usa la propia web para un fichaje nuevo.
    return {
        "new": True, "deleted": False, "agreementEventId": None, "code": None, "iP": None,
        "requestId": None, "signId": 0, "signStatus": 1, "signType": 3,
        "time": ts[11:], "date": ts, "trueDate": ts, "deviceId": None,
        "signIn": is_in, "userId": uid,
    }


def plan(day, rnd, weekly_hours, friday_hours):
    """Devuelve [(entrada, salida), ...] cuya suma es exactamente la jornada del día."""
    at = lambda h, m: dt.datetime.combine(day, dt.time(h, m))
    if day.weekday() == 4:
        start = at(8, rnd.randint(0, 12))
        return [(start, start + dt.timedelta(hours=friday_hours))]
    total = dt.timedelta(minutes=round((weekly_hours - friday_hours) * 60 / 4))
    start = at(8, 50) + dt.timedelta(minutes=rnd.randint(0, 24))
    lunch_start = at(13, rnd.randint(0, 30))
    lunch_end = lunch_start + dt.timedelta(hours=1)
    return [(start, lunch_start), (lunch_end, lunch_end + total - (lunch_start - start))]


class Woffu:
    def __init__(self):
        self.h, self.uid = login()

    def slots(self, day):
        r = requests.get(
            f"{BASE}/api/svc/core/users/{self.uid}/diarysummaries/workday/slots",
            headers=self.h, params={"date": day.isoformat()}, timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def put(self, day, pl):
        slots = [
            {"in": sign(self.uid, a.strftime(FMT), True),
             "out": sign(self.uid, b.strftime(FMT), False), "motive": None}
            for a, b in pl
        ]
        body = {"date": day.isoformat(), "comments": None, "userId": self.uid, "slots": slots}
        r = requests.put(
            f"{BASE}/api/svc/core/users/{self.uid}/diarysummaries/workday/slots/self",
            headers={**self.h, "Content-Type": "application/json"},
            data=json.dumps(body), timeout=30,
        )
        r.raise_for_status()

    def saved(self, day):
        s = self.slots(day).get("signSlots") or []
        return [(x["in"]["time"][:5], (x.get("out") or {}).get("time", "")[:5]) for x in s]


def main():
    today = dt.date.today()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", type=dt.date.fromisoformat, default=today.replace(day=1))
    ap.add_argument("--to", dest="end", type=dt.date.fromisoformat, default=today - dt.timedelta(days=1))
    ap.add_argument("--weekly-hours", type=float, default=40)
    ap.add_argument("--friday-hours", type=float, default=7)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    w, rnd = Woffu(), random.Random()
    end = min(a.end, today - dt.timedelta(days=1))
    ok = bad = 0
    day = a.start
    while day <= end:
        if day.weekday() < 5:
            data = w.slots(day)
            wd = data.get("diarySummaryWorkday") or {}
            absent = any(wd.get(k) for k in (
                "absenceRemuneratedEffectiveTime", "absenceRemuneratedNotEffectiveTime", "isEvent"))
            if not wd or wd.get("isHoliday") or wd.get("isWeekend") or data.get("signSlots") or absent:
                print(day, "salto", "(ausencia/vacaciones)" if absent else "")
            else:
                pl = plan(day, rnd, a.weekly_hours, a.friday_hours)
                exp = [(x.strftime("%H:%M"), y.strftime("%H:%M")) for x, y in pl]
                hours = sum((y - x).seconds for x, y in pl) / 3600
                if a.dry_run:
                    print(day, day.strftime("%a"), exp, f"{hours:.2f}h", "(dry-run)")
                else:
                    w.put(day, pl)
                    good = w.saved(day) == exp
                    print(day, day.strftime("%a"), exp, f"{hours:.2f}h", "OK" if good else "FALLO")
                    ok += good
                    bad += not good
        day += dt.timedelta(days=1)
    if not a.dry_run:
        print(f"escritos {ok}, fallos {bad}")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

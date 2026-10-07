#!/usr/bin/env python3
"""
FatSecret CBOMBA Importer
=========================
Importa la rotación de 3 días al diario y/o Saved Meals de tu cuenta de FatSecret.

Requisitos:
    pip install -r requirements.txt
    .env con FATSECRET_CLIENT_ID y FATSECRET_CONSUMER_SECRET (ver .env.example)

Uso:
    python fatsecret_import.py

La primera vez se abre el navegador para que autorices la app y pegues el código
de verificación en la terminal. El token se guarda y no vuelve a pedirse.
"""

import sys
import time
from datetime import date, timedelta

from fatsecret import FatSecretError
from fatsecret.oauth1 import FatSecretUserClient

# ── Dieta CBOMBA ─────────────────────────────────────────────────────
# Tupla: (término_búsqueda, gramos, comida)
# comida FatSecret: "breakfast", "lunch", "dinner", "other" (no hay "snacks")

DIETA = [
    {
        "nombre": "CBOMBA A — Pollo Arroz",
        "comidas": [
            ("rolled oats",              80, "breakfast"),
            ("plain kefir",             200, "breakfast"),
            ("frozen mixed berries",     80, "breakfast"),
            ("grilled chicken breast",  200, "lunch"),
            ("white rice cooked",       200, "lunch"),     # 80g seco ≈ 200g cocido
            ("broccoli cauliflower mix",150, "lunch"),
            ("grilled chicken breast",  150, "dinner"),
            ("gnocchi cooked",          150, "dinner"),
            ("mixed green salad",        80, "dinner"),
            ("raw almonds",              30, "other"),
            ("85% dark chocolate",       20, "other"),
        ],
    },
    {
        "nombre": "CBOMBA B — Pescado Patata",
        "comidas": [
            ("rolled oats",              80, "breakfast"),
            ("plain kefir",             200, "breakfast"),
            ("frozen mixed berries",     80, "breakfast"),
            ("hake fillet baked",       200, "lunch"),
            ("roasted potatoes",        250, "lunch"),
            ("broccoli cauliflower mix",150, "lunch"),
            ("grilled salmon",          150, "dinner"),
            ("baked sweet potato",      150, "dinner"),
            ("mixed green salad",        80, "dinner"),
            ("walnuts",                  30, "other"),
            ("protein pudding",         120, "other"),     # Natillas +Proteína Mercadona
        ],
    },
    {
        "nombre": "CBOMBA C — Huevo Mix HC",
        "comidas": [
            ("rolled oats",              80, "breakfast"),
            ("plain kefir",             200, "breakfast"),
            ("frozen mixed berries",     80, "breakfast"),
            ("scrambled eggs",          180, "lunch"),     # ~3 huevos grandes
            ("baked sweet potato",      200, "lunch"),
            ("mixed green salad",       100, "lunch"),
            ("turkey breast sliced",    100, "dinner"),
            ("cooked lentils",          200, "dinner"),
            ("mixed stir fry vegetables",150, "dinner"),
            ("raw almonds",              30, "other"),
            ("plain kefir",             150, "other"),
        ],
    },
]

MEAL_LABEL = {"breakfast": "Desayuno", "lunch": "Almuerzo", "dinner": "Cena", "other": "Snacks"}
EPOCH = date(1970, 1, 1)


def as_list(value):
    if value is None:
        return []
    return [value] if isinstance(value, dict) else value


# ── Resolución de alimentos ──────────────────────────────────────────

_cache = {}


def resolve_food(fs, query, grams):
    """Devuelve (food_id, serving_id, number_of_units, food_name) o None."""
    if query not in _cache:
        foods = as_list(fs.call("foods.search", search_expression=query, max_results=10)
                        .get("foods", {}).get("food"))
        if not foods:
            _cache[query] = None
        else:
            # Prioriza alimentos genéricos frente a marcas
            stub = next((f for f in foods if f.get("food_type") == "Generic"), foods[0])
            food = fs.call("food.get.v4", food_id=stub["food_id"])["food"]
            servings = as_list(food.get("servings", {}).get("serving"))
            weighed = [s for s in servings
                       if s.get("metric_serving_unit") in ("g", "ml") and s.get("metric_serving_amount")]
            # Preferimos el serving en gramos ("100 g"), si no cualquiera con peso métrico
            serving = next((s for s in weighed if s.get("measurement_description") == "g"),
                           weighed[0] if weighed else None)
            _cache[query] = (stub, serving)

    hit = _cache[query]
    if not hit or not hit[1]:
        return None
    stub, serving = hit
    # number_of_units se expresa en la unidad del serving: escalamos por gramos
    units = grams / float(serving["metric_serving_amount"]) * float(serving.get("number_of_units", 1))
    return stub["food_id"], serving["serving_id"], round(units, 3), stub["food_name"]


# ── Saved Meals ──────────────────────────────────────────────────────

def import_as_saved_meals(fs):
    print("=" * 55)
    print("  Modo: SAVED MEALS (una por día y comida)")
    print("=" * 55)

    for dia in DIETA:
        for meal in MEAL_LABEL:
            items = [c for c in dia["comidas"] if c[2] == meal]
            if not items:
                continue
            nombre = f"{dia['nombre']} · {MEAL_LABEL[meal]}"
            print(f"\n📋  {nombre}")
            try:
                data = fs.call("saved_meal.create", saved_meal_name=nombre, meals=meal)
                saved_id = data["saved_meal_id"]
                saved_id = saved_id["value"] if isinstance(saved_id, dict) else saved_id
            except FatSecretError as e:
                print(f"  ❌  No se pudo crear: {e}")
                continue

            for query, grams, _ in items:
                result = resolve_food(fs, query, grams)
                if result is None:
                    print(f"  ⚠️   No encontrado: '{query}'")
                    continue
                food_id, serving_id, units, food_name = result
                try:
                    fs.call("saved_meal_item.add", saved_meal_id=saved_id, food_id=food_id,
                            saved_meal_item_name=food_name, serving_id=serving_id,
                            number_of_units=units)
                    print(f"  ✅  {food_name} — {grams}g")
                except FatSecretError as e:
                    print(f"  ❌  '{food_name}': {e}")
                time.sleep(0.3)

    print("\n✅  Saved Meals creados. Búscalos en FatSecret > Saved Meals.")


# ── Diario ───────────────────────────────────────────────────────────

def import_to_diary(fs, start_date):
    print("=" * 55)
    print("  Modo: DIARIO (Food Diary)")
    print("=" * 55)

    for i, dia in enumerate(DIETA):
        entry_date = start_date + timedelta(days=i)
        print(f"\n📅  {dia['nombre']} → {entry_date}")

        for query, grams, meal in dia["comidas"]:
            result = resolve_food(fs, query, grams)
            if result is None:
                print(f"  ⚠️   No encontrado: '{query}'")
                continue
            food_id, serving_id, units, food_name = result
            try:
                fs.call("food_entry.create", food_id=food_id, food_entry_name=food_name,
                        serving_id=serving_id, number_of_units=units, meal=meal,
                        date=(entry_date - EPOCH).days)
                print(f"  ✅  [{MEAL_LABEL[meal]}] {food_name} — {grams}g")
            except FatSecretError as e:
                print(f"  ❌  '{food_name}': {e}")
            time.sleep(0.3)

    print("\n✅  Diario actualizado. Revisa FatSecret > Food Diary.")


# ── Entry point ──────────────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════════╗")
    print("║   FatSecret CBOMBA Importer  🏋️              ║")
    print("║   Rotación 3 días · 2300 kcal · 210g P       ║")
    print("╚══════════════════════════════════════════════╝")

    print("\nElige modo:")
    print("  [1] Saved Meals (comidas guardadas — sin fechas)")
    print("  [2] Diario (añade a días concretos desde hoy)")
    print("  [3] Ambos")

    choice = input("\nOpción (1/2/3): ").strip()
    if choice not in {"1", "2", "3"}:
        sys.exit("Opción no válida.")

    try:
        fs = FatSecretUserClient()
        fs.authorize()
    except FatSecretError as e:
        sys.exit(f"❌  {e}")

    if choice in {"1", "3"}:
        import_as_saved_meals(fs)

    if choice in {"2", "3"}:
        start = date.today()
        print(f"\nImportando días {start} → {start + timedelta(days=len(DIETA) - 1)}…")
        import_to_diary(fs, start)

    print("\n🎯  Todo listo. Revisa FatSecret y ajusta pesos o nombres si hace falta.\n")


if __name__ == "__main__":
    main()

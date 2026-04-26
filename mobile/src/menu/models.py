from __future__ import annotations

TOPPING_PRICES = {
    "Eggs": 25,
    "Chicken": 0,
    "Shrimps": 30,
    "Beef": 15,
    "Lamb": 30,
    "Mushrooms": 20,
}
MEAT_TOPPINGS = ["Chicken", "Beef", "Lamb"]
EXTRA_TOPPINGS = ["Eggs", "Shrimps", "Mushrooms"]


def is_topping_eligible(name: str) -> bool:
    lowered = str(name or "").lower()
    return "fried rice" in lowered or "fried noodles" in lowered or "magic bowl" in lowered


def normalize_cart(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if not item:
            continue
        entry = {
            "item_id": item.get("item_id"),
            "name": item.get("name", "Item"),
            "price": float(item.get("price", 0.0)),
            "quantity": max(1, int(item.get("quantity", 1))),
            "meat_topping": item.get("meat_topping", ""),
            "extra_toppings": item.get("extra_toppings", []),
        }
        if not isinstance(entry["extra_toppings"], list):
            entry["extra_toppings"] = []
        if is_topping_eligible(entry["name"]) and not entry["meat_topping"]:
            entry["meat_topping"] = "Chicken"
        normalized.append(entry)
    return normalized

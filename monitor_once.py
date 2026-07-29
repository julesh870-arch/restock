#!/usr/bin/env python3
# monitor_once.py — verifie tous les produits UNE fois, envoie une notif iPhone
# (ntfy) pour ceux qui viennent de repasser en stock, puis s'arrete.
# Concu pour GitHub Actions (gratuit, tourne tout seul 24/7 sans serveur a toi).

import os
import json
import csv
import ssl
import time
import urllib.request
import urllib.error

# Le nom de canal ntfy vient d'un "secret" GitHub (voir le guide).
NTFY_TOPIC = (os.environ.get("NTFY_TOPIC") or "").strip() or "restock-a-changer-9f3a7c"
NTFY_SERVER = "https://ntfy.sh"
CSV_FILE = "produits.csv"
STATE_FILE = "state.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()


def load_products(path):
    items = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("url") or "").strip()
            if not url or url.startswith("#"):
                continue
            items.append({
                "name": (row.get("nom") or url).strip(),
                "url": url,
                "present": [k.strip().lower() for k in (row.get("en_stock_si_present") or "").split("|") if k.strip()],
                "absent": [k.strip().lower() for k in (row.get("rupture_si_present") or "").split("|") if k.strip()],
            })
    return items


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
        return r.read().decode("utf-8", "ignore").lower()


def in_stock(page, p):
    ok_present = any(k in page for k in p["present"]) if p["present"] else True
    ok_absent = (not any(k in page for k in p["absent"])) if p["absent"] else True
    return ok_present and ok_absent


def push_iphone(title, message, click_url):
    payload = json.dumps({
        "topic": NTFY_TOPIC,
        "title": title,
        "message": message,
        "click": click_url,
        "tags": ["shopping_cart"],
        "priority": 5,
    }).encode("utf-8")
    req = urllib.request.Request(NTFY_SERVER, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15)


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def main():
    products = load_products(CSV_FILE)
    state = load_state()
    print(f"Verification de {len(products)} produit(s)…")
    for p in products:
        try:
            stock = in_stock(fetch(p["url"]), p)
        except urllib.error.HTTPError as e:
            print(f"  ⚠️  {p['name']} : HTTP {e.code}")
            continue
        except Exception as e:
            print(f"  ⚠️  {p['name']} : {e}")
            continue

        prev = state.get(p["name"])
        print(f"  {p['name']} : {'EN STOCK' if stock else 'rupture'}")
        if stock and prev is not True:
            try:
                push_iphone("🟢 RESTOCK", f"{p['name']} est disponible !", p["url"])
                print(f"    📲 Notif iPhone envoyee")
            except Exception as e:
                print(f"    ⚠️  Echec notif : {e}")
        state[p["name"]] = stock
        time.sleep(2)  # politesse entre 2 produits
    save_state(state)
    print("Termine.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# monitor_once.py — verifie tous les produits UNE fois, envoie une notif iPhone
# (ntfy) pour ceux qui viennent de repasser en stock, puis s'arrete.
# Concu pour GitHub Actions (gratuit, tourne tout seul 24/7 sans serveur a toi).

import os
import sys
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

# IP attendue du proxy Geonix. Si tu renouvelles ta cle avec une autre IP,
# mets a jour cette valeur (et le Secret PROXY_URL).
EXPECTED_IP = "45.11.189.70"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()

# --- Proxy : lu depuis le Secret GitHub, jamais en dur dans le code ---
PROXY_URL = (os.environ.get("PROXY_URL") or "").strip()
if not PROXY_URL:
    sys.exit("❌ ARRET : PROXY_URL absent — le scraper ne tournera pas sans proxy.")

# Opener qui force TOUT le trafic (http et https) a passer par le proxy.
OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY_URL, "https": PROXY_URL}),
    urllib.request.HTTPSHandler(context=CTX),
)


def check_proxy_ip():
    """Verifie que le trafic sort bien par l'IP du proxy, sinon on s'arrete."""
    req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": UA})
    ip = OPENER.open(req, timeout=15).read().decode("utf-8", "ignore").strip()
    print(f"IP de sortie : {ip}")
    if ip != EXPECTED_IP:
        sys.exit(f"❌ ARRET : IP inattendue ({ip}), le proxy n'est pas actif.")
    print("✅ Proxy actif, IP masquee.")


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
    with OPENER.open(req, timeout=20) as r:
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
    OPENER.open(req, timeout=15)


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
    check_proxy_ip()  # garde-fou : on ne scrape jamais sans proxy
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
    main()        "tags": ["shopping_cart"],
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

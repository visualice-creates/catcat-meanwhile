"""Automatische Formprüfung eines erzeugten Tages – ohne API, lokal testbar (python3 test_validate.py).

Die inhaltliche Prüfung (stimmt das?) übernimmt eine zweite Claude-Anfrage mit Websuche (siehe generate.py).
Hier geht es um alles, was sich mechanisch prüfen lässt: Pflichtfelder, Länge, erlaubte Motive, Belege,
keine Wiederholung.
"""
import re

from specs import ACCENTS, MAX_CHARS, MOTIFS, WORDS


def words(text):
    return len(re.findall(r"\w+", text.replace("## ", "")))


def key_for(topic, item):
    """Merkmal gegen Wiederholung: dieselbe Person, derselbe Titel, dasselbe Kraut, dasselbe Wort."""
    field = {"quote": "author", "so": "author", "paleo": "title", "astro": "title", "fact": "headline",
             "plant": "latin", "sa": "word"}[topic]
    return f"{topic}:{re.sub(r'[^a-z0-9äöüß]+', ' ', str(item.get(field, '')).lower()).strip()}"


def avoid_list(history, topic):
    """Lesbare Liste des bereits Verwendeten für den Prompt."""
    return [h["label"] for h in history if h["topic"] == topic]


def check(topic, item, history_keys):
    """Gibt eine Liste von Fehlern zurück (leer = in Ordnung)."""
    errors = []

    def need(field, min_len=1):
        v = item.get(field)
        if not isinstance(v, str) or len(v.strip()) < min_len:
            errors.append(f"Feld „{field}“ fehlt oder ist zu kurz")

    if topic in MOTIFS:
        if item.get("illu") not in MOTIFS[topic]:
            errors.append(f"Motiv „{item.get('illu')}“ nicht erlaubt")
        if item.get("accent") not in ACCENTS:
            errors.append(f"Akzentfarbe „{item.get('accent')}“ nicht erlaubt")

    if topic == "quote":
        for f in ("headline", "text", "author", "role", "when", "tag"):
            need(f)
        if len(item.get("text", "")) > MAX_CHARS["quote"]:
            errors.append(f"Zitat zu lang fürs Sperrbild (max. {MAX_CHARS['quote']} Zeichen)")
    elif topic in ("paleo", "astro"):
        for f in ("title", "tag", "source"):
            need(f)
        body = item.get("body") or []
        if not body or body[0].startswith("## "):
            errors.append("Artikel braucht einen Einstiegsabsatz")
        heads = sum(1 for p in body if p.startswith("## "))
        if not 3 <= heads <= 8:
            errors.append(f"{heads} Zwischenüberschriften (erwartet 3–8)")
        n = words(" ".join(body))
        lo, hi = WORDS["article"]
        if not lo <= n <= hi:
            errors.append(f"Artikel hat {n} Wörter (erwartet {lo}–{hi})")
    elif topic == "fact":
        for f in ("headline", "text", "tag", "source"):
            need(f)
        chain = item.get("chain") or []
        if len(chain) != 9:
            errors.append(f"Kette hat {len(chain)} Stationen (erwartet 9)")
        if any(not c.get("title") or not c.get("text") for c in chain):
            errors.append("Station ohne Titel oder Text")
        n = words(" ".join(f"{c.get('title', '')} {c.get('text', '')}" for c in chain))
        lo, hi = WORDS["chain"]
        if not lo <= n <= hi:
            errors.append(f"Kette hat {n} Wörter (erwartet {lo}–{hi})")
    elif topic == "plant":
        for f in ("name", "latin", "effect", "text"):
            need(f)
        n = words(item.get("text", ""))
        lo, hi = WORDS["plant_text"]
        if not lo <= n <= hi:
            errors.append(f"Kräutertext hat {n} Wörter (erwartet {lo}–{hi})")
    elif topic == "sa":
        for f in ("word", "kind", "meaning", "origin"):
            need(f)
        if len(item.get("word", "")) > MAX_CHARS["word"]:
            errors.append("Wort zu lang fürs Sperrbild")
    elif topic == "so":
        for f in ("text", "author", "when"):
            need(f)
        if len(item.get("text", "")) > MAX_CHARS["so"]:
            errors.append(f"Zitat zu lang fürs Sperrbild (max. {MAX_CHARS['so']} Zeichen)")

    # Belege: jede Behauptung mit einer Quelle (Werk, Fachartikel oder URL) – ob sie stimmt, prüft die Faktenprüfung
    claims = item.get("claims") or []
    min_claims = {"paleo": 6, "astro": 6, "fact": 9}.get(topic, 1)
    if len(claims) < min_claims:
        errors.append(f"nur {len(claims)} belegte Behauptungen (mindestens {min_claims})")
    bad = [c for c in claims if len(c.get("source", "").strip()) < 4]
    if bad:
        errors.append(f"{len(bad)} Behauptungen ohne Quelle")
    if not any(s.get("title", "").strip() for s in item.get("sources") or []):
        errors.append("keine Quellen angegeben")

    if key_for(topic, item) in history_keys:
        errors.append("schon einmal verwendet")
    return errors

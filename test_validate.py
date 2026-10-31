"""Tests der Formprüfung – laufen ohne API-Schlüssel (lokal und vor jedem Wochen-Job in GitHub Actions)."""
import json
import pathlib

from validate import avoid_list, check, key_for, words

FILL = "Wort " * 175
CLAIMS = [{"claim": f"Aussage {i}", "source": f"Autorin (2025), Fachzeitschrift {i}"} for i in range(10)]
SOURCES = [{"title": "Quelle", "url": "https://example.org"}]


def article(n_heads=5):
    body = ["Einstieg in zwei Sätzen. Noch ein Satz."]
    for i in range(n_heads):
        body += [f"## Abschnitt {i}", FILL.strip()]
    return {"tag": "Evolution", "title": "Ein neuer Titel", "illu": "dino", "accent": "#e8643c", "source": "X (2025)",
            "body": body, "sources": SOURCES, "claims": CLAIMS}


def run():
    failures = []

    def expect(name, topic, item, ok, used=frozenset()):
        errs = check(topic, item, set(used))
        if (not errs) != ok:
            failures.append(f"{name}: erwartet {'ok' if ok else 'Fehler'}, bekommen {errs}")

    expect("Artikel gültig", "paleo", article(), True)
    expect("Artikel zu kurz", "paleo", dict(article(), body=article()["body"][:3]), False)
    expect("Artikel knapp unter Ziel ist ok", "paleo", dict(article(), body=article()["body"][:-1] + [("Wort " * 140).strip()]), True)
    expect("Artikel ohne Einstieg", "paleo", dict(article(), body=article()["body"][1:]), False)
    expect("falsches Motiv", "paleo", dict(article(), illu="galaxy"), False)
    expect("falsche Farbe", "paleo", dict(article(), accent="#000000"), False)
    expect("zu wenige Belege", "paleo", dict(article(), claims=CLAIMS[:2]), False)
    expect("Beleg ohne Quelle", "paleo", dict(article(), claims=CLAIMS[:8] + [{"claim": "x", "source": ""}]), False)

    chain = [{"title": f"Station {i}", "text": "Wort " * 95} for i in range(9)]
    fact = {"tag": "Tierwelt", "headline": "Von A nach B", "text": "Einstieg.", "illu": "honey", "accent": "#f2b33d",
            "source": "Quellen", "chain": chain, "sources": SOURCES, "claims": CLAIMS}
    expect("Kette gültig", "fact", fact, True)
    expect("Kette mit 8 Stationen", "fact", dict(fact, chain=chain[:8]), False)

    plant = {"name": "Thymian", "latin": "Thymus vulgaris", "effect": "Lindert Husten.", "text": "Wort " * 50,
             "illu": "rosemary", "accent": "#a678f0", "sources": SOURCES, "claims": CLAIMS[:2]}
    expect("Kraut gültig", "plant", plant, True)
    expect("Kraut schon verwendet", "plant", plant, False, {key_for("plant", plant)})

    quote = {"tag": "Philosophie", "headline": "Mut", "text": "Ein kurzes Zitat.", "author": "Jemand", "role": "Philosophin",
             "when": "1900 · Werk", "illu": "eye", "accent": "#3fb6e0", "sources": SOURCES, "claims": CLAIMS[:1]}
    expect("Zitat gültig", "quote", quote, True)
    expect("Zitat zu lang", "quote", dict(quote, text="x" * 400), False)

    sa = {"word": "Lethologika", "kind": "Substantiv", "meaning": "Wort fehlt.", "origin": "griech.", "sources": SOURCES, "claims": CLAIMS[:1]}
    so = {"text": "Ein Satz über Sterne.", "author": "Jemand", "when": "1788 · Werk", "sources": SOURCES, "claims": CLAIMS[:1]}
    expect("Wort gültig", "sa", sa, True)
    expect("Sternen-Zitat gültig", "so", so, True)

    # Historie: eingebaute Inhalte sind gesperrt, Schreibweise egal
    history = json.loads((pathlib.Path(__file__).parent / "history.json").read_text())
    keys = {h["key"] for h in history}
    expect("eingebautes Wort gesperrt", "sa", dict(sa, word="LETHOLOGIKA"), False, keys)
    if "Lethologika" not in avoid_list(history, "sa"):
        failures.append("avoid_list enthält eingebaute Wörter nicht")
    if words("## Titel eins zwei") != 3:
        failures.append("Wortzählung")

    for f in failures:
        print("FEHLER", f)
    print("Formprüfung:", "alles ok" if not failures else f"{len(failures)} Fehler")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())

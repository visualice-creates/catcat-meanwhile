"""Was der Wochen-Job erzeugt: Wochenplan, JSON-Formate je Thema, Vorgaben für die Texte.

Die Formate entsprechen dem, was die App schon kennt (web/content.js, chains.js, herbs.js, weekend.js),
damit ein Tag aus dem Netz genauso dargestellt wird wie ein eingebauter.
"""

MODEL = "claude-opus-5-5"
EFFORT = "high"          # gründlich recherchieren und schreiben; Claude Opus 5.5 nimmt sonst "medium"
MAX_TOKENS = 32000       # Platz für Denken, Suchen und einen 5-Minuten-Artikel
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}

# Wochenplan ab 2. November 2026 (Montag = 0 … Sonntag = 6), wie SCHEDULES in web/content.js
PLAN = {0: "quote", 1: "paleo", 2: "fact", 3: "astro", 4: "plant", 5: "sa", 6: "so"}

# Motive, die die App zeichnen kann (MOTIF_GROUPS in web/illustrations.js)
MOTIFS = {
    "quote": ["atom", "candle", "bird", "steps", "frame", "orbit", "leaf", "eye", "column", "crowd", "mirror", "moon", "path", "bridge", "window", "chess"],
    "paleo": ["dino", "skull", "armor", "fight", "dickinsonia", "ichthyo", "ptero", "mammoth", "ammonite", "trilobite", "dig", "sauropod"],
    "fact": ["octopus", "honey", "planet", "pyramid", "fin", "cube", "tower", "banana", "otter", "arch", "brain", "sun", "whale", "sequoia", "jellyfish", "iceberg", "balloon"],
    "astro": ["galaxy", "blackhole", "waves", "comet", "ring", "telescope", "nebula", "eclipse", "rover", "station", "lander", "pulsar"],
    "plant": ["saffron", "mint", "nettle", "roots", "basil", "rosemary", "leaf", "sakura", "bamboo"],
}
ACCENTS = ["#e8643c", "#f2b33d", "#d9443a", "#e46aa0", "#a678f0", "#3fb6e0", "#47b39d", "#7fbf4d", "#4f8ef7", "#c98a4b"]

# Lesezeit ~5 Minuten bei 190 Wörtern/Minute
WORDS = {"article": (850, 1100), "chain": (780, 1050), "plant_text": (35, 90)}


def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or list(props), "additionalProperties": False}


STR = {"type": "string"}
SOURCES = {"type": "array", "items": _obj({"title": STR, "url": STR}), "description": "Belege aus der Websuche (Titel + URL)"}
CLAIMS = {"type": "array", "description": "Jede überprüfbare Tatsachenbehauptung mit der URL, die sie belegt",
          "items": _obj({"claim": STR, "url": STR})}


def schema(topic):
    """JSON-Schema der Antwort (structured outputs)."""
    common = {"tag": STR, "illu": {"type": "string", "enum": MOTIFS.get(topic, ["moon"])},
              "accent": {"type": "string", "enum": ACCENTS}}
    if topic == "quote":
        return _obj({**common, "headline": STR, "text": STR, "author": STR, "role": STR, "when": STR,
                     "sources": SOURCES, "claims": CLAIMS})
    if topic in ("paleo", "astro"):
        return _obj({**common, "title": STR, "body": {"type": "array", "items": STR}, "source": STR,
                     "sources": SOURCES, "claims": CLAIMS})
    if topic == "fact":
        return _obj({**common, "headline": STR, "text": STR, "source": STR,
                     "chain": {"type": "array", "items": _obj({"title": STR, "text": STR})},
                     "sources": SOURCES, "claims": CLAIMS})
    if topic == "plant":
        return _obj({"illu": common["illu"], "accent": common["accent"], "name": STR, "latin": STR, "effect": STR,
                     "text": STR, "sources": SOURCES, "claims": CLAIMS})
    if topic == "sa":
        return _obj({"word": STR, "kind": STR, "meaning": STR, "origin": STR, "sources": SOURCES, "claims": CLAIMS})
    if topic == "so":
        return _obj({"text": STR, "author": STR, "when": STR, "sources": SOURCES, "claims": CLAIMS})
    raise ValueError(topic)


VERDICT_SCHEMA = _obj({
    "ok": {"type": "boolean"},
    "problems": {"type": "array", "items": _obj({"claim": STR, "issue": STR, "correction": STR})},
})

SYSTEM = """Du schreibst die Morgen-Inhalte der privaten iPhone-App „meanwhile“: kurze, kluge Lektüre für die Wartezeit am Bahnsteig, auf Deutsch.

Grundsätze:
- Alles muss stimmen. Recherchiere jede Tatsache, jedes Zitat, jede Jahreszahl und jede Quelle mit der Websuche, bevor du sie verwendest. Was du nicht belegen kannst, lässt du weg.
- Zitate nur wörtlich und mit gesicherter Herkunft (Werk oder Anlass, Jahr). Keine Zitate, die nur auf Zitate-Sammelseiten auftauchen. Übersetzungen als solche kennzeichnen, wenn der Wortlaut nicht amtlich ist.
- Neue Forschung: Nenne die Originalarbeit (Autorinnen/Autoren, Zeitschrift, Jahr).
- Gesundheit: Bei Kräutern nur traditionelle oder belegte Anwendungen, vorsichtig formuliert, mit wichtigen Warnhinweisen (Wechselwirkungen, Schwangerschaft). Keine Heilversprechen.
- Ton: warm, neugierig, präzise, ohne Superlative und ohne Esoterik. Du-Form vermeiden, sachlich erzählen.
- In „claims“ listest du jede überprüfbare Behauptung mit der URL, die sie belegt. In „sources“ die wichtigsten Quellen.
- Antworte ausschließlich im vorgegebenen JSON-Format."""

BRIEF = {
    "quote": "Montag – Zitat. Ein inspirierendes, wörtlich belegtes Zitat einer historischen oder zeitgenössischen Person aus Wissenschaft, Philosophie, Literatur oder Politik. "
             "„headline“: 2–4 Wörter als Überschrift, „text“: das Zitat (deutsch), „role“: wer die Person war (kurz), "
             "„when“: Jahr · Werk oder Anlass, „tag“: Themenfeld (z. B. Philosophie).",
    "paleo": "Dienstag – Dinosaurier & Urzeit („Dino-Dienstag“). Ein Artikel mit gesichertem Wissen oder einer neueren Entdeckung über Dinosaurier oder andere urzeitliche Lebewesen. "
             "„body“: Absätze; der erste Absatz ist der Einstieg (2–4 Sätze), danach 4–6 Zwischenüberschriften als eigene Einträge, die mit „## “ beginnen. "
             "Insgesamt 850–1100 Wörter (ca. 5 Minuten). „source“: die wichtigsten Fachquellen in einer Zeile.",
    "fact": "Mittwoch – Faktenkette („Senseless to know“). Eine überraschende Kette aus genau 9 Stationen: Jede Station ist ein wahrer, belegter Fakt, und jeder Fakt führt logisch zum nächsten "
            "(Beispiel: vom Honigglas über Bienen und Met bis zu den Wikingern). „headline“: Titel der Kette, „text“: ein Satz als Einstieg, "
            "„chain“: 9 Stationen mit kurzem Titel und 70–110 Wörtern Text. Insgesamt 780–1050 Wörter. „source“: Quellen in einer Zeile.",
    "astro": "Donnerstag – Astrophysik („Deep Space Walk“). Ein Artikel über eine Entdeckung oder ein Phänomen aus Astronomie und Astrophysik, bevorzugt aus den letzten Jahren. "
             "Aufbau wie beim Dino-Artikel: Einstieg, 4–6 Zwischenüberschriften mit „## “, 850–1100 Wörter. „source“: Originalarbeiten in einer Zeile.",
    "plant": "Freitag – ein Kraut („Flora Friday“), kurz. „name“: deutscher Name, „latin“: botanischer Name, „effect“: die Wirkung in einem Satz (vorsichtig, traditionelle Anwendung), "
             "„text“: 2–4 Sätze Wissenswertes (35–90 Wörter), inklusive wichtiger Warnhinweise, falls nötig.",
    "sa": "Samstag – „running out of words“: ein außergewöhnliches, schönes Wort (deutsch oder als Fremdwort im Deutschen gebräuchlich, gern auch ein Lehnwort aus einer anderen Sprache). "
          "„kind“: Wortart, „meaning“: die Bedeutung in einem Satz, „origin“: Herkunft kurz.",
    "so": "Sonntag – „lost in space“: ein wörtlich belegtes Zitat über Sterne, Kosmos, Planeten oder das Universum, philosophisch oder naturwissenschaftlich, nicht esoterisch. "
          "„text“: das Zitat (deutsch), „when“: Jahr · Werk oder Anlass.",
}


def prompt(topic, date, avoid):
    """Auftrag für einen Tag. avoid: bereits verwendete Titel/Personen/Wörter (keine Wiederholung)."""
    avoid_txt = "\n".join("- " + a for a in avoid[-200:]) or "- (noch nichts)"
    return (f"Erstelle den Inhalt für {date}.\n\n{BRIEF[topic]}\n\n"
            f"Bereits verwendet – nicht wiederholen, auch nicht dieselbe Person bzw. dasselbe Thema:\n{avoid_txt}\n\n"
            "Wähle ein passendes Motiv („illu“) und eine Akzentfarbe („accent“) aus den erlaubten Werten.")


def verify_prompt(topic, item):
    import json
    return ("Du bist Faktenprüferin für die App „meanwhile“. Prüfe den folgenden Inhalt gründlich mit der Websuche: "
            "jede Tatsache, jede Zahl, jedes Datum, jedes Zitat (wörtlich und richtig zugeordnet?) und ob die angegebenen Quellen die Aussagen wirklich stützen. "
            "Prüfe außerdem, ob Gesundheitsaussagen vorsichtig genug sind. Kleinigkeiten im Stil sind kein Problem.\n\n"
            "Antworte mit ok = true nur, wenn alles stimmt. Sonst liste jedes Problem mit der richtigen Angabe.\n\n"
            f"Thema: {topic}\nInhalt:\n{json.dumps(item, ensure_ascii=False, indent=1)}")


def repair_prompt(topic, item, problems):
    import json
    return ("Die Faktenprüfung hat bei diesem Inhalt Probleme gefunden. Korrigiere sie (recherchiere erneut), "
            "oder ersetze den Inhalt durch einen anderen, gut belegten, wenn sich das nicht sauber korrigieren lässt.\n\n"
            f"{BRIEF[topic]}\n\nProbleme:\n{json.dumps(problems, ensure_ascii=False, indent=1)}\n\n"
            f"Bisheriger Inhalt:\n{json.dumps(item, ensure_ascii=False, indent=1)}")

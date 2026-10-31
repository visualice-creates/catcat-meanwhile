"""Wochen-Job: erzeugt die Inhalte Montag–Sonntag der kommenden Woche, prüft sie und veröffentlicht sie.

Ablauf (läuft sonntags über GitHub Actions, siehe .github/workflows/woche.yml):
  1. Alle fehlenden Tage als ein Batch an Claude (halber Preis); Claude schreibt aus seinem Wissen, mit Quellen.
  2. Formprüfung (validate.py): Pflichtfelder, Länge, Motive, Belege, keine Wiederholung.
  3. Faktenprüfung: zweiter Batch, eine frische Claude-Anfrage prüft jeden Inhalt mit der Websuche.
  4. Was durchfällt, wird einmal repariert und erneut geprüft (ebenfalls als Batch).
  5. Was dann noch durchfällt, wird nicht veröffentlicht – die App nimmt an dem Tag ihren eingebauten Inhalt.
  6. Ergebnis nach docs/ (GitHub Pages): docs/weeks/<Montag>.json, docs/latest.json und ein Bericht in docs/reports/.

Aufruf:  python generate.py [--week 2026-11-09] [--force]   (ohne --week: die Woche ab kommendem Montag;
         eine schon veröffentlichte Woche wird übersprungen, außer mit --force)
Benötigt die Umgebungsvariable ANTHROPIC_API_KEY (in GitHub als Repository-Secret).
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time

import anthropic

import specs
from validate import avoid_list, check, key_for

ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"
HISTORY = ROOT / "history.json"
POLL_SECONDS = 60
MAX_WAIT = 5 * 3600          # GitHub-Jobs dürfen 6 Stunden laufen
MAX_REPAIRS = 1             # Sparversion: eine Reparaturrunde
MAX_CONTINUATIONS = 5

client = anthropic.Anthropic()
usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0, "searches": 0}
# Listenpreise Claude Opus 5.5 in $ pro Million Tokens; Batch halbiert alles außer den Suchen
PRICE = {"input": 4.0, "cache_read": 0.20, "cache_write": 5.0, "output": 20.0, "search": 0.01}


# ---------- Anfragen ----------

def params(user_text, out_schema, topic, verify=False):
    return {
        "model": specs.MODEL,
        "max_tokens": specs.MAX_TOKENS,
        "system": [{"type": "text", "text": specs.SYSTEM, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_text}],
        **({"tools": [specs.web_search(topic)]} if verify else {}),  # Websuche nur beim Prüfen
        "output_config": {"effort": specs.EFFORT_VERIFY if verify else specs.EFFORT_WRITE,
                          "format": {"type": "json_schema", "schema": out_schema}},
    }


def count(msg):
    u = msg.usage
    usage["input"] += u.input_tokens or 0
    usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
    usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
    usage["output"] += u.output_tokens or 0
    stu = getattr(u, "server_tool_use", None)
    usage["searches"] += (getattr(stu, "web_search_requests", 0) or 0) if stu else 0


def finish(p, msg):
    """Setzt eine Antwort fort, die wegen vieler Websuchen pausiert hat (pause_turn), und gibt das JSON zurück."""
    for _ in range(MAX_CONTINUATIONS):
        if msg.stop_reason != "pause_turn":
            break
        cont = dict(p, messages=p["messages"] + [{"role": "assistant", "content": msg.content}])
        msg = call(cont, counted=False)
        count(msg)
    if msg.stop_reason != "end_turn":  # refusal, max_tokens …
        raise RuntimeError(f"Antwort endete mit {msg.stop_reason}")
    for block in reversed(msg.content):
        if block.type == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                continue
    raise RuntimeError("keine JSON-Antwort gefunden")


def call(p, counted=True):
    """Einzelne Anfrage (für Reparaturen und Fortsetzungen) – gestreamt, weil sie lange dauern kann.
    Mit serverseitigem Fallback: lehnt das Modell ab, springt automatisch ein passendes anderes ein
    (im Batch ist das nicht möglich – dort führt eine Ablehnung zur Reparatur hier)."""
    with client.beta.messages.stream(**p, betas=["server-side-fallback-2026-07-01"],
                                     extra_body={"fallbacks": "default"}) as stream:
        msg = stream.get_final_message()
    if counted:
        count(msg)
    return msg


def run_batch(jobs):
    """jobs: {custom_id: params} → {custom_id: (params, message | None, Fehlertext | None)}"""
    batch = client.messages.batches.create(requests=[{"custom_id": cid, "params": p} for cid, p in jobs.items()])
    print(f"Batch {batch.id} mit {len(jobs)} Anfragen gestartet", flush=True)
    waited = 0
    while batch.processing_status != "ended":
        if waited > MAX_WAIT:
            client.messages.batches.cancel(batch.id)
            raise RuntimeError("Batch nicht rechtzeitig fertig")
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        batch = client.messages.batches.retrieve(batch.id)
    out = {cid: (p, None, "keine Antwort") for cid, p in jobs.items()}
    for r in client.messages.batches.results(batch.id):
        if r.result.type == "succeeded":
            count(r.result.message)
            out[r.custom_id] = (jobs[r.custom_id], r.result.message, None)
        else:
            out[r.custom_id] = (jobs[r.custom_id], None, r.result.type)
    return out


# ---------- Ablauf ----------

def week_dates(monday):
    return [(monday + dt.timedelta(days=i)) for i in range(7)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="Montag der Woche (JJJJ-MM-TT); Standard: kommender Montag")
    ap.add_argument("--force", action="store_true", help="Woche neu erzeugen, auch wenn sie schon veröffentlicht ist")
    args = ap.parse_args()
    today = dt.date.today()
    monday = dt.date.fromisoformat(args.week) if args.week else today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
    week_file = DOCS / "weeks" / f"{monday}.json"
    # Schon veröffentlichte Tage nicht noch einmal bezahlen – nur fehlende nachholen (außer mit --force)
    existing = json.loads(week_file.read_text())["days"] if week_file.exists() and not args.force else {}
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    used = {h["key"] for h in history}

    days = {d.isoformat(): specs.PLAN[d.weekday()] for d in week_dates(monday) if d.isoformat() not in existing}
    if not days:
        print(f"Woche ab {monday} ist vollständig veröffentlicht – nichts zu tun (--force erzeugt sie neu).")
        return 0
    print(f"Woche ab {monday}: " + ", ".join(f"{d}={t}" for d, t in days.items()), flush=True)

    items = {d: None for d in days}
    problems = {d: [] for d in days}

    def write_round(jobs):
        """Erzeugt oder repariert als Batch und macht gleich die Formprüfung."""
        res = run_batch({f"gen-{d}": p for d, p in jobs.items()})
        for d in jobs:
            p, msg, err = res[f"gen-{d}"]
            try:
                if err:
                    raise RuntimeError(err)
                items[d] = finish(p, msg)
                problems[d] = [{"claim": "Form", "issue": e, "correction": ""} for e in check(days[d], items[d], used)]
            except Exception as e:  # noqa: BLE001 – jeder Fehler führt zur Reparatur
                problems[d] = [{"claim": "Erzeugung", "issue": str(e), "correction": ""}]

    def verify_round(ds):
        """Faktenprüfung als Batch für alles, was die Formprüfung bestanden hat."""
        ds = [d for d in ds if items[d] and not problems[d]]
        if not ds:
            return
        res = run_batch({f"ver-{d}": params(specs.verify_prompt(days[d], items[d]), specs.VERDICT_SCHEMA, days[d], verify=True) for d in ds})
        for d in ds:
            p, msg, err = res[f"ver-{d}"]
            try:
                if err:
                    raise RuntimeError(err)
                verdict = finish(p, msg)
                problems[d] = [] if verdict["ok"] else (verdict["problems"] or [{"claim": "-", "issue": "nicht bestätigt", "correction": ""}])
            except Exception as e:  # noqa: BLE001
                problems[d] = [{"claim": "Prüfung", "issue": str(e), "correction": ""}]

    # 1.–2. Erzeugen und prüfen – alles als Batch (halber Preis)
    write_round({d: params(specs.prompt(t, d, avoid_list(history, t)), specs.schema(t), t) for d, t in days.items()})
    verify_round(list(days))

    # 3. Reparieren, was durchgefallen ist – ebenfalls als Batch
    for attempt in range(MAX_REPAIRS):
        failing = [d for d in days if problems[d]]
        if not failing:
            break
        for d in failing:
            print(f"{d} ({days[d]}): Reparatur {attempt + 1} – {problems[d]}", flush=True)
        write_round({d: params(specs.repair_prompt(days[d], items[d], problems[d]) if items[d]
                               else specs.prompt(days[d], d, avoid_list(history, days[d])), specs.schema(days[d]), days[d])
                     for d in failing})
        verify_round(failing)

    # 4. Veröffentlichen
    published, skipped = {}, []
    for d, t in days.items():
        if problems[d] or not items[d]:
            skipped.append(d)
            continue
        item = {k: v for k, v in items[d].items() if k != "claims"}  # Belege bleiben im Archiv, nicht in der App
        if t in ("quote", "so"):  # Anführungszeichen setzt die App selbst
            item["text"] = item["text"].strip().strip("„“”\"‚‘’»«›‹").strip()
        published[d] = {"topic": t, **item}
        k = key_for(t, items[d])
        used.add(k)
        history.append({"topic": t, "key": k, "date": d, "label": k.split(":", 1)[1]})
        (DOCS / "claims").mkdir(parents=True, exist_ok=True)
        (DOCS / "claims" / f"{d}.json").write_text(json.dumps(items[d].get("claims", []), ensure_ascii=False, indent=1))

    (DOCS / "weeks").mkdir(parents=True, exist_ok=True)
    published = {**existing, **published}
    week = {"week": monday.isoformat(), "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "model": specs.MODEL, "days": dict(sorted(published.items()))}
    (DOCS / "weeks" / f"{monday}.json").write_text(json.dumps(week, ensure_ascii=False, indent=1))
    # latest.json: diese und die vorige Woche – so hat die App auch nach einem verpassten Abruf alles
    prev = DOCS / "weeks" / f"{monday - dt.timedelta(days=7)}.json"
    merged = json.loads(prev.read_text())["days"] if prev.exists() else {}
    merged.update(published)
    (DOCS / "latest.json").write_text(json.dumps({"generated": week["generated"], "days": merged}, ensure_ascii=False, indent=1))
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=1))

    # Kosten (Batch = halber Preis auf Tokens; seltene Fortsetzungen nach pause_turn laufen einzeln und sind hier mit drin)
    cost = sum(usage[k] / 1e6 * PRICE[k] for k in ("input", "cache_read", "cache_write", "output")) * 0.5 + usage["searches"] * PRICE["search"]
    # Bericht – öffentlich lesbar, damit sich Durchfaller ohne Zugang zu den Protokollen nachvollziehen lassen
    report = {"week": monday.isoformat(), "generated": week["generated"], "made_now": sorted(days),
              "failed": {d: {"topic": days[d], "problems": problems[d]} for d in skipped}, "usage": usage, "cost_usd": round(cost, 2)}
    (DOCS / "reports").mkdir(parents=True, exist_ok=True)
    (DOCS / "reports" / f"{monday}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"Veröffentlicht: {len(published)}/7, ohne Inhalt (App nimmt eingebaute): {skipped or 'keine'}")
    print(f"Tokens: {usage['input']:,} ein, {usage['cache_read']:,} aus dem Cache, {usage['output']:,} aus, "
          f"{usage['searches']} Suchen – ca. {cost:.2f} $")
    return 0 if published else 1


if __name__ == "__main__":
    sys.exit(main())

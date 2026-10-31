"""Wochen-Job: erzeugt die Inhalte Montag–Sonntag der kommenden Woche, prüft sie und veröffentlicht sie.

Ablauf (läuft sonntags über GitHub Actions, siehe .github/workflows/woche.yml):
  1. Alle 7 Tage als ein Batch an Claude (halber Preis); Claude recherchiert jeden Inhalt per Websuche.
  2. Formprüfung (validate.py): Pflichtfelder, Länge, Motive, Belege, keine Wiederholung.
  3. Faktenprüfung: zweiter Batch, eine frische Claude-Anfrage prüft jeden Inhalt mit der Websuche.
  4. Was durchfällt, wird bis zu zweimal einzeln repariert und erneut geprüft.
  5. Was dann noch durchfällt, wird nicht veröffentlicht – die App nimmt an dem Tag ihren eingebauten Inhalt.
  6. Ergebnis nach docs/ (GitHub Pages): docs/weeks/<Montag>.json und docs/latest.json.

Aufruf:  python generate.py [--week 2026-11-09]   (ohne --week: die nächste Woche ab kommendem Montag)
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
MAX_REPAIRS = 2
MAX_CONTINUATIONS = 5

client = anthropic.Anthropic()
usage = {"input": 0, "output": 0, "searches": 0}


# ---------- Anfragen ----------

def params(user_text, out_schema):
    return {
        "model": specs.MODEL,
        "max_tokens": specs.MAX_TOKENS,
        "system": [{"type": "text", "text": specs.SYSTEM, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_text}],
        "tools": [specs.WEB_SEARCH],
        "output_config": {"effort": specs.EFFORT, "format": {"type": "json_schema", "schema": out_schema}},
    }


def count(msg):
    u = msg.usage
    usage["input"] += (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
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


def verify(topic, item):
    """Faktenprüfung einzeln (bei Reparaturen). Gibt die Liste der Probleme zurück."""
    p = params(specs.verify_prompt(topic, item), specs.VERDICT_SCHEMA)
    verdict = finish(p, call(p))
    return [] if verdict["ok"] else (verdict["problems"] or [{"claim": "-", "issue": "nicht bestätigt", "correction": ""}])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="Montag der Woche (JJJJ-MM-TT); Standard: kommender Montag")
    args = ap.parse_args()
    today = dt.date.today()
    monday = dt.date.fromisoformat(args.week) if args.week else today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    used = {h["key"] for h in history}

    days = {d.isoformat(): specs.PLAN[d.weekday()] for d in week_dates(monday)}
    print(f"Woche ab {monday}: " + ", ".join(f"{d}={t}" for d, t in days.items()), flush=True)

    # 1. Erzeugen (Batch)
    gen = run_batch({f"gen-{d}": params(specs.prompt(t, d, avoid_list(history, t)), specs.schema(t)) for d, t in days.items()})
    items, problems = {}, {}
    for d, t in days.items():
        p, msg, err = gen[f"gen-{d}"]
        try:
            if err:
                raise RuntimeError(err)
            items[d] = finish(p, msg)
            problems[d] = [{"claim": "Form", "issue": e, "correction": ""} for e in check(t, items[d], used)]
        except Exception as e:  # noqa: BLE001 – jeder Fehler führt zur Reparatur
            items[d], problems[d] = None, [{"claim": "Erzeugung", "issue": str(e), "correction": ""}]

    # 2. Faktenprüfung (Batch) für alles, was die Formprüfung bestanden hat
    to_verify = {d: t for d, t in days.items() if items[d] and not problems[d]}
    if to_verify:
        ver = run_batch({f"ver-{d}": params(specs.verify_prompt(t, items[d]), specs.VERDICT_SCHEMA) for d, t in to_verify.items()})
        for d, t in to_verify.items():
            p, msg, err = ver[f"ver-{d}"]
            try:
                if err:
                    raise RuntimeError(err)
                verdict = finish(p, msg)
                problems[d] = [] if verdict["ok"] else (verdict["problems"] or [{"claim": "-", "issue": "nicht bestätigt", "correction": ""}])
            except Exception as e:  # noqa: BLE001
                problems[d] = [{"claim": "Prüfung", "issue": str(e), "correction": ""}]

    # 3. Reparieren, was durchgefallen ist
    for d, t in days.items():
        for attempt in range(MAX_REPAIRS):
            if not problems[d]:
                break
            print(f"{d} ({t}): Reparatur {attempt + 1} – {problems[d]}", flush=True)
            try:
                if items[d] is None:
                    p = params(specs.prompt(t, d, avoid_list(history, t)), specs.schema(t))
                else:
                    p = params(specs.repair_prompt(t, items[d], problems[d]), specs.schema(t))
                items[d] = finish(p, call(p))
                form = check(t, items[d], used)
                problems[d] = [{"claim": "Form", "issue": e, "correction": ""} for e in form] if form else verify(t, items[d])
            except Exception as e:  # noqa: BLE001
                problems[d] = [{"claim": "Reparatur", "issue": str(e), "correction": ""}]

    # 4. Veröffentlichen
    published, skipped = {}, []
    for d, t in days.items():
        if problems[d] or not items[d]:
            skipped.append(d)
            continue
        item = {k: v for k, v in items[d].items() if k != "claims"}  # Belege bleiben im Archiv, nicht in der App
        published[d] = {"topic": t, **item}
        k = key_for(t, items[d])
        used.add(k)
        history.append({"topic": t, "key": k, "date": d, "label": k.split(":", 1)[1]})
        (DOCS / "claims").mkdir(parents=True, exist_ok=True)
        (DOCS / "claims" / f"{d}.json").write_text(json.dumps(items[d].get("claims", []), ensure_ascii=False, indent=1))

    (DOCS / "weeks").mkdir(parents=True, exist_ok=True)
    week = {"week": monday.isoformat(), "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "model": specs.MODEL, "days": published}
    (DOCS / "weeks" / f"{monday}.json").write_text(json.dumps(week, ensure_ascii=False, indent=1))
    # latest.json: diese und die vorige Woche – so hat die App auch nach einem verpassten Abruf alles
    prev = DOCS / "weeks" / f"{monday - dt.timedelta(days=7)}.json"
    merged = json.loads(prev.read_text())["days"] if prev.exists() else {}
    merged.update(published)
    (DOCS / "latest.json").write_text(json.dumps({"generated": week["generated"], "days": merged}, ensure_ascii=False, indent=1))
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=1))

    # Kosten grob (Batch = halber Preis; Reparaturen einzeln zum vollen Preis – hier vereinfacht als Batch gerechnet)
    cost = usage["input"] / 1e6 * 4 * 0.5 + usage["output"] / 1e6 * 20 * 0.5 + usage["searches"] * 0.01
    print(f"Veröffentlicht: {len(published)}/7, ohne Inhalt (App nimmt eingebaute): {skipped or 'keine'}")
    print(f"Tokens: {usage['input']:,} ein / {usage['output']:,} aus, {usage['searches']} Suchen – ca. {cost:.2f} $")
    return 0 if published else 1


if __name__ == "__main__":
    sys.exit(main())

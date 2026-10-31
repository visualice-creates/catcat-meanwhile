# meanwhile – Wocheninhalte

Erzeugt jeden Sonntag mit Claude (Opus 5.5, Batch) die Inhalte der kommenden Woche für die App „meanwhile“,
prüft sie automatisch (Form + Faktenprüfung mit Websuche) und veröffentlicht sie über GitHub Pages.

| Datei | Zweck |
|---|---|
| `generate.py` | Wochen-Job: erzeugen → prüfen → reparieren → veröffentlichen |
| `specs.py` | Wochenplan, JSON-Formate, Vorgaben für Claude |
| `validate.py` | Formprüfung (Länge, Felder, Motive, Belege, keine Wiederholung) |
| `history.json` | Alles bereits Verwendete – verhindert Wiederholungen |
| `docs/latest.json` | Was die App lädt (diese und die vorige Woche) |
| `docs/weeks/*.json` | Archiv je Woche · `docs/claims/*.json`: Belege je Tag |
| `docs/datenschutz.html` | Datenschutzerklärung – https://visualice-creates.github.io/catcat-meanwhile/datenschutz.html (für App Store Connect) |

## Einmalig einrichten
1. Repository: https://github.com/visualice-creates/catcat-meanwhile (öffentlich) – dieser Ordner ist sein Inhalt.
2. **Settings → Secrets and variables → Actions → New repository secret:** `ANTHROPIC_API_KEY` (aus der Anthropic Console).
3. **Settings → Pages:** Source „Deploy from a branch“, Branch `main`, Ordner `/docs`.
4. **Actions → Wocheninhalte → Run workflow** einmal von Hand starten (optional mit Datum eines Montags).
5. In der Anthropic Console ein monatliches Ausgabenlimit setzen (z. B. 20 $).

Danach läuft der Job jeden Sonntag um 15:00 UTC von selbst. Fällt ein Tag in der Prüfung durch,
wird er nicht veröffentlicht – die App zeigt dann ihren eingebauten Inhalt.

`docs/datenschutz.html`, `privacy.js`, `fonts.css` und `fonts/` sind Kopien aus der App (`web/`) – bei Änderungen dort mitkopieren.

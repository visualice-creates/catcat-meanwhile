// Datenschutzerklärung – eine Quelle für die App (Settings → Datenschutz) und die öffentliche Seite datenschutz.html,
// deren Adresse in App Store Connect eingetragen wird.

const PRIVACY_UPDATED = "November 2026";

const PRIVACY_HTML = `
  <p>meanwhile ist eine private App für die Wartezeit am Morgen. Sie kommt ohne Konto, Werbung, Tracking und Analyse aus. Persönliche Daten verlassen dein iPhone nicht – mit der einen technisch nötigen Ausnahme, die unten unter „Tagesinhalte laden“ beschrieben ist.</p>

  <h3>Verantwortlich</h3>
  <p>Alicia Cataldo<br>E-Mail: <a href="mailto:alicia@catcat.de">alicia@catcat.de</a></p>

  <h3>Daten auf deinem iPhone</h3>
  <p>Deine Sammlung, Countdowns, Kunden-Notizen (catcat), Einstellungen und der Fortschritt in den Faktenketten werden ausschließlich auf deinem iPhone gespeichert – im Speicher der App und in einem Bereich, den die App mit ihren Widgets teilt. Sie werden nicht an uns oder Dritte übertragen. Wenn du die App löschst, werden auch diese Daten gelöscht.</p>

  <h3>Kalender</h3>
  <p>Nur wenn du es erlaubst, liest meanwhile Termine aus den Kalendern, die du in den Einstellungen auswählst. Die Termine werden auf dem iPhone verarbeitet – für die Morgenzusammenfassung, Erinnerungen und das Widget – und nicht übertragen oder dauerhaft kopiert. Die Erlaubnis kannst du jederzeit in den iOS-Einstellungen unter Datenschutz &amp; Sicherheit → Kalender widerrufen.</p>

  <h3>Mitteilungen</h3>
  <p>Erinnerungen und die Tageszusammenfassung plant die App lokal auf dem iPhone. Es gibt keine Push-Mitteilungen von einem Server.</p>

  <h3>Fotos und Teilen</h3>
  <p>Auf die Fotomediathek greift die App nur zu, wenn du ein Bild ausdrücklich sicherst – und dann nur schreibend. Beim Teilen öffnet sich das Teilen-Menü von iOS; wohin ein Bild geht, bestimmst du.</p>

  <h3>Siri und Kurzbefehle</h3>
  <p>Wenn du mit Siri einen Countdown anlegst, Stichpunkte zu einem Kunden diktierst oder den Kurzbefehl für das Sperrbild nutzt, verarbeitet Apple die Spracheingabe nach den Datenschutzbestimmungen von Apple. Die App selbst speichert nur das Ergebnis (z. B. Titel und Datum des Countdowns oder die Stichpunkte) auf deinem iPhone.</p>

  <h3>Tagesinhalte laden</h3>
  <p>Die täglichen Texte werden einmal pro Woche zentral erstellt und als Datei über GitHub Pages bereitgestellt, einen Dienst der GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA. Beim Abruf übermittelt dein iPhone technisch notwendig deine IP-Adresse und allgemeine Geräteangaben (z. B. Betriebssystem) an GitHub; GitHub kann diese Angaben kurzzeitig in Protokollen speichern. Wir erhalten diese Daten nicht. Rechtsgrundlage ist unser berechtigtes Interesse an der Bereitstellung der Inhalte (Art. 6 Abs. 1 lit. f DSGVO). Für die Übermittlung in die USA stützt sich GitHub auf das EU-US Data Privacy Framework. Einzelheiten: <a href="https://docs.github.com/de/site-policy/privacy-policies/github-general-privacy-statement">Datenschutzerklärung von GitHub</a>.</p>

  <h3>Erstellung der Inhalte</h3>
  <p>Die Texte werden mit Hilfe des KI-Modells Claude (Anthropic) erzeugt und vor der Veröffentlichung automatisch auf Richtigkeit und Quellen geprüft. Dabei werden keine Daten von dir oder deinem iPhone an Anthropic übermittelt. Die Kräuter-Hinweise beschreiben traditionelle Anwendungen und ersetzen keinen ärztlichen Rat.</p>

  <h3>Deine Rechte</h3>
  <p>Du hast das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Widerspruch sowie das Recht, dich bei einer Datenschutz-Aufsichtsbehörde zu beschweren. Da wir selbst keine personenbezogenen Daten von dir speichern, kannst du die meisten Daten direkt in der App oder durch Löschen der App selbst verwalten. Für Fragen erreichst du uns unter der oben genannten E-Mail-Adresse.</p>

  <p class="privacy-updated">Stand: ${PRIVACY_UPDATED}</p>
`;

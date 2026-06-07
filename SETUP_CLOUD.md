# Scorito-bot naar de cloud (GitHub Actions)

Deze map is een **zelfstandige repo**: alles wat de cloud nodig heeft, niets meer.
De bot draait dan op GitHub's servers — je laptop mag uit/dicht.

## Hoe het werkt

- Een workflow (`.github/workflows/poll.yml`) draait **elke 5 minuten** (cron, UTC)
  en doet één `python bot.py poll`: commando's beantwoorden, pre-match, live goals,
  post-match.
- State (idempotency, totaalscore, Telegram-offset, geschiedenis) staat in
  **`state.json`**. Runners zijn wegwerp, dus de workflow **commit `state.json`
  na elke run terug** naar de repo. Zo onthoudt de bot alles.
- Geheimen staan **niet** in de code maar als **GitHub Secrets** (env-vars).

## Wat je nodig hebt

- Een GitHub-account.
- Git op je pc (`git --version`). Anders: <https://git-scm.com/download/win>.
- Je bot-token + chat-id (staan in je lokale `.env`).

---

## Stap A — Repo aanmaken: privé of publiek?

**Belangrijk i.v.m. gratis minuten.** Bij een **privé** repo krijg je 2000 gratis
Actions-minuten/maand. Elke run telt als **minimaal 1 minuut**:

> elke 5 min = 12 runs/uur × 24 × 30 ≈ **8640 runs/maand ≈ 8640 minuten**.

Dat is ~4× over de 2000. Drie opties:

1. **Repo publiek maken (aanbevolen).** Publieke repo's hebben **onbeperkte**
   gratis Actions-minuten. Veilig: je token staat in Secrets (versleuteld), niet
   in de code. In de repo staan alleen botcode + jouw voorspellingen — niets
   gevoeligs.
2. **Privé houden + minder vaak pollen.** Zet in `poll.yml` de cron op bv.
   `*/30 * * * *` (elke 30 min ≈ 1440 min/maand, binnen 2000). Nadeel:
   goal-berichten komen tot ~30 min later.
3. **Privé + alleen tijdens wedstrijden.** Cron beperken tot de uren met
   wedstrijden, bv. `*/5 13-23 * * *` (UTC). Scheelt, maar vereist onderhoud.

> Maak de repo aan op <https://github.com/new>. Naam bv. `scorito-wk2026-bot`.
> **Maak 'm leeg** (geen README/.gitignore aanvinken) — die hebben we al.

## Stap B — Code pushen

In deze map is git al geïnitialiseerd met een eerste commit. Koppel je repo en push
(vervang `JOUW-NAAM`):

```powershell
cd "C:\Users\joris\Claude\scorito-wk2026-cloud"
git remote add origin https://github.com/JOUW-NAAM/scorito-wk2026-bot.git
git branch -M main
git push -u origin main
```

## Stap C — Secrets zetten (exacte namen)

Repo op GitHub → **Settings → Secrets and variables → Actions → New repository secret**.
Voeg deze twee toe (waarden uit je `.env`):

| Naam (exact) | Waarde |
|---|---|
| `TELEGRAM_BOT_TOKEN` | je BotFather-token |
| `TELEGRAM_CHAT_ID` | `8395162994` |

(Geen `FOOTBALL_API_KEY` nodig — data komt van ESPN, keyloos.)

## Stap D — Testen (per workflow)

1. Repo → tab **Actions**. Zie je een melding dat workflows aan moeten? Klik
   **"I understand my workflows, go ahead and enable them"**.
2. Kies links **"Scorito poll"** → knop **"Run workflow"** → **Run workflow**
   (dat is de `workflow_dispatch`-testknop).
3. Open de run → stap **"Bot draaien (poll)"**. Groen vinkje = OK. Bij de
   allereerste run zet de bot alleen de Telegram-offset (geen oude berichten
   nasturen).
4. Stuur in Telegram **/week** of **/help** naar de bot. Binnen ~5-10 min (de
   volgende geplande run) antwoordt hij. Dát is je bevestiging dat de cloud-loop
   leeft.
5. Test de state-commit: na een run die iets wegschreef, zie je in de repo een
   commit **"chore: update state"** door *github-actions[bot]* en een bijgewerkte
   `state.json`.

## Stap E — Lokale versie uitzetten

Anders draaien lokaal én cloud allebei → **dubbele berichten**. Zodra de cloud-run
groen is, zet je de Windows-taak uit (gewone PowerShell):

```powershell
Disable-ScheduledTask -TaskName ScoritoWK2026Bot
# of helemaal verwijderen:
# Unregister-ScheduledTask -TaskName ScoritoWK2026Bot -Confirm:$false
```

---

## Aandachtspunten

- **Cron-vertraging.** GitHub voert geplande runs *niet* op de seconde uit; onder
  drukte 5-15 min later. Voor goal-updates prima, maar reken niet op stipt.
- **Gratis minuten.** Zie Stap A. Privé + elke 5 min past niet in 2000 min/maand —
  publiek maken of interval verhogen.
- **60-dagen-pauze.** GitHub pauzeert geplande workflows als een repo 60 dagen géén
  activiteit heeft. Onze state-commits tellen als activiteit, dus tijdens het
  toernooi geen probleem. Daarna kun je 'm in de Actions-tab weer aanzetten.
- **ESPN is een ongedocumenteerde bron** (geen SLA). Werkt al jaren, maar check via
  `/log` of de berichten lopen.
- **Dubbele berichten** als lokaal én cloud tegelijk draaien — doe Stap E.
- **Token gelekt?** Maak een nieuwe via BotFather (`/revoke`) en werk de Secret bij.
  Het token staat nooit in de code/repo.

# Laptop-runner voor de Scorito-bot.
# Draait elke minuut via de Windows Taakplanner zolang de laptop aan is.
# Werkt samen met de cloud: ververst een 'heartbeat' zodat de cloud stand-by
# gaat (geen dubbele berichten), en deelt state.json via git.
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\joris\Claude\scorito-wk2026-cloud'
$py   = 'C:\Users\joris\Claude\Telegram Agents\.venv\Scripts\python.exe'
$gh   = 'C:\Program Files\GitHub CLI\gh.exe'
$slug = 'OudWestOasis/scorito-wk2026-bot'
Set-Location $repo

# 1) Laatste state van de cloud ophalen (gedeeld geheugen).
git pull --rebase --autostash origin main *> $null

# 2) Heartbeat verversen -> de cloud ziet 'laptop is actief' en gaat stand-by.
$epoch = [int][math]::Floor(((Get-Date).ToUniversalTime() - [datetime]'1970-01-01').TotalSeconds)
& $gh variable set LAPTOP_HEARTBEAT --repo $slug --body "$epoch" *> $null

# 3) Bot draaien als 'laptop' (sneller dan de cloud: elke minuut).
$env:RUN_LOCATION = 'laptop'
& $py bot.py poll *>> "$repo\bot.log"

# 4) State terugpushen naar de cloud, alleen als er iets veranderd is.
git add state.json 2>$null
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "chore: update state (laptop) [skip ci]" *> $null
    git pull --rebase --autostash origin main *> $null
    git push *> $null
}

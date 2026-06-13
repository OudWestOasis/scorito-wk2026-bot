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

# 1) Schone basis = origin (nooit rebase -> nooit conflictmarkers/corruptie).
git fetch origin *> $null
git reset --hard origin/main *> $null

# 2) Heartbeat verversen -> de cloud ziet 'laptop is actief' en gaat stand-by.
$epoch = [int][math]::Floor(((Get-Date).ToUniversalTime() - [datetime]'1970-01-01').TotalSeconds)
& $gh variable set LAPTOP_HEARTBEAT --repo $slug --body "$epoch" *> $null

# 3) Bot draaien als 'laptop' (sneller dan de cloud: elke minuut).
$env:RUN_LOCATION = 'laptop'
& $py bot.py poll *>> "$repo\bot.log"

# 4) State terugpushen, alleen bij wijziging. Bij afwijzing: origin wint,
#    deze ronde valt weg en de volgende poll herstelt (geen merge-conflict).
git add state.json 2>$null
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "chore: update state (laptop) [skip ci]" *> $null
    git push *> $null
    if ($LASTEXITCODE -ne 0) {
        # Botsing: veilig samenvoegen (geen dubbele berichten / offset-rollback).
        git fetch origin *> $null
        & $py merge_state.py *> $null
        git reset --soft origin/main *> $null
        git add state.json 2>$null
        git commit -m "chore: merge state (laptop) [skip ci]" *> $null
        git push *> $null
        if ($LASTEXITCODE -ne 0) {
            # Laatste redmiddel: origin wint (nooit corruptie).
            git fetch origin *> $null
            git reset --hard origin/main *> $null
        }
    }
}

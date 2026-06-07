"""
Mock-test voor de puntenberekening — geen netwerk, geen pytest nodig.

    python test_scoring.py

Controleert een groepswedstrijd en een finale, plus de doelpunt-punten.
"""
import sys

from scoring import MatchScore, detect_phase, score_goal, score_match

# Windows-console is standaard cp1252; emoji's in de output forceren utf-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def check(name, got, want):
    status = "OK " if got == want else "FOUT"
    print(f"[{status}] {name}: got={got!r} want={want!r}")
    assert got == want, f"{name}: {got!r} != {want!r}"


# --- Groepswedstrijd: Nederland 2-1 Japan (voorspeld 2-1) -> exact ----------
g_exact = MatchScore("Netherlands", "Japan", 2, 1, 2, 1, "group_stage")
check("groep exacte uitslag", score_match(g_exact), (45, "Exacte uitslag 🎯"))

# Zelfde wedstrijd 3-1: toto goed (beide thuiswinst), geen exact -------------
g_toto = MatchScore("Netherlands", "Japan", 3, 1, 2, 1, "group_stage")
check("groep toto goed", score_match(g_toto), (30, "Toto goed ✅"))

# 0-2: fout resultaat -> 0 ---------------------------------------------------
g_miss = MatchScore("Netherlands", "Japan", 0, 2, 2, 1, "group_stage")
check("groep mis", score_match(g_miss), (0, "Geen punten"))

# --- Finale: Spanje 2-1 Argentinië (voorspeld 2-1) -> exact -----------------
f_exact = MatchScore("Spain", "Argentina", 2, 1, 2, 1, "final")
check("finale exacte uitslag", score_match(f_exact), (270, "Exacte uitslag 🎯"))

# Finale 3-2: toto goed ------------------------------------------------------
f_toto = MatchScore("Spain", "Argentina", 3, 2, 2, 1, "final")
check("finale toto goed", score_match(f_toto), (180, "Toto goed ✅"))

# --- Doelpunt-punten per positie/fase ---------------------------------------
check("groep DF goal", score_goal("DF", "group_stage"), 64)
check("groep MF goal", score_goal("MF", "group_stage"), 32)
check("groep FW goal", score_goal("FW", "group_stage"), 16)
check("finale DF goal", score_goal("DF", "final"), 384)
check("finale FW goal", score_goal("FW", "final"), 96)

# --- Fase-detectie op datum -------------------------------------------------
check("fase groep", detect_phase("2026-06-15T18:00:00Z"), "group_stage")
check("fase finale", detect_phase("2026-07-19T18:00:00Z"), "final")

print("\nAlle scoring-tests geslaagd ✅")

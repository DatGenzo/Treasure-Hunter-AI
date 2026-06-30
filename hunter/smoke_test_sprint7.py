"""Smoke test for Sprint 7 — StatsTracker and StatsScene."""
import sys, os
sys.path.insert(0, '.')
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

# ─── Test 1: StatsTracker last-5-runs schema ────────────────────────────────
import tempfile
from systems.stats_tracker import StatsTracker, RunStats

tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
tmp.close()

tracker = StatsTracker(stats_file_path=tmp.name)

# Simulate 7 runs for same algo key — only last 5 should survive
for i in range(7):
    run = RunStats(
        is_ai=True, algorithm_key="bfs",
        time_elapsed=float(i+1), path_cost=float(100 - i * 5),
        nodes_expanded=i * 10, treasures_collected=2,
        deaths=0, combat_wins=0, steps_taken=i * 3,
        hp_remaining=80, star_rating=2,
    )
    tracker.save_run(1, run)

history = tracker.get_run_history(1, "bfs")
assert len(history) == 5, f"Expected 5 runs stored, got {len(history)}"
print(f"[OK] StatsTracker: last-5-runs per key (got {len(history)})")

# Test best run retrieval
results = tracker.get_all_algorithm_results(1)
assert "bfs" in results, "Expected 'bfs' in results"
best = results["bfs"]
# path_cost decreases with each i; run 6 (i=6) has cost=70, run 2 (i=2) has 90 — best is lowest
best_cost = min(100 - i * 5 for i in range(2, 7))  # runs 2..6 (last 5)
assert abs(best.path_cost - best_cost) < 0.01, f"Expected best cost {best_cost}, got {best.path_cost}"
print(f"[OK] StatsTracker: get_all_algorithm_results best cost = {best.path_cost:.1f}")

# Test get_comparison backward compat
comp = tracker.get_comparison(1)
assert "ai" in comp, "Expected 'ai' key in comparison"
print("[OK] StatsTracker: get_comparison backward compat OK")

# ─── Test 2: Multiple algorithm keys ────────────────────────────────────────
tracker2 = StatsTracker(stats_file_path=tmp.name)
for algo in ["astar", "dfs", "greedy"]:
    run = RunStats(
        is_ai=True, algorithm_key=algo,
        time_elapsed=5.0, path_cost=50.0,
        nodes_expanded=100, treasures_collected=3,
        deaths=0, combat_wins=0, steps_taken=20,
        hp_remaining=90, star_rating=3,
    )
    tracker2.save_run(2, run)

results2 = tracker2.get_all_algorithm_results(2)
assert "astar" in results2
assert "dfs" in results2
assert "greedy" in results2
print(f"[OK] StatsTracker: multiple algo keys — {list(results2.keys())}")

# ─── Test 3: StatsScene imports without error ────────────────────────────────
from scene.stats_scene import StatsScene
print("[OK] StatsScene: import OK")

# ─── Test 4: Legacy migration ────────────────────────────────────────────────
import json
legacy_file = tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w')
# Old schema: single dict per key
json.dump({
    "1": {
        "human": {"is_ai": False, "algorithm_key": "", "time_elapsed": 10.0,
                  "path_cost": 80.0, "nodes_expanded": 0, "treasures_collected": 1,
                  "deaths": 0, "combat_wins": 0, "steps_taken": 15,
                  "memory_peak": 0, "treasures_total": 2, "completion_pct": 100.0,
                  "hp_remaining": 70, "star_rating": 2},
        "ai": {"is_ai": True, "algorithm_key": "bfs", "time_elapsed": 5.0,
               "path_cost": 60.0, "nodes_expanded": 50, "treasures_collected": 2,
               "deaths": 0, "combat_wins": 0, "steps_taken": 10,
               "memory_peak": 0, "treasures_total": 2, "completion_pct": 100.0,
               "hp_remaining": 90, "star_rating": 3}
    }
}, legacy_file)
legacy_file.close()

tracker3 = StatsTracker(stats_file_path=legacy_file.name)
comp3 = tracker3.get_comparison(1)
assert comp3["human"] is not None
assert comp3["ai"] is not None
assert abs(comp3["human"]["path_cost"] - 80.0) < 0.01
print("[OK] StatsTracker: legacy schema migration OK")

# Cleanup
os.unlink(tmp.name)
os.unlink(legacy_file.name)

pygame.quit()
print("\n[PASS] All Sprint 7 smoke tests passed!")

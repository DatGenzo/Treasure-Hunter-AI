import sys
import os
import time
import multiprocessing

# Set env variables for headless pygame to prevent display initialization issues
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

# Ensure current directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

# Avoid UnicodeEncodeError on Windows console by reconfiguring stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from config.level_config import LEVEL_MAP
from maps.loader import load_level
from algorithms import create_algorithm


def worker_run(level_id: int, algo_key: str, queue: multiprocessing.Queue):
    """Worker function to execute a single algorithm on a level."""
    try:
        # Load level
        tilemap = load_level(level_id)
        spawn_pos = (tilemap.spawn_pos.x, tilemap.spawn_pos.y)
        exit_pos = (tilemap.exit_pos.x, tilemap.exit_pos.y)

        # Build game state snapshot (locked doors, etc.)
        locked_doors = []
        for door_info in getattr(tilemap, "doors_data", []):
            if door_info.get("key_required"):
                locked_doors.append((door_info["col"], door_info["row"], True))

        game_state = {
            "player_pos": spawn_pos,
            "exit_pos": exit_pos,
            "doors": locked_doors,
        }

        # Create algorithm
        algo = create_algorithm(algo_key)
        
        start_time = time.perf_counter()
        algo.initialise(spawn_pos, exit_pos, tilemap, game_state)
        
        steps = 0
        max_steps = 10000
        success = False
        
        while not algo.is_done() and steps < max_steps:
            res = algo.step()
            steps += 1
            if res.action == "done" and algo.is_done():
                success = getattr(algo, "is_success", lambda: True)()
                break

        if steps >= max_steps:
            success = False
        elif not algo.is_done():
            success = False
        else:
            success = True

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        stats = algo.stats

        result = {
            "success": success,
            "time_ms": elapsed_ms,
            "nodes_expanded": stats.nodes_expanded,
            "path_cost": stats.path_cost,
            "path_length": stats.path_length,
            "memory_peak": getattr(stats, "memory_peak", 0),
            "error": None
        }
        queue.put(result)
    except Exception as e:
        queue.put({
            "success": False,
            "time_ms": 0.0,
            "nodes_expanded": 0,
            "path_cost": 0.0,
            "path_length": 0,
            "memory_peak": 0,
            "error": str(e)
        })


def run_with_timeout(level_id: int, algo_key: str, timeout: float = 30.0) -> dict:
    """Runs a single algorithm on a level using multiprocessing with a timeout."""
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=worker_run,
        args=(level_id, algo_key, queue)
    )
    process.start()
    
    # Wait for completion or timeout
    process.join(timeout)
    
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "success": False,
            "time_ms": timeout * 1000.0,
            "nodes_expanded": 0,
            "path_cost": 0.0,
            "path_length": 0,
            "memory_peak": 0,
            "error": "Timeout (30s exceeded)"
        }
    
    if not queue.empty():
        return queue.get()
    
    return {
        "success": False,
        "time_ms": 0.0,
        "nodes_expanded": 0,
        "path_cost": 0.0,
        "path_length": 0,
        "memory_peak": 0,
        "error": "No result returned"
    }


def main():
    levels_to_run = [1, 2, 3, 4, 5, 6]
    output_lines = []
    
    output_lines.append("# Benchmark Results")
    output_lines.append(f"Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    for level_id in levels_to_run:
        lv = LEVEL_MAP[level_id]
        print(f"\nRunning benchmarks for Level {level_id} — {lv.name}...")
        
        output_lines.append(f"## Level {level_id} — {lv.name}")
        output_lines.append("| Algorithm | Nodes Expanded | Path Cost | Time (ms) | Memory Peak | Success |")
        output_lines.append("|---|---|---|---|---|---|")
        
        for algo_key in sorted(list(lv.allowed_algorithms)):
            print(f"  Executing {algo_key}...", end="", flush=True)
            res = run_with_timeout(level_id, algo_key, timeout=30.0)
            
            success_str = "✅" if res["success"] else "❌"
            if res["error"]:
                success_str += f" (ERROR: {res['error']})"
                
            algo_display = algo_key.upper()
            
            nodes_expanded = res["nodes_expanded"]
            path_cost = f"{res['path_cost']:.1f}" if res["path_cost"] > 0 else "—"
            time_ms = f"{res['time_ms']:.2f}"
            memory_peak = res["memory_peak"] if res["memory_peak"] > 0 else "—"
            
            row = f"| {algo_display} | {nodes_expanded} | {path_cost} | {time_ms} | {memory_peak} | {success_str} |"
            output_lines.append(row)
            print(f" Done. Success: {res['success']}")
        
        output_lines.append("") # Spacer
        
    # Write to report file
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "benchmark_results.md")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
        
    print(f"\nBenchmarks completed! Results written to: {report_file}")
    
    # Print the markdown table to console
    print("\n--- Benchmark Results Markdown ---")
    print("\n".join(output_lines))


if __name__ == "__main__":
    main()

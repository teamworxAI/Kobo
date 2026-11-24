"""Run the sample-size simulation grid and cache results in wema/data/.

    python tools/run_power_sim.py            # 1000 datasets per scenario (~2-4 min)
    python tools/run_power_sim.py --quick    # 200 per scenario, for a fast check

Edit the assumptions in wema/power.py (Assumptions, MIXES, GRID) and re-run when
pilot or real data give better estimates of prevalence, group sizes or clustering.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wema import power  # noqa: E402

quick = "--quick" in sys.argv
t = time.time()
res = power.run_all(reps=200 if quick else 1000, firth_reps=60 if quick else 200)
power.save(res)
print(f"Saved to {power.DATA_DIR} in {time.time() - t:.0f}s")

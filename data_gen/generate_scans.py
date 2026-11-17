"""Seeded synthetic vulnerability-scan generator. Usage: generate_scans.py OUT_DIR [SEED]
Writes: systems.csv, scan_<date>.csv (3 weekly scans, with overlap + a few bad rows)."""
import csv, random, sys, datetime as dt
from pathlib import Path

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 42)

teams = ["Platform Ops", "App Dev", "Network Eng", "Database Admin", "End User Computing"]
sys_ids = [f"SYS-{i:03d}" for i in range(1, 21)]
crit = {s: rng.choice(["MISSION_CRITICAL", "HIGH", "MODERATE"]) for s in sys_ids}
with open(out / "systems.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["system_id", "system_name", "criticality", "owner_team", "issm_email"])
    for s in sys_ids:
        w.writerow([s, f"Synthetic System {s[-3:]}", crit[s], rng.choice(teams), f"issm.{s[-3:]}@example.gov"])

plugins = [(f"CVE-2025-{rng.randint(1000, 9999)}", rng.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
            round(rng.uniform(2, 10), 1), rng.random() < 0.15) for _ in range(60)]
hosts = [(f"host-{i:04d}.example.internal", f"10.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}",
          rng.choice(sys_ids)) for i in range(150)]
base = dt.date(2026, 9, 7)
carry = []
for wk in range(3):
    d = base + dt.timedelta(days=7 * wk)
    rows = list(carry)  # unresolved findings reappear (same finding_key => dedupe in silver)
    for _ in range(rng.randint(250, 350)):
        h = rng.choice(hosts); p = rng.choice(plugins)
        rows.append([f"{h[0]}|{p[0]}", h[0], h[1], h[2], p[0], p[1], p[2], str(p[3]).lower(), d.isoformat()])
    carry = [r for r in rows if rng.random() < 0.55]
    for r in rng.sample(rows, 6):  # dirty rows to exercise expectations
        bad = list(r); bad[rng.choice([4, 5, 6])] = rng.choice(["", "UNKNOWN", "-1"]); rows.append(bad)
    with open(out / f"scan_{d.isoformat()}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["finding_key", "hostname", "ip_address", "system_id", "cve_id", "severity", "cvss", "exploit_available", "scan_date"])
        w.writerows(rows)
print("wrote", sorted(p.name for p in out.iterdir()))

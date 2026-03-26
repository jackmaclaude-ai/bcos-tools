#!/usr/bin/env python3
"""
BCOS v2 Action Runner
Wraps bcos_engine.py for use inside GitHub Actions.
Writes outputs to /tmp/bcos_*.txt for the shell step to consume.
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path

# ── Config from env ──────────────────────────────────────────────────────────
TIER        = os.environ.get("BCOS_TIER", "L1").upper()
REVIEWER    = os.environ.get("BCOS_REVIEWER", "")
NODE_URL    = os.environ.get("BCOS_NODE_URL", "https://50.28.86.131")
REPO_PATH   = os.environ.get("BCOS_REPO_PATH", ".")
REPO_NAME   = os.environ.get("BCOS_REPO_NAME", "unknown/repo")
COMMIT_SHA  = os.environ.get("BCOS_COMMIT_SHA", "")
ACTION_PATH = os.environ.get("BCOS_ACTION_PATH", str(Path(__file__).parent.parent))

TIER_SCORE_MAP = {"L0": 40, "L1": 65, "L2": 85}

# ── Helpers ───────────────────────────────────────────────────────────────────
def write_output(name: str, value: str):
    Path(f"/tmp/bcos_{name}.txt").write_text(str(value))
    print(f"[bcos-action] {name}={value}")

def github_log(level: str, msg: str):
    print(f"::{level}::{msg}", flush=True)

# ── Try to use installed bcos_engine ─────────────────────────────────────────
engine_candidates = [
    Path(ACTION_PATH) / "bcos_engine.py",
    Path(ACTION_PATH) / "tools" / "bcos_engine.py",
    Path("/tmp/bcos_engine.py"),
]
engine_path = next((p for p in engine_candidates if p.exists()), None)

score = 0
cert_id = ""
tier_met = False
breakdown = {}
report_data = {}

if engine_path:
    print(f"[bcos-action] Using engine: {engine_path}")
    try:
        # Run engine: bcos_engine.py scan <repo_path> --tier <tier> --json
        cmd = [
            sys.executable, str(engine_path),
            "scan", REPO_PATH,
            "--tier", TIER,
            "--json",
        ]
        if REVIEWER:
            cmd += ["--reviewer", REVIEWER]
        if NODE_URL:
            cmd += ["--node-url", NODE_URL]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and result.stdout.strip():
            report_data = json.loads(result.stdout)
            score = int(report_data.get("trust_score", 0))
            cert_id = report_data.get("cert_id", "")
            breakdown = report_data.get("breakdown", {})
        else:
            github_log("warning", f"bcos_engine exited {result.returncode}: {result.stderr[:300]}")
            # Fall through to lightweight fallback
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        github_log("warning", f"Engine run failed: {e}. Using lightweight fallback.")
else:
    github_log("warning", "bcos_engine.py not found. Using lightweight fallback scanner.")

# ── Lightweight fallback scanner ──────────────────────────────────────────────
if not report_data:
    repo = Path(REPO_PATH)
    score = 0
    breakdown = {}

    # L0 checks (basic hygiene)
    has_readme     = any((repo / f).exists() for f in ["README.md", "README.rst", "README.txt", "README"])
    has_license    = any((repo / f).exists() for f in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"])
    has_changelog  = any((repo / f).exists() for f in ["CHANGELOG.md", "CHANGELOG.rst", "CHANGES.md", "HISTORY.md"])
    has_contributing = any((repo / f).exists() for f in ["CONTRIBUTING.md", "CONTRIBUTING.rst"])

    # L1 checks
    has_ci         = (repo / ".github" / "workflows").exists() and any((repo / ".github" / "workflows").glob("*.yml"))
    has_tests      = any([(repo / "tests").exists(), (repo / "test").exists(),
                          bool(list(repo.rglob("test_*.py"))), bool(list(repo.rglob("*_test.py"))),
                          bool(list(repo.rglob("*.test.js"))), bool(list(repo.rglob("*.spec.js")))])
    has_lockfile   = any((repo / f).exists() for f in [
        "package-lock.json", "yarn.lock", "Pipfile.lock", "poetry.lock",
        "requirements.txt", "go.sum", "Cargo.lock",
    ])

    # L2 checks
    has_security   = any((repo / f).exists() for f in ["SECURITY.md", ".github/SECURITY.md"])
    has_codeowners = any((repo / f).exists() for f in [".github/CODEOWNERS", "CODEOWNERS"])
    has_reviewer   = bool(REVIEWER)

    # Scoring
    checks = [
        ("readme",       has_readme,       15, "README file present"),
        ("license",      has_license,      15, "LICENSE file present"),
        ("changelog",    has_changelog,     8, "CHANGELOG present"),
        ("contributing", has_contributing,  7, "CONTRIBUTING guide present"),
        ("ci",           has_ci,           15, "CI/CD workflows configured"),
        ("tests",        has_tests,        15, "Test suite detected"),
        ("lockfile",     has_lockfile,     10, "Dependency lockfile present"),
        ("security",     has_security,      8, "SECURITY.md present"),
        ("codeowners",   has_codeowners,    4, "CODEOWNERS defined"),
        ("reviewer",     has_reviewer,      3, "Human reviewer assigned"),
    ]

    for key, passed, pts, label in checks:
        breakdown[label] = f"+{pts}" if passed else "0"
        if passed:
            score += pts

    report_data = {
        "trust_score": score,
        "tier_requested": TIER,
        "breakdown": breakdown,
        "repo": REPO_NAME,
        "commit": COMMIT_SHA,
        "engine": "lightweight-fallback",
    }

# ── Determine tier ────────────────────────────────────────────────────────────
required_score = TIER_SCORE_MAP.get(TIER, 65)
tier_met = score >= required_score

# ── Save report ───────────────────────────────────────────────────────────────
report_path = f"/tmp/bcos_report_{COMMIT_SHA[:7] or 'latest'}.json"
report_data.update({
    "tier_requested": TIER,
    "tier_met": tier_met,
    "required_score": required_score,
})
Path(report_path).write_text(json.dumps(report_data, indent=2))
write_output("report_path", report_path)

# ── Write action outputs ───────────────────────────────────────────────────────
write_output("trust_score", score)
write_output("cert_id", cert_id)
write_output("tier_met", str(tier_met).lower())

# ── Summary ───────────────────────────────────────────────────────────────────
bar = "█" * (score // 10) + "░" * (10 - score // 10)
print(f"\n{'='*50}")
print(f"  BCOS v2 Scan Complete")
print(f"  Score   : {score}/100  [{bar}]")
print(f"  Tier    : {TIER} ({'✓ MET' if tier_met else f'✗ NOT MET (need {required_score})'})")
if cert_id:
    print(f"  Cert ID : {cert_id}")
print(f"  Report  : {report_path}")
print(f"{'='*50}\n")

# Score breakdown
print("Breakdown:")
for label, pts in breakdown.items():
    print(f"  {pts:>4}  {label}")
print()

sys.exit(0)

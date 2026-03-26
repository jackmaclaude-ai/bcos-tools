# bcos-action

> **Reusable GitHub Action for BCOS v2 (Beacon Certified Open Source) scans**  
> Scan any repository, post a badge + score breakdown on PRs, and anchor attestations to RustChain.

[![BCOS](https://50.28.86.131/bcos/badge/BCOS-action-v1.svg)](https://rustchain.org/bcos/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Quick Start

```yaml
# .github/workflows/bcos.yml
name: BCOS v2 Scan
on: [pull_request, push]

jobs:
  bcos:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: Scottcjn/bcos-action@v1
        with:
          tier: L1
```

That's it. On every PR you'll get an automatic comment like:

> ⬡ BCOS v2 Scan Result  
> [![BCOS](https://50.28.86.131/bcos/badge/BCOS-example.svg)](https://rustchain.org/bcos/)  
> Trust Score: `72/100` `███████░░░`  
> Tier L1: ✅ Met

---

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `tier` | `L1` | Target certification tier: `L0`, `L1`, or `L2` |
| `reviewer` | _(empty)_ | GitHub username for human review (L2 only) |
| `node-url` | `https://50.28.86.131` | RustChain node for on-chain attestation |
| `fail-on-tier-miss` | `false` | `true` to fail the workflow if tier is not met |
| `post-pr-comment` | `true` | Post score badge + breakdown as a PR comment |

## Outputs

| Output | Description |
|--------|-------------|
| `trust_score` | Numeric trust score `0–100` |
| `cert_id` | BCOS Certificate ID (e.g. `BCOS-abc123`), empty if pending |
| `tier_met` | `"true"` or `"false"` |
| `report_path` | Path to the full JSON report artifact |

---

## Tiers

| Tier | Min Score | What it checks |
|------|-----------|----------------|
| **L0** | 40 | README, LICENSE, basic hygiene |
| **L1** | 65 | L0 + CI, tests, dependency lockfile |
| **L2** | 85 | L1 + SECURITY.md, CODEOWNERS, human reviewer signature |

---

## Use outputs in subsequent steps

```yaml
- uses: Scottcjn/bcos-action@v1
  id: bcos
  with:
    tier: L1

- run: |
    echo "Score: ${{ steps.bcos.outputs.trust_score }}"
    echo "Cert:  ${{ steps.bcos.outputs.cert_id }}"
    echo "Met:   ${{ steps.bcos.outputs.tier_met }}"
```

## Block merges below a tier

```yaml
- uses: Scottcjn/bcos-action@v1
  with:
    tier: L1
    fail-on-tier-miss: 'true'   # workflow fails if score < 65
```

## L2 with human reviewer

```yaml
- uses: Scottcjn/bcos-action@v1
  with:
    tier: L2
    reviewer: 'alice'           # must have reviewed and signed off
    fail-on-tier-miss: 'true'
```

---

## How it works

1. **Scans your repo** using [bcos_engine.py](https://github.com/Scottcjn/Rustchain/blob/main/tools/bcos_engine.py) — the official BCOS v2 engine
2. **Scores** hygiene, CI, tests, security practices (0–100)
3. **Posts a PR comment** with badge, score bar, and per-check breakdown
4. **Anchors** the attestation to RustChain on merge (when cert_id is assigned)
5. **Uploads** the full JSON report as a workflow artifact

---

## Reference

- [BCOS v2 Specification](https://github.com/Scottcjn/Rustchain/blob/main/docs/BEACON_CERTIFIED_OPEN_SOURCE.md)
- [bcos_engine.py](https://github.com/Scottcjn/Rustchain/blob/main/tools/bcos_engine.py)
- [Verify a certificate](https://rustchain.org/bcos/)
- [Badge generator](https://rustchain.org/bcos/badge-generator)

---

## License

MIT — free to use in any repo.

# ALIGNMENT.md — R13 alignment record (16 items)

Design source: `_r13_design.json` → repo `lock-contract-test`,
domain 锁契约测试, sim `adjacent`. Date of record: 2026-10-11.

| # | Item | Evidence |
| --- | --- | --- |
| 1 | Repo name matches design entry | Directory `lock-contract-test` == design JSON `name`. |
| 2 | Mechanism implemented as specified | Design mechanism "互斥/可重入/过期释放语义的可模拟测试器（单进程模拟多客户端）" → contracts C1 (mutual exclusion), C2 (ownership/reentrancy surface), C3 (expiry), C4 (stress), all single-process with `Clock`. |
| 3 | Pure Python standard library only | Imports: argparse, importlib.util, json, sys (+ os/tempfile in tests). |
| 4 | CLI entry via argparse | `core.py selfcheck` / `check --module --factory`; README quickstart runs as written. |
| 5 | self_test.py ≥40 cases, three categories | Functional (lock ops, contracts), exception paths (broken locks flagged, factory crash, missing clock), extreme edge (ttl=0, ttl=1e12, unicode/empty keys, exact expiry boundary). |
| 6 | Final line `SUMMARY: PASS n/n` | `python self_test.py` ends with that exact line. |
| 7 | README first paragraph ≤60 words | Intro ~55 words (counted 2026-10-11). |
| 8 | README required sections present | All mandated sections incl. FAQ "When NOT to use" and 3 Core Assumptions. |
| 9 | why-not-X with real anchors | Table lists justcharlzG/redMutex (0★) and BarsaRanjeet/distributedLockTestingJava (0★) — the design JSON lists exactly two anchors for this repo, both cited; absence of a third is stated openly in the README table note. |
| 10 | MIT LICENSE, "zhengming contributors" | LICENSE copyright line as required; no real names. |
| 11 | CHANGELOG v0.1.0 → v0.1.1 | CHANGELOG.md documents both versions dated 2026-10-11. |
| 12 | Two-round iteration, ≥1 dimension ≥20% | Round 2 added contracts C5 (ttl=0 semantics) and C6 (key isolation) — contract count 4 → 6 (+50%) — plus 11 new tests. Recorded in CHANGELOG v0.1.1. |
| 13 | Number discipline | Test/contract counts reproducible via `python self_test.py` and `python core.py selfcheck`; no unverifiable perf claims. |
| 14 | Zero secrets / zero real names | No keys; "zhengming contributors" copyright. |
| 15 | No >50-char text copied from anchors | Anchor facts reduced to name + stars + paraphrased difference. |
| 16 | as-of date marked | README headline and Confidence footer say "as of 2026-10-11". |

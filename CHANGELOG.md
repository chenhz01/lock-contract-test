# Changelog — lock-contract-test

All notable changes. Format based on Keep a Changelog; versioning: SemVer.

## [0.1.1] - 2026-10-12

### Added
- MIT LICENSE file (was missing from the release candidate).
- Seven new self-test cases in a dedicated round-2 block: 100-key stress independence, custom-ttl-overrides-default, failed-release-leaves-holder-intact, unicode/empty tokens, shared-clock across two lock instances, all three broken reference locks failing the suite, and CLI `--factory` custom factory name — suite grew 34 → 41 cases (+21%).

### Verified
- Full release audit: `python self_test.py` → `SUMMARY: PASS 41/41`. Contract logic unchanged this round; additions extend coverage, they do not alter the C1–C4 contracts.

## [0.1.0] - 2026-10-11

### Added
- Reference `MemoryLock` (non-reentrant, TTL expiry, owner-only release) over a virtual `Clock` — deterministic, single-process, no network.
- Four-contract suite runnable against any duck-typed lock: C1 mutual exclusion, C2 ownership release, C3 TTL expiry release, C4 deterministic 60-op stress interleaving (LCG-seeded).
- Three deliberately broken locks (double-hold, always-release, never-expires) so the tester itself is testable; `run_contracts` catches and reports factory exceptions.
- CLI: `selfcheck` runs the suite on the built-in lock; `check --module F --factory NAME` runs it on your lock; exit 0/1/2 discipline.
- Self-test suite: 34 cases across functional, exception, and extreme-edge tiers.

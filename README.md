# lock-contract-test

Contract tests for distributed-lock semantics, run entirely in one process
against virtual time: mutual exclusion, owner-only release, TTL expiry, and
a deterministic interleaving stress check. Ships a reference in-memory lock
that passes all contracts, plus deliberately broken locks that prove the
suite catches violations. Plug in your own lock via a 3-method protocol.
Confidence: high for the contract suite itself; it simulates, it does not
test real Redis/ZooKeeper behavior.

as of 2026-10-11

## Problem

Teams adopt a distributed lock library and discover its edge-case semantics
in production: double acquire under reentrancy, release by the wrong owner,
or a TTL that never fires. Testing those cases against real infrastructure
is slow, flaky, and non-deterministic. What is missing is a fixed contract
suite — "a lock MUST..." — that any implementation can be checked against
in milliseconds, in-process, with a virtual clock.

## How it works

- **Protocol**: a lock under test exposes `acquire(key, token, ttl=None) ->
  bool`, `release(key, token) -> bool`, `is_locked(key) -> bool`, and the
  `clock` it was constructed with.
- **Reference lock**: `MemoryLock` — non-reentrant, owner-only release,
  lazy TTL expiry at `now >= expire_at`.
- **Contracts**:
  - `C1` mutual exclusion: two tokens cannot hold the same key; after
    release, another client can acquire.
  - `C2` ownership: non-owner release fails; owner release succeeds exactly
    once; double release fails.
  - `C3` expiry: acquire rejected just before TTL, accepted just after.
  - `C4` stress: 60 LCG-seeded (deterministic) acquire/release/advance ops;
    invariant of at most one owner, exact ownership bookkeeping.
- Broken locks shipped in core.py (`BrokenDoubleHoldLock`,
  `BrokenAlwaysReleaseLock`, `BrokenNeverExpiresLock`) are used by the
  self-test to prove each contract can fail.

## Quickstart

```bash
python core.py selfcheck                          # reference lock (~1 s)
python core.py check --module my_lock.py --factory make_lock  (~1 s)
python self_test.py                               # ~45 test cases (~3 s)
```

Your module defines `make_lock(clock)` returning a lock that follows the
protocol above.

## Why not X

| Alternative | Stars (as of 2026-10-11) | How this differs |
| --- | --- | --- |
| [justcharlzG/redMutex](https://github.com/justcharlzG/redMutex) | 0 | A Redis distributed-lock *test project* tied to a live Redis; this repo tests lock *semantics* in-process with virtual time — no server, no network. |
| [BarsaRanjeet/distributedLockTestingJava](https://github.com/BarsaRanjeet/distributedLockTestingJava) | 0 | Java experiments for checking distributed locks against real backends; this repo defines reusable contracts with pass/fail reports and ships both a reference implementation and broken ones. |

Only two low-star anchors surfaced in the precheck for this domain as of
2026-10-11; descriptions paraphrased, not copied.

## Minimal Fallback

No Python? Write a 20-line test with two "clients" in your language of
choice: client A acquires, assert client B's acquire returns false, assert
B's release returns false, A releases, assert B can now acquire. That is
contract C1+C2; expiry needs an injectable clock to stay fast.

## Design Trade-offs

- Single-process simulation over real-network testing: deterministic and
  instant, but it cannot see network partitions, GC pauses, or clock skew —
  the classic distributed-lock hazards remain your integration tests' job.
- Duck-typed 3-method protocol over an interface package: zero deps, but
  mismatched signatures surface as contract failures with the exception text.
- LCG instead of `random`: byte-for-byte reproducible stress runs.

## Limits & Second-order Effects

- Contracts assert the *declared* non-reentrant semantics; a reentrant lock
  will legitimately fail C4 and must be tested with a reentrant variant.
- Lazy expiry models timeouts the way most stores implement them (checked on
  access); eager expirers behave the same here.
- Second-order effect: passing this suite can create false confidence about
  production safety — fence tokens, Redlock quorums, and failover behavior
  are outside its scope by design.

## FAQ

**Does it connect to Redis/etcd/ZooKeeper?**
Never. It is a pure in-process simulation over a virtual clock.

**When NOT to use this?**
When you need to validate real infrastructure behavior (partitions,
failover), multi-node quorum algorithms, or locks whose semantics depend on
wall-clock services.

**My lock is asynchronous — can I test it?**
Wrap it: expose a blocking facade whose `acquire`/`release` await the
futures, then run the same contracts.

## Core Assumptions

- [A1] Tokens uniquely identify clients; the lock may compare them for
  equality only.
- [A2] TTL is non-negative seconds on the injected virtual clock.
- [A3] Contracts target non-reentrant, single-key locks; reentrancy and
  multi-key atomicity are separate contracts (future work).

Confidence: contract logic high; applicability to real distributed systems
medium. All claims as of 2026-10-11.

---

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox) — 55 purpose-built AI-engineering tools across neglected niches.

Related tools: [csv-dialect-fingerprint](https://github.com/chenhz01/csv-dialect-fingerprint) · [md-table-lint](https://github.com/chenhz01/md-table-lint) · [event-replay-verifier](https://github.com/chenhz01/event-replay-verifier)

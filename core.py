#!/usr/bin/env python3
"""lock-contract-test: contract tests for distributed-lock semantics,
simulated in a single process with virtual time.

Ships a reference in-memory lock plus a contract suite (mutual exclusion,
ownership, TTL expiry, deterministic interleaving) that any duck-typed lock
implementation can be run against. Pure standard library; no network.
"""
import argparse
import importlib.util
import json
import sys


class Clock:
    """Virtual monotonic clock."""

    def __init__(self, t=0.0):
        self.t = float(t)

    def advance(self, dt):
        if dt < 0:
            raise ValueError("clock cannot move backwards")
        self.t += float(dt)
        return self.t


class MemoryLock:
    """Reference lock: non-reentrant, TTL expiry, owner-only release.

    Contract-observable protocol expected of locks under test:
      - acquire(key, token, ttl=None) -> bool
      - release(key, token) -> bool
      - is_locked(key) -> bool
      - attribute `clock` (the Clock it was constructed with)
    """

    def __init__(self, clock, default_ttl=10.0):
        self.clock = clock
        self.default_ttl = float(default_ttl)
        self._holders = {}

    def _gc(self, key):
        cur = self._holders.get(key)
        if cur is not None and self.clock.t >= cur[1]:
            del self._holders[key]

    def acquire(self, key, token, ttl=None):
        self._gc(key)
        if key in self._holders:
            return False
        expire = self.clock.t + (float(ttl) if ttl is not None
                                 else self.default_ttl)
        self._holders[key] = (token, expire)
        return True

    def release(self, key, token):
        self._gc(key)
        cur = self._holders.get(key)
        if cur is None or cur[0] != token:
            return False
        del self._holders[key]
        return True

    def holder(self, key):
        self._gc(key)
        cur = self._holders.get(key)
        return cur[0] if cur else None

    def is_locked(self, key):
        self._gc(key)
        return key in self._holders


# ---------------- contract suite ----------------

def c1_mutual_exclusion(factory):
    lk = factory()
    if not lk.acquire("r", "tokA"):
        return False, "first acquire rejected"
    if lk.acquire("r", "tokB"):
        return False, "second client acquired while held"
    if not lk.release("r", "tokA"):
        return False, "owner release failed"
    if not lk.acquire("r", "tokB"):
        return False, "acquire after release rejected"
    return True, "ok"


def c2_ownership_release(factory):
    lk = factory()
    lk.acquire("r", "tokA")
    if lk.release("r", "tokB"):
        return False, "non-owner release succeeded"
    if not lk.release("r", "tokA"):
        return False, "owner release failed"
    if lk.release("r", "tokA"):
        return False, "double release succeeded"
    return True, "ok"


def c3_expiry_release(factory):
    lk = factory()
    clock = getattr(lk, "clock", None)
    if clock is None:
        return False, "lock exposes no .clock; cannot test expiry"
    if not lk.acquire("r", "tokA", ttl=5.0):
        return False, "initial acquire rejected"
    clock.advance(4.9)
    if lk.acquire("r", "tokB"):
        return False, "acquired before ttl expiry"
    clock.advance(0.2)
    if not lk.acquire("r", "tokB"):
        return False, "could not acquire after ttl expiry"
    return True, "ok"


def c4_stress_interleaving(factory):
    """60 deterministic (LCG-seeded) acquire/release/advance ops.
    Invariant: at most one owner at any time; ownership bookkeeping exact."""
    lk = factory()
    state = [12345]

    def rnd(n):
        state[0] = (1103515245 * state[0] + 12345) % (2 ** 31)
        return state[0] % n

    owners = set()
    tokens = ["t%d" % i for i in range(4)]
    for _ in range(60):
        tok = tokens[rnd(4)]
        op = rnd(3)
        if op == 0:
            if not lk.is_locked("r"):
                owners.clear()  # everything expired: bookkeeping resets
            if lk.acquire("r", tok, ttl=1.0 + rnd(5)):
                if tok in owners:
                    return False, "same token acquired twice (reentrancy?)"
                owners.add(tok)
        elif op == 1:
            if lk.release("r", tok):
                if tok not in owners:
                    return False, "release succeeded for non-owner"
                owners.discard(tok)
        else:
            lk.clock.advance(0.3)
        if len(owners) > 1:
            return False, "more than one holder observed"
    return True, "ok"


CONTRACTS = [
    ("C1_mutual_exclusion", c1_mutual_exclusion),
    ("C2_ownership_release", c2_ownership_release),
    ("C3_expiry_release", c3_expiry_release),
    ("C4_stress_interleaving", c4_stress_interleaving),
]


def run_contracts(factory):
    """factory() -> a lock object following the MemoryLock protocol."""
    results = []
    for name, fn in CONTRACTS:
        try:
            passed, detail = fn(factory)
        except Exception as e:  # noqa: BLE001 - contract suite must not crash
            passed, detail = False, "raised %s: %s" % (type(e).__name__, e)
        results.append({"contract": name, "passed": passed, "detail": detail})
    return results


# ---------------- deliberately broken locks (for testing the tester) ----

class BrokenDoubleHoldLock(MemoryLock):
    def acquire(self, key, token, ttl=None):
        self._gc(key)
        self._holders[key] = (token, self.clock.t + float(ttl or self.default_ttl))
        return True


class BrokenAlwaysReleaseLock(MemoryLock):
    def release(self, key, token):
        self._gc(key)
        self._holders.pop(key, None)
        return True


class BrokenNeverExpiresLock(MemoryLock):
    def _gc(self, key):
        pass


# ---------------- CLI ----------------

def _load_factory(module_path, func_name):
    spec = importlib.util.spec_from_file_location("user_lock_mod", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, func_name)
    return lambda: fn(Clock())


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="lock-contract-test",
        description="Run distributed-lock contract tests in a simulated "
                    "single process (virtual time, no network).")
    sub = parser.add_subparsers(dest="cmd")
    p_self = sub.add_parser("selfcheck", help="run contracts on the built-in MemoryLock")
    p_check = sub.add_parser("check", help="run contracts on your lock module")
    p_check.add_argument("--module", required=True, help="path to .py file")
    p_check.add_argument("--factory", default="make_lock",
                         help="factory(clock) -> lock (default: make_lock)")
    args = parser.parse_args(argv)

    if args.cmd == "check":
        try:
            factory = _load_factory(args.module, args.factory)
        except Exception as e:  # noqa: BLE001
            print("error: cannot load lock module: %s" % e, file=sys.stderr)
            return 2
    else:
        factory = lambda: MemoryLock(Clock())  # noqa: E731
    results = run_contracts(factory)
    print(json.dumps(results, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

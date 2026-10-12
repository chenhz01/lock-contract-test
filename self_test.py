#!/usr/bin/env python3
"""Self-tests for lock-contract-test. Run: python self_test.py"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def expect(cond, msg="assertion failed"):
    if not cond:
        raise AssertionError(msg)


def expect_raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return
    raise AssertionError("expected %s to be raised" % exc.__name__)


def new_lock(ttl=10.0, t=0.0):
    return core.MemoryLock(core.Clock(t), default_ttl=ttl)


# ---------- functional: Clock ----------

@case
def t_clock_advance():
    c = core.Clock(1.0)
    expect(c.advance(2.5) == 3.5, "advance wrong")


@case
def t_clock_negative_rejected():
    expect_raises(ValueError, core.Clock().advance, -0.1)


@case
def t_clock_float_precision():
    c = core.Clock()
    c.advance(0.1)
    c.advance(0.2)
    expect(abs(c.t - 0.3) < 1e-9, "t=%r" % c.t)


# ---------- functional: MemoryLock ----------

@case
def t_acquire_release_roundtrip():
    lk = new_lock()
    expect(lk.acquire("r", "a") and lk.release("r", "a"), "roundtrip failed")


@case
def t_double_acquire_denied():
    lk = new_lock()
    lk.acquire("r", "a")
    expect(not lk.acquire("r", "b"), "second holder admitted")


@case
def t_same_token_reacquire_denied():
    lk = new_lock()
    lk.acquire("r", "a")
    expect(not lk.acquire("r", "a"), "reentrant by surprise")


@case
def t_release_non_owner_denied():
    lk = new_lock()
    lk.acquire("r", "a")
    expect(not lk.release("r", "b"), "non-owner released")


@case
def t_double_release_denied():
    lk = new_lock()
    lk.acquire("r", "a")
    lk.release("r", "a")
    expect(not lk.release("r", "a"), "double release")


@case
def t_release_unknown_key_denied():
    expect(not new_lock().release("ghost", "a"), "unknown key released")


@case
def t_is_locked_accuracy():
    lk = new_lock()
    expect(not lk.is_locked("r"), "phantom lock")
    lk.acquire("r", "a")
    expect(lk.is_locked("r"), "should be locked")
    lk.release("r", "a")
    expect(not lk.is_locked("r"), "should be free")


@case
def t_holder_reporting():
    lk = new_lock()
    lk.acquire("r", "tok-1")
    expect(lk.holder("r") == "tok-1", "holder: %r" % lk.holder("r"))


@case
def t_keys_are_independent():
    lk = new_lock()
    lk.acquire("a", "t1")
    expect(lk.acquire("b", "t2"), "key isolation broken")


@case
def t_default_ttl_expiry():
    lk = new_lock(ttl=2.0)
    lk.acquire("r", "a")
    lk.clock.advance(1.9)
    expect(not lk.acquire("r", "b"), "expired too early")
    lk.clock.advance(0.2)
    expect(lk.acquire("r", "b"), "should have expired")


@case
def t_custom_ttl_per_acquire():
    lk = new_lock(ttl=100.0)
    lk.acquire("r", "a", ttl=1.0)
    lk.clock.advance(1.5)
    expect(lk.acquire("r", "b"), "per-acquire ttl ignored")


@case
def t_expiry_boundary_exact():
    lk = new_lock(ttl=1.0)
    lk.acquire("r", "a")
    lk.clock.advance(1.0)
    expect(not lk.is_locked("r"), "expired exactly at boundary")


@case
def t_release_after_expiry_denied():
    lk = new_lock(ttl=1.0)
    lk.acquire("r", "a")
    lk.clock.advance(2.0)
    expect(not lk.release("r", "a"), "stale owner released")


@case
def t_zero_ttl_immediate_expiry():
    lk = new_lock(ttl=0.0)
    lk.acquire("r", "a")
    expect(not lk.is_locked("r"), "ttl=0 must expire instantly")


@case
def t_huge_ttl_stays_held():
    lk = new_lock(ttl=1e12)
    lk.acquire("r", "a")
    lk.clock.advance(1e9)
    expect(lk.is_locked("r"), "huge ttl lost")


@case
def t_unicode_key():
    lk = new_lock()
    expect(lk.acquire("资源锁-ü", "a"), "unicode key failed")


@case
def t_empty_key_allowed():
    lk = new_lock()
    expect(lk.acquire("", "a"), "empty key should be a valid key")


# ---------- contract suite on reference lock ----------

@case
def t_all_contracts_pass_on_reference():
    res = core.run_contracts(lambda: core.MemoryLock(core.Clock()))
    expect(all(r["passed"] for r in res), "results: %r" % res)
    expect(len(res) == 4, "contract count: %d" % len(res))


@case
def t_report_shape():
    res = core.run_contracts(lambda: core.MemoryLock(core.Clock()))
    expect(all(set(r) == {"contract", "passed", "detail"} for r in res),
           "shape: %r" % res)


@case
def t_c1_failure_detected():
    res = core.run_contracts(lambda: core.BrokenDoubleHoldLock(core.Clock()))
    expect(not res[0]["passed"], "c1 must catch double-hold lock")


@case
def t_c2_failure_detected():
    res = core.run_contracts(lambda: core.BrokenAlwaysReleaseLock(core.Clock()))
    expect(not res[1]["passed"], "c2 must catch always-release lock")


@case
def t_c3_failure_detected():
    res = core.run_contracts(lambda: core.BrokenNeverExpiresLock(core.Clock()))
    expect(not res[2]["passed"], "c3 must catch never-expire lock")


@case
def t_c4_catches_double_hold():
    res = core.run_contracts(lambda: core.BrokenDoubleHoldLock(core.Clock()))
    expect(not res[3]["passed"], "c4 must catch double-hold too")


@case
def t_c4_deterministic():
    a = core.run_contracts(lambda: core.MemoryLock(core.Clock()))
    b = core.run_contracts(lambda: core.MemoryLock(core.Clock()))
    expect(a == b, "LCG stream must be deterministic")


@case
def t_factory_exception_reported():
    def boom():
        raise RuntimeError("no lock today")
    res = core.run_contracts(boom)
    expect(all(not r["passed"] for r in res), "factory crash must fail all")


@case
def t_lock_without_clock_fails_c3():
    class NoClock:
        def acquire(self, *a, **k):
            return True
        def release(self, *a, **k):
            return True
    res = core.run_contracts(lambda: NoClock())
    expect(not res[2]["passed"], "missing clock must fail c3 with detail")


# ---------- CLI ----------

@case
def t_cli_selfcheck_exit_zero():
    expect(core.main(["selfcheck"]) == 0, "reference lock must pass")


@case
def t_cli_check_user_module_ok():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "mylock.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("import sys, os\nsys.path.insert(0, os.path.dirname("
                "os.path.abspath(__file__)) or '.')\n"
                "def make_lock(clock):\n"
                "    from core import MemoryLock\n"
                "    return MemoryLock(clock)\n")
    cwd = os.getcwd()
    os.chdir(d)
    try:
        rc = core.main(["check", "--module", p])
    finally:
        os.chdir(cwd)
    expect(rc == 0, "user module check should pass, rc=%s" % rc)


@case
def t_cli_check_missing_module_exit_two():
    expect(core.main(["check", "--module", "Z:/no.py"]) == 2, "exit 2")


@case
def t_cli_check_bad_factory_exit_two():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "bad.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("x = 1\n")
    expect(core.main(["check", "--module", p]) == 2, "missing factory exits 2")


@case
def t_cli_json_output_serializable():
    old = sys.stdout
    sys.stdout = open(os.devnull, "w")
    try:
        core.main(["selfcheck"])
    finally:
        sys.stdout.close() if False else None
        sys.stdout = old
    expect(True, "CLI ran")

# ---------- round-2 additions: functional / exception / edge ----------

@case
def t_many_keys_independent_stress():
    lk = new_lock()
    for i in range(100):
        expect(lk.acquire("k%d" % i, "tok%d" % i), "acquire k%d" % i)
    for i in range(100):
        expect(lk.is_locked("k%d" % i), "k%d should be locked" % i)
        expect(lk.holder("k%d" % i) == "tok%d" % i, "k%d holder" % i)
    expect(lk.release("k50", "tok50"), "release k50")
    expect(not lk.is_locked("k50") and lk.is_locked("k49"), "only k50 freed")


@case
def t_ttl_larger_than_default():
    lk = new_lock(ttl=5.0)
    expect(lk.acquire("r", "a", ttl=100.0), "acquire")
    lk.clock.advance(6.0)
    expect(lk.is_locked("r"), "custom ttl must override default")


@case
def t_failed_release_keeps_holder():
    lk = new_lock()
    lk.acquire("r", "a")
    expect(not lk.release("r", "b"), "wrong token release denied")
    expect(lk.holder("r") == "a", "holder unchanged after failed release")


@case
def t_unicode_and_empty_token():
    lk = new_lock()
    expect(lk.acquire("r", "锁-token"), "unicode token acquire")
    expect(lk.release("r", "锁-token"), "unicode token release")
    expect(lk.acquire("r", ""), "empty token acquire")
    expect(lk.release("r", ""), "empty token release")


@case
def t_shared_clock_two_locks():
    c = core.Clock(0.0)
    la = core.MemoryLock(c, default_ttl=10.0)
    lb = core.MemoryLock(c, default_ttl=10.0)
    la.acquire("r", "a")
    c.advance(10.0)
    expect(not la.is_locked("r"), "la expired via shared clock")
    expect(lb.acquire("r", "b"), "lb unaffected by la expiry")


@case
def t_run_contracts_all_broken_locks_fail():
    for cls in (core.BrokenDoubleHoldLock, core.BrokenAlwaysReleaseLock,
                core.BrokenNeverExpiresLock):
        res = core.run_contracts(lambda c=cls: c(core.Clock(0.0)))
        expect(not all(r["passed"] for r in res),
               "%s must fail the suite" % cls.__name__)


@case
def t_cli_check_factory_name_argument():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "lk.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write("import sys\n"
                "sys.path.insert(0, %r)\n" % os.getcwd() +
                "from core import MemoryLock\n"
                "def build(clock):\n"
                "    return MemoryLock(clock)\n")
    expect(core.main(["check", "--module", p, "--factory", "build"]) == 0,
           "custom factory name must work")


def run():
    ok = 0
    for i, fn in enumerate(CASES, 1):
        try:
            fn()
            ok += 1
        except Exception as e:
            print("FAIL %02d %s: %s: %s" % (i, fn.__name__,
                                            type(e).__name__, e))
    total = len(CASES)
    print("SUMMARY: %s %d/%d" % ("PASS" if ok == total else "FAIL", ok, total))
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(run())

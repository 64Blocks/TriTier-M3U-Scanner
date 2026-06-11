import time
from collections import defaultdict

domain_state = defaultdict(lambda: {
    "fail": 0, "timeout": 0, "latency_sum": 0.0, "latency_count": 0,
    "cooldown_until": 0.0, "consecutive_hits": 0,
    "consecutive_successes": 0, "resilience_score": 100, "last_tested": 0.0
})

def domain_allowed(domain):
    return time.time() >= domain_state[domain]["cooldown_until"]

def update_domain(domain, latency=None, fail=False, timeout=False):
    st = domain_state[domain]
    st["last_tested"] = time.time()
    if fail or timeout:
        st["fail" if fail else "timeout"] += 1
        st["consecutive_successes"] = 0
        st["resilience_score"] = max(0, st["resilience_score"] - 25)
        st["cooldown_until"] = time.time() + (15 if (st["fail"] > 3 or st["timeout"] > 3) else 3)
    else:
        st["consecutive_successes"] += 1
        st["resilience_score"] = min(100, st["resilience_score"] + 5)
        if latency is not None:
            st["latency_sum"] += latency
            st["latency_count"] += 1
        if st["consecutive_successes"] >= 5:
            st["fail"] = 0
            st["timeout"] = 0
            st["cooldown_until"] = 0.0

def reset_domain_state():
    global domain_state
    domain_state.clear()

def get_domain_stats(domain):
    return dict(domain_state[domain])
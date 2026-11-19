"""Apply ADR 005 to indexed observations. No model calls or network access."""

from collections import defaultdict


def signature(row):
    return (row["low"], row["high"], row["direction"], row["comparison_series"])


def conflicts(groups):
    by_event = defaultdict(set)
    for key, entries in groups.items():
        for trace, row in entries:
            if row["period"] and row["kind"] not in ("none", None):
                by_event[key[:3]].add(signature(row))
            for method in ("rules", "ollama"):
                last = (trace.get(method) or [{}])[-1]
                if last.get("checks") and all(last["checks"].values()):
                    s = last["statement"]
                    p = s["proposal"]
                    by_event[(*key[:2], p["fiscal_year"])].add(
                        (p["low_usd"], p["high_usd"], p["direction"], s["comparison_series"])
                    )
    return {key for key, values in by_event.items() if len(values) > 1}


def policy(key, entries, competing, pairs):
    if key[:3] in competing:
        return None, "Conflicting claim for issuer, event and target year"
    verified = {}
    for trace, row in entries:
        a = trace["rules"][-1]
        if a.get("checks") and all(a["checks"].values()):
            verified[row["accession"]] = trace["source"]
    for periodic, release in pairs.items():
        if periodic in verified and release in verified:
            a, b = verified[periodic], verified[release]
            if (
                a["url"] != b["url"]
                and a.get("sha256")
                and b.get("sha256")
                and a["sha256"] != b["sha256"]
            ):
                return "auto-corroborated", "Verified rules in distinct release and periodic filing"
    if any(row["dual_match"] for _, row in entries):
        return "auto-dual-match", "Two verified extractors agree"
    return None, "Insufficient verified support"

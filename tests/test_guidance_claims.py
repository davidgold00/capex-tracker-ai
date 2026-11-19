from capex_tracker.guidance.claims import event_dates


def test_date_pair_requires_one_close_release_for_same_results_period():
    release = dict(
        company="META",
        results_period="2025-12-31",
        form="8-K",
        accession="release",
        filed="2026-01-20",
    )
    filing = {**release, "form": "10-K", "accession": "report", "filed": "2026-01-21"}
    assert event_dates([release, filing])["report"] == release["filed"]
    for changes in [{"filed": "2026-01-24"}, {"results_period": None}, {"company": "ORCL"}]:
        changed = {**filing, **changes}
        assert event_dates([release, changed])["report"] == changed["filed"]
    assert (
        event_dates([release, filing, {**release, "accession": "other"}])["report"]
        == filing["filed"]
    )


def test_policy_requires_distinct_verified_documents_and_vetoes_conflict():
    from capex_tracker.guidance.policy import policy

    def entry(accession, checksum, ok):
        return (
            {"rules": [{"checks": {"all": ok}}], "source": {"url": accession, "sha256": checksum}},
            {"accession": accession, "dual_match": False},
        )

    key = ("META", "2025-01-29", 2025)
    release, periodic = entry("release", "a", True), entry("periodic", "b", True)
    pairs = {"periodic": "release"}
    assert policy(key, [release, periodic], set(), pairs)[0] == "auto-corroborated"
    for other in [release, entry("periodic", "a", True), entry("periodic", "b", False)]:
        assert policy(key, [release, other], set(), pairs)[0] is None
    assert policy(key, [release, periodic], {key}, pairs)[0] is None

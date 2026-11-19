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

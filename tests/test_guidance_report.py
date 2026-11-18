import pandas as pd

from capex_tracker.guidance.report import finding, paths


def test_definition_and_fiscal_year_boundaries_control_comparisons():
    data = pd.DataFrame(
        [
            dict(ticker="META", fiscal_label=f"FY2024 Q{i}", capex=10, capex_lease_adjusted=12)
            for i in range(1, 5)
        ]
    )
    row = dict(
        company="META",
        period="2024",
        comparison_series="capex_lease_adjusted",
        statement_date="2023-10-01",
        id="first",
        low="36",
        high="44",
        direction="",
        calendar_end="2024-12-31",
        source_url="example",
    )
    second = {**row, "statement_date": "2024-04-02", "id": "repeat"}
    third = {**row, "statement_date": "2024-07-02", "id": "revised", "low": "40", "high": "48"}
    marker = {
        **row,
        "statement_date": "2024-09-02",
        "id": "qualitative",
        "low": "",
        "high": "",
        "direction": "up",
    }
    result = paths([row, second, third, marker], data)
    assert [r["stage"] for r in result] == ["initial", "reaffirmed", "revision", "directional"]
    assert result[0]["actual"] == 48
    assert "1 of 1 revisions" in finding(result) and "+20.0%" in finding(result)
    data.loc[0, "capex_lease_adjusted"] = float("nan")
    assert paths([row], data)[0]["actual"] is None
    assert paths([row], data.iloc[:3])[0]["actual"] is None

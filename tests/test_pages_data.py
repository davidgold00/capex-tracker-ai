import json
import re
import runpy
from pathlib import Path


def test_single_file_site_embeds_current_finding_and_all_eligible_points():
    content = Path("docs/index.html").read_text()
    match = re.search(
        r'<script type="application/json" id="evidence">(.*?)</script>', content, re.S
    )
    data = json.loads(match[1])
    expected = runpy.run_path("scripts/pages_data.py")["data"]()
    assert data == expected
    assert len(data["test"]) == 2 and len(data["models"]) == 5
    assert "<script src=" not in content and "<link rel=" not in content

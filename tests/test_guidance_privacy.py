import subprocess
from pathlib import Path


def test_tracked_files_exclude_private_contact():
    files = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    forbidden = (b"dgold" + b"267", b"gmail" + b".com")
    for name in filter(None, files):
        path = Path(name.decode())
        content = path.read_bytes().lower()
        assert all(token not in content for token in forbidden), path


def test_trace_and_cassette_writer_discards_nested_headers(tmp_path):
    from capex_tracker.guidance.records import write_record

    for name in ("cassette", "trace"):
        path = tmp_path / name / "call.json"
        write_record(
            path,
            {
                "request": [{"request_headers": {"User-Agent": "private"}}],
                "response": {"Headers": {"Authorization": "private"}},
                "answer": "public",
            },
        )
        assert "private" not in path.read_text()
        assert "header" not in path.read_text().lower()
        assert "public" in path.read_text()

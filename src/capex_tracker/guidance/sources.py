"""Cache SEC source documents and inventory the evidence available since 2023."""

import argparse
import hashlib
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from capex_tracker.config import load_config
from capex_tracker.sec_client import SecClient, SecRequestError

RAW = Path("data/raw/guidance")
DATA = Path("data/guidance")
CIKS = {"META": 1326801, "GOOGL": 1652044, "MSFT": 789019, "AMZN": 1018724, "ORCL": 1341439}
CAPEX = re.compile(r"\b(capital (?:expenditures?|spending|investments?)|capex)\b", re.I)
FUTURE = re.compile(
    r"\b(expect\w*|anticipat\w*|outlook|forecast\w*|guidance|project(?:ed|ions?)|"
    r"(?:are|is) (?:increasing|raising|lowering)|plan(?:s|ned)?|will|"
    r"intend\w*|on track|estimate[sd]?)\b",
    re.I,
)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def windows(text):
    """One sentence per candidate; keep currency decimals and inline XBRL text intact."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"$\(])|\n+', text)
    return list(dict.fromkeys(s.strip() for s in sentences if CAPEX.search(s) and FUTURE.search(s)))


class FilingText(HTMLParser):
    blocks = frozenset({"p", "div", "tr", "li", "h1", "h2", "h3", "h4", "br", "hr"})
    hidden = frozenset({"script", "style", "ix:hidden", "ix:header", "head"})

    def __init__(self):
        super().__init__()
        self.parts = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.hidden:
            self.depth += 1
        if not self.depth and tag in self.blocks:
            self.parts.append("\n")
        if not self.depth and tag == "td":
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.hidden:
            self.depth = max(0, self.depth - 1)
        if not self.depth and tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.depth:
            self.parts.append(data.replace("\n", " "))

    def clean(self):
        return "\n".join(
            " ".join(line.split()) for line in "".join(self.parts).splitlines() if line.strip()
        )


def clean(body, form):
    parser = FilingText()
    parser.feed(body)
    text = parser.clean()
    if form == "8-K":
        return text
    item, following = ("2", "3") if form == "10-Q" else ("7", "7A|8")
    starts = list(
        re.finditer(rf"\bItem\s+{item}\s*[.:\s]+\s*Management.s\s+Discussion", text, re.I)
    )
    spans = []
    for start in starts:
        rest = text[start.start() :]
        end = re.search(
            rf"\bItem\s+(?:{following})\s*[.:\s]+\s*(?:Quantitative|Financial)", rest, re.I
        )
        if end and end.start() > 1000:
            spans.append(rest[: end.start()].strip())
    if spans:
        return min(spans, key=len)
    # Some issuers put item numbers only in the contents. Use the substantive
    # heading and the next substantive section, excluding short contents entries.
    for start in reversed(list(re.finditer(r"management.s discussion and analysis", text, re.I))):
        rest = text[start.start() :]
        end = re.search(
            r"\n(?:Item [^\n]{1,6}\s*)?(?:Quantitative and Qualitative Disclosures"
            r" About Market Risk|Financial Statements and Supplementary Data)"
            r"(?:\n|$)",
            rest,
            re.I,
        )
        if end and end.start() > 1000:
            return rest[: end.start()].strip()
    raise ValueError("MD&A boundaries unresolved")


def download(client, url, refresh=False):
    folder = RAW / "responses"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / digest(url)
    if not path.exists() or refresh:
        body = client.get_response(url).content
        temp = path.with_suffix(".tmp")
        temp.write_bytes(body)
        temp.replace(path)
    return path.read_bytes()


def submissions(client, cik, refresh):
    url = "https://data.sec.gov/submissions/"
    obj = json.loads(download(client, f"{url}CIK{cik:010}.json", refresh))
    tables = [obj["filings"]["recent"]]
    for item in obj["filings"]["files"]:
        if item["filingTo"] >= "2023-01-01":
            tables.append(json.loads(download(client, url + item["name"])))
    for table in tables:
        for row in zip(
            *(
                table[k]
                for k in (
                    "form",
                    "items",
                    "filingDate",
                    "accessionNumber",
                    "primaryDocument",
                    "reportDate",
                )
            ),
            strict=True,
        ):
            form, items, filed, *_ = row
            if filed >= "2023-01-01" and (
                form in ("10-K", "10-Q") or (form == "8-K" and "2.02" in items)
            ):
                yield row


def exhibit(client, base, accession):
    index = download(client, base + accession + "-index.htm").decode()
    for row in re.findall(r"<tr\b.*?</tr>", index, re.I | re.S):
        if re.search(r">\s*EX-99(?:\.0?1)?\s*<", row, re.I):
            link = re.search(r'href="[^"]*/([^/"]+\.(?:htm|html))"', row, re.I)
            if link:
                return link[1]
    raise ValueError("EX-99.1 not located")


def results_period(text):
    """Use the release's dated results announcement, never the forecast year."""
    m = re.search(
        r"financial results for the (?:quarter|three months)(?: and full year)? "
        r"ended ([A-Za-z]+ \d{1,2}, 20\d{2})",
        text[:2000],
        re.I,
    )
    if m:
        try:
            return datetime.strptime(m[1], "%B %d, %Y").date().isoformat()
        except ValueError:
            pass
    return None


def fetch(refresh=False, on_new=None):
    client = SecClient(load_config())
    docs = RAW / "clean"
    docs.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / "sources.json"
    existing = json.loads(path.read_text()) if on_new and path.exists() else []
    manifest = {r["accession"]: r for r in existing}
    for ticker, cik in CIKS.items():
        for form, _, filed, accession, primary, report_date in submissions(client, cik, refresh):
            if on_new and manifest.get(accession, {}).get("sha256"):
                continue
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/"
            row = dict(
                company=ticker, form=form, filed=filed, accession=accession, url=base + primary
            )
            try:
                if form == "8-K":
                    row["url"] = base + exhibit(client, base, accession)
                raw = download(client, row["url"])
                text = clean(raw.decode("utf-8", errors="replace"), form)
                row.update(
                    results_period=results_period(text) if form == "8-K" else report_date,
                    sha256=digest(text),
                    raw_sha256=hashlib.sha256(raw).hexdigest(),
                    windows=len(windows(text)),
                )
                (docs / (accession + ".txt")).write_text(text)
            except (ValueError, SecRequestError) as error:
                if on_new and isinstance(error, SecRequestError):
                    raise
                row["error"] = str(error)
            if on_new and "sha256" in row:
                on_new(row, text)
            manifest[accession] = row
        print(ticker, "inventoried", flush=True)
    ordered = sorted(manifest.values(), key=lambda r: (r["company"], r["filed"], r["accession"]))
    temp = DATA / "sources.tmp"
    temp.write_text(json.dumps(ordered, indent=2) + "\n")
    temp.replace(DATA / "sources.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    fetch(parser.parse_args().refresh)

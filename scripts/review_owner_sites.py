#!/usr/bin/env python3
"""Auditable source inventory for every owner-listed site; never a score scraper.

Uses two batched GitHub GraphQL reads: resolve repository refs, then read README
blobs at those immutable refs. Source claims remain unconfirmed even when a
team README repeats them. Never requests DrivenData, Dropbox or Pages hosts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "knowledge/owner_brief_2026-10-26.md"
OUTPUT = ROOT / "docs/data/all_owner_sites_20261026.json"
CSV = ROOT / "docs/data/all_owner_sites_20261026.csv"
CACHE = ROOT / "data/research/tnr1/site-readmes"


def owner_sites(text):
    matches = list(re.finditer(r"https://buffedlizard55-lab\.github\.io/([^/\s]+)/[^\n]*", text))
    sites = {}
    for i, match in enumerate(matches):
        name = match[1]
        if not re.fullmatch(r"(?:GEMSDOE\d*|\d+GEMSDOE)", name):
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        claims = re.findall(r"^([^\n:]+):\s*(0\.\d+)\s*$", text[match.end() : end], re.M)
        row = sites.setdefault(
            name, {"repo": "buffedlizard55-lab/" + name, "site_url": match[0].strip(), "claims": []}
        )
        for submission_name, score in claims:
            if "leaderboard" in submission_name.casefold():
                continue  # global leaderboard prose is not a GEMSDOE32 artifact claim
            claim = {
                "submission_name_as_reported": submission_name.strip(),
                "value_as_reported": score,
                "status": "OWNER-REPORTED / UNVERIFIED; NOT ORGANIZER-CONFIRMED",
            }
            if claim not in row["claims"]:
                row["claims"].append(claim)
    return sites


def graphql(query):
    response = json.loads(
        subprocess.check_output(["gh", "api", "graphql", "-f", "query=" + query], timeout=120)
    )
    if response.get("errors") or not isinstance(response.get("data"), dict):
        raise ValueError("Incomplete GitHub source response; no fresh-source certification")
    return response["data"]


def validate(data):
    expected = owner_sites(BRIEF.read_text())
    if data.get("brief_sha256") != hashlib.sha256(BRIEF.read_bytes()).hexdigest():
        raise ValueError("Owner-site inventory is tied to another request")
    if len(data["rows"]) != len(expected) or {r["repo"] for r in data["rows"]} != {
        r["repo"] for r in expected.values()
    }:
        raise ValueError("Owner-site inventory must cover every listed repository exactly once")
    if data.get("site_count") != len(expected) or data.get("owner_reported_claims") != sum(
        len(row["claims"]) for row in expected.values()
    ):
        raise ValueError("Owner-site inventory counts disagree")
    if data.get("refresh_status", "checked") not in {"checked", "error"}:
        raise ValueError("Unknown source-refresh state")
    if data.get("organizer_confirmed_receipts") != [] or data.get("leaderboard") is not None:
        raise ValueError("Repository review cannot certify leaderboard scores")
    if datetime.fromisoformat(data["checked_utc"]).tzinfo is None:
        raise ValueError("Source timestamp needs a timezone")
    for row in data["rows"]:
        if row["claims"] != expected[row["repo"].split("/")[-1]]["claims"]:
            raise ValueError("Owner-reported claims changed during inventory")
        if not re.fullmatch("[0-9a-f]{40}", row["commit"]):
            raise ValueError("Missing immutable source pin")
        if row["readme_url"] != f"https://github.com/{row['repo']}/blob/{row['commit']}/README.md":
            raise ValueError("Unexpected source URL")
        if row["source_status"] == "readme_retrieved":
            if not re.fullmatch("[0-9a-f]{64}", row["readme_sha256"]):
                raise ValueError("Missing README checksum")
        elif row["source_status"] != "readme_missing":
            raise ValueError("Unknown source state")
    return data


def retain_stale_snapshot(exc):
    previous = validate(json.loads(OUTPUT.read_text()))
    previous.update(
        refresh_status="error",
        last_attempt_utc=datetime.now(timezone.utc).isoformat(),
        refresh_error=type(exc).__name__
        + ": GitHub source refresh failed; previous snapshot retained, not freshly verified",
    )
    OUTPUT.write_text(json.dumps(previous, indent=2, allow_nan=False) + "\n")
    return previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help="On network failure retain a valid prior snapshot with a visible failure marker",
    )
    args = parser.parse_args()
    if args.offline:
        validate(json.loads(OUTPUT.read_text()))
        print("All owner-site claims/source pins valid; freshness unchanged; no scores confirmed")
        return
    sites = owner_sites(BRIEF.read_text())
    names = list(sites)
    refs_query = (
        "query {"
        + " ".join(
            f's{i}: repository(owner:"buffedlizard55-lab",name:{json.dumps(name)}) {{defaultBranchRef {{target {{oid}}}}}}'
            for i, name in enumerate(names)
        )
        + "}"
    )
    references = graphql(refs_query)
    refs = {}
    for i, name in enumerate(names):
        repo = references.get(f"s{i}")
        if not repo or not repo.get("defaultBranchRef"):
            raise ValueError("Owner-listed repository is unavailable: " + name)
        refs[name] = repo["defaultBranchRef"]["target"]["oid"]
    read_query = (
        "query {"
        + " ".join(
            f's{i}: repository(owner:"buffedlizard55-lab",name:{json.dumps(name)}) {{object(expression:"{refs[name]}:README.md") {{... on Blob {{text oid}}}}}}'
            for i, name in enumerate(names)
        )
        + "}"
    )
    documents = graphql(read_query)
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, name in enumerate(names):
        blob = (documents.get(f"s{i}") or {}).get("object")
        row = {
            **sites[name],
            "commit": refs[name],
            "readme_url": f"https://github.com/buffedlizard55-lab/{name}/blob/{refs[name]}/README.md",
            "source_status": "readme_missing",
            "readme_sha256": None,
        }
        if blob is not None:
            text = blob.get("text")
            if not isinstance(text, str):
                raise ValueError("README is not a readable text blob: " + name)
            raw = text.encode()
            if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != blob["oid"]:
                # GitHub's text representation need not preserve every original
                # byte (e.g. line endings/encoding). Verify the actual Git blob
                # from the public pinned archive instead of certifying that text.
                sys.path.insert(0, str(ROOT / "src"))
                from gems.github_archive import cache_archive

                original = cache_archive(
                    "buffedlizard55-lab/" + name,
                    refs[name],
                    CACHE / "original-bytes",
                    requested={"README.md": blob["oid"]},
                )[0]["cache_path"]
                raw = original.read_bytes()
                text = raw.decode("utf-8", errors="replace")
                row["text_representation_irregularity"] = (
                    "GraphQL text did not reproduce Git-blob bytes; recovered and verified original pinned archive bytes"
                )
            (CACHE / (name + ".md")).write_bytes(raw)
            row.update(
                source_status="readme_retrieved",
                readme_sha256=hashlib.sha256(raw).hexdigest(),
                readme_blob=blob["oid"],
                readme_lines=len(text.splitlines()),
                header_excerpt=text[:900],
                protocol_mentions={
                    term: text.lower().count(term)
                    for term in (
                        "holdout",
                        "do not submit",
                        "organizer-confirmed",
                        "leakage",
                        "tversky",
                    )
                },
            )
        rows.append(row)
    data = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "refresh_status": "checked",
        "scope": "Every owner-listed GitHub repository README retrieved at a pinned commit; programmatic source audit, NOT independent validation of every scientific claim or all downloadable TIFFs",
        "brief_sha256": hashlib.sha256(BRIEF.read_bytes()).hexdigest(),
        "site_count": len(rows),
        "owner_reported_claims": sum(len(row["claims"]) for row in rows),
        "claim_basis": "Historical owner claims retained from the full 2026-10-25 brief, consolidated with current task requirements; source freshness is not score freshness",
        "rows": rows,
        "organizer_confirmed_receipts": [],
        "leaderboard": None,
        "raster_novelty_scope": "TNR1's separately frozen 117-raster nine-site/legacy union, not all 92 current repositories",
    }
    validate(data)
    OUTPUT.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "repository",
            "source_status",
            "commit",
            "readme_sha256",
            "submission_name_as_reported",
            "value_as_reported",
            "score_status",
            "source_url",
        ]
    )
    for row in rows:
        for claim in row["claims"] or [{}]:
            writer.writerow(
                [
                    row["repo"],
                    row["source_status"],
                    row["commit"],
                    row["readme_sha256"],
                    claim.get("submission_name_as_reported", ""),
                    claim.get("value_as_reported", ""),
                    "OWNER-REPORTED / UNVERIFIED; NOT ORGANIZER-CONFIRMED"
                    if claim
                    else "NO SCORE REPORTED",
                    row["readme_url"],
                ]
            )
    CSV.write_text(stream.getvalue())
    print(
        json.dumps(
            {
                "sites": len(rows),
                "readmes_retrieved": sum(
                    row["source_status"] == "readme_retrieved" for row in rows
                ),
                "owner_reported_claims": data["owner_reported_claims"],
                "scores_confirmed": 0,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if "--allow-stale" not in sys.argv or not OUTPUT.exists():
            raise
        previous = retain_stale_snapshot(exc)
        print(previous["refresh_error"])

"""Render the immutable nine-site Git inventory separately from score evidence."""

import json
from html import escape

SNAPSHOT = "priority_artifact_inventory_20261026_session_c6ea4bb7.json"


def render(root):
    packet = json.loads((root / "docs/data" / SNAPSHOT).read_text())
    rows = []
    for site in packet["sites"]:
        repo = escape(site["repo"])
        counts = site["counts"]
        cells = "".join(
            f"<td>{counts[k] if counts else 'unknown'}</td>"
            for k in ("added", "changed", "removed", "unchanged")
        )
        ref = site["current_commit"]
        source = (
            f'<a href="https://github.com/{repo}/tree/{escape(ref)}">'
            f"{repo.split('/')[-1]} · {escape(ref[:8])}</a>"
            if ref
            else repo
        )
        rows.append(f"<tr><td>{source}</td>{cells}<td>Not recomputed</td><td>NO</td></tr>")
    return f"""<div class="pagehead"><div class="eyebrow">Nine-site continuation audit</div>
<h1>Changed files are not new validated science.</h1>
<p><strong>No submission-authorized TIFF. No new experiment or TIFF in this session.</strong>
Git inventory checked {escape(packet["checked_utc"])}. This is not a leaderboard feed.</p>
<div class="actions"><a class="button primary" href="executive-summary.html">Research download &amp; submission gates</a>
<a class="button" href="data/{SNAPSHOT}" download>Download immutable inventory JSON</a></div></div>
<section><h2>What changed since the frozen registry?</h2>
<p>All tracked .tif, .tiff and .zip paths, including research inputs and archives.
Counts are files, not distinct predictions. Git blobs were inventoried at pinned commits;
TIFF pixels were not revalidated. Old scientific registry pins remain unchanged.</p>
<div class="tablewrap"><table><thead><tr><th>Site / immutable source</th><th>Added paths</th>
<th>Changed paths</th><th>Removed</th><th>Unchanged</th><th>Current pixel uniqueness</th>
<th>Submit authorization</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
<section><h2>Historical H33-B2 ZIP irregularity</h2><p>The old pinned ZIP contained a single empty
.zip-named member, not a GeoTIFF. The current inspected ZIP contains a TIFF-named member with
TIFF magic bytes. This fixes the observed archive-member problem; it is not a new scientific
prediction or proof of competition acceptance. See the <a href="data/h33_archive_inspection_c6ea4bb7.json">byte inspection receipt</a>.</p></section>
<section><h2>Download decision and score estimate</h2><p>The existing DPRF1 research TIFF passes
fresh finite [0,1], single-band, CRS, shape and transform checks. Its outside-footprint/nodata
convention still differs from the cached sample. The literal all-entry uniqueness gate fails.
<strong>DOWNLOAD for research: YES. SUBMIT: NO. Leaderboard estimate: unavailable.</strong></p>
<p>The <a href="review-c6ea4bb7.md">session review</a> distinguishes recorded holdout evidence,
prospective hypotheses and outstanding work. No historical score is promoted to ORGANIZER-CONFIRMED.</p></section>"""

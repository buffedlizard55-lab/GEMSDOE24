"""Render the owner's reported priority-site comparison, never a selector."""

from html import escape

# Verbatim identities/values from the owner brief, not submission-page receipts.
REPORTED = (
    (
        24,
        "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
        "0.2477",
        "Dotted H19 ancestry; historical reference only.",
    ),
    (
        25,
        "dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
        "0.2600",
        "Wider dot spacing on H19; not an independent discovery.",
    ),
    (
        27,
        "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
        "0.2449",
        "Topographic gap-closure variant; reported below the dotted reference.",
    ),
    (
        28,
        "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan",
        "0.2710",
        "Highest reported of the four listed historical GEMSDOE28 variants; not a validated new lane.",
    ),
    (
        30,
        "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca",
        "0.2600",
        "Off-catalogue Poisson emission; equal reported value does not prove equal predictions.",
    ),
    (
        31,
        "h27-4-solo-d28-20261004-8acb75e1-nan",
        "0.2708",
        "Same reported value as GEMSDOE28 H27-4; verify geometry, not score equality.",
    ),
    (
        32,
        "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
        "0.2778",
        "Highest owner-reported value in this nine-site list. Recorded geometry: catalogue-flank pruning, no new dots.",
    ),
    (
        33,
        "h33d-analog-tip-stepover-r30-20261004-cb490425926e",
        "0.2632",
        "Analog tip/stepover method; reported below H33-B2.",
    ),
    (
        36,
        "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros",
        "0.2750",
        "Second-highest owner-reported value here. A physics model name is not proof of vent discovery.",
    ),
)


def priority_summary(registry, feed):
    pins = {int(s["repo"].split("GEMSDOE")[-1]): s for s in registry["sources"]}
    changes = {int(s["repo"].split("GEMSDOE")[-1]): s for s in feed["rows"]}
    if set(pins) != {r[0] for r in REPORTED} or set(changes) != set(pins):
        raise ValueError("Priority summary requires all nine source pins and freshness rows")
    rows = []
    for number, name, claim, explanation in REPORTED:
        pin, change = pins[number], changes[number]
        freshness = "Unknown: fetch failed"
        if change["status"] == "checked":
            freshness = (
                "Changed since pinned review"
                if change["changed_since_review"]
                else "Matches pinned review"
            )
        url = f"https://github.com/{pin['repo']}/tree/{pin['ref']}"
        rows.append(
            f'<tr><td><a href="{escape(url)}">GEMSDOE{number}</a></td>'
            f"<td><code>{escape(name)}</code></td><td>OWNER-REPORTED, UNVERIFIED: {claim}</td>"
            f"<td>{escape(explanation)}<br>{freshness}.<br><strong>SUBMIT: NO — historical reference, not a unique new candidate.</strong></td></tr>"
        )
    return (
        """<section id="priority-summary"><h2>Nine-site executive comparison</h2>
<p><strong>Best file to submit under the current gates: NONE.</strong> This is an evidence comparison, not selection of a weekly slot.
GEMSDOE32 leads only the owner's reported list, not an organizer-verified ranking. Every quoted competition value below is an
unverified owner claim, explicitly excluded from scientific scores and promotion. No ORGANIZER-CONFIRMED receipt is available.</p>
<div class="tablewrap"><table><thead><tr><th>Pinned source</th><th>Highest listed historical identity</th><th>Claim, not verified score</th><th>Interpretation and decision</th></tr></thead><tbody>"""
        + "".join(rows)
        + """</tbody></table></div>
<p>Source freshness is checked separately from scientific review. New commits do not invalidate frozen results, but their new files
are not covered by the old novelty certificate. Do not upload an old winner, a renamed copy, or a candidate merely because it passes [0,1].
The newer reported GEMSDOE24/25/27/28/30 results in the brief do not exceed their listed historical maxima; they also lack organizer receipts.</p>
<p><a href="research.html">H33-B2 geometry, hypothesis history and metric limitations</a> ·
<a href="data/priority_feed.json">Timestamped nine-source feed</a> ·
<a href="https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/knowledge/owner_brief_2026-10-25.md">Preserved owner claims</a></p></section>"""
    )

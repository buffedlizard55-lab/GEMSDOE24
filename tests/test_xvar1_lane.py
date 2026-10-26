"""Unit, mathematical, and recorded-receipt tests for H24-XVAR1."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np

from gems import gvc, selector, submission, xvar1

ROOT = Path(__file__).resolve().parents[1]


def test_centered_semivariogram_is_parity_symmetric_and_peaks_on_fault_step():
    """Verify 180-deg parity symmetry, step localization, and two-sided log jumps."""
    h_rows, w_cols = 51, 51
    # Sharp N-S striking buried basement step across x = 25
    field = np.full((h_rows, w_cols), -2.0, dtype=np.float32)
    field[:, 25:] = 2.0

    dir_gammas, iso = xvar1._centered_directional_semivariances(field, lag_px=3, sigma_px=1.0)
    assert len(dir_gammas) == 4
    assert iso.shape == (h_rows, w_cols)
    assert iso.dtype == np.float32

    # Along-strike N-S (dir index 2: dy=1, dx=0) has zero difference everywhere
    assert float(dir_gammas[2].max()) == 0.0
    # Cross-strike E-W (dir index 0: dy=0, dx=1) peaks symmetrically across col 24..25
    ew_profile = dir_gammas[0][25, :]
    assert ew_profile[24] > 0.0 and ew_profile[25] > 0.0
    assert np.isclose(ew_profile[24], ew_profile[25], atol=1e-6)
    # Far from the fault step (col 5 and col 45), E-W semivariance is negligible
    assert ew_profile[5] < 1e-6 and ew_profile[45] < 1e-6

    # Two-sided log-semivariogram jump across a high-roughness vs low-roughness juxtaposition
    rng = np.random.default_rng(20261026)
    juxta = rng.standard_normal((51, 51)).astype(np.float32) * 0.05
    juxta[:, 25:] *= 40.0  # Shallow magnetic volcanic footwall vs thick alluvial hanging-wall
    _, iso_juxta = xvar1._centered_directional_semivariances(juxta, lag_px=3, sigma_px=2.0)
    jumps = xvar1._twosided_log_jumps(iso_juxta, offset_px=5)
    assert len(jumps) == 4
    # Strike m=2 (N-S strike -> E-W normal dx=-5) peaks right across the offset_px=5 fault zone
    abs_ew_jump = np.abs(jumps[2][10:41, :]).mean(axis=0)
    peak_col = int(np.argmax(abs_ew_jump))
    assert abs(peak_col - 25) <= 5
    assert abs_ew_jump[peak_col] > 5.0 * max(abs_ew_jump[5], abs_ew_jump[45])

    # Exact 180-degree parity commutation: V(-x) == flip(V(x))
    rand_field = rng.standard_normal((33, 37)).astype(np.float32)
    g_fwd, iso_fwd = xvar1._centered_directional_semivariances(rand_field, lag_px=3, sigma_px=2.0)
    g_rev, iso_rev = xvar1._centered_directional_semivariances(
        rand_field[::-1, ::-1].copy(),
        lag_px=3,
        sigma_px=2.0,
    )
    np.testing.assert_allclose(iso_fwd[::-1, ::-1], iso_rev, rtol=1e-5, atol=1e-6)
    for m in range(4):
        np.testing.assert_allclose(g_fwd[m][::-1, ::-1], g_rev[m], rtol=1e-5, atol=1e-6)


def test_xvar1_excludes_forbidden_and_1m_lidar_channels():
    """Ensure XVAR1 never touches catalogue-proximity or 1 m LiDAR channels."""
    assert len(xvar1.XVAR1_NAMES) == 8
    assert set(xvar1.XVAR1_NAMES).isdisjoint(gvc.FORBIDDEN_COLUMNS)
    assert len(xvar1.RAW_LIDAR_AMPLITUDE_NAMES) == 15
    assert "lidar_1" in xvar1.RAW_LIDAR_AMPLITUDE_NAMES
    assert "gvc_lidar_lineament_900m" in xvar1.RAW_LIDAR_AMPLITUDE_NAMES
    assert "sahg_g_sat" in xvar1.RAW_LIDAR_AMPLITUDE_NAMES
    assert "sahg_h_conduit" in xvar1.RAW_LIDAR_AMPLITUDE_NAMES
    assert set(xvar1.XVAR1_NAMES).isdisjoint(xvar1.RAW_LIDAR_AMPLITUDE_NAMES)


def test_xvar1_recorded_receipts_and_strict_geotiff_integrity():
    """Verify frozen H24-XVAR1 run card, selector v2, GeoTIFFs, ZIP, note, and 9-site audit."""
    card_path = ROOT / "evidence/xvar1_run_card_20261026.json"
    sel_path = ROOT / "evidence/xvar1_selector_20261026.json"
    dl_path = ROOT / "docs/data/xvar1_download.json"
    nine_path = ROOT / "evidence/nine_site_executive_summary_xvar1_20261026.json"
    template = ROOT / "data/bridge/sample_submission.tif"

    card = json.loads(card_path.read_text())
    saved_sel = json.loads(sel_path.read_text())
    dl = json.loads(dl_path.read_text())
    nine = json.loads(nine_path.read_text())

    assert card["lane_id"] == "H24-XVAR1"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert dl["ok_to_submit"] is False
    assert saved_sel["decision"] == "DO_NOT_SUBMIT"
    assert saved_sel["ok_to_submit"] is False
    assert saved_sel["human_inspection_used"] is False

    # Leakage canary + C2ST + DPRF1 overlap checks
    assert card["leakage_canary"]["passed"] is True
    assert card["leakage_canary"]["n_features_checked"] == 60
    assert card["leakage_canary"]["worst_polarity_extremity"] <= 0.90
    c2_cand = card["exact_file_nuisance_audit"]["candidate"]
    assert c2_cand["strict_gate_passed"] is True
    assert c2_cand["observed_auc"] < 0.55
    assert card["correlation_overlap_vs_registry"]["dot_overlap_within_3px_vs_dprf1"] <= 0.70
    assert card["correlation_overlap_vs_registry"]["dot_overlap_within_3px_vs_dkrn1"] > 0.70

    # Preregistration commit exists in repository history
    commit = card["preregistration_commit"]
    res = subprocess.run(
        ["git", "cat-file", "-t", commit],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.stdout.strip() == "commit"

    # GeoTIFFs, ZIP, note, and selector re-verification
    zeros_tif = ROOT / "docs/downloads" / card["submission_name"]
    nan_tif = ROOT / "docs/downloads" / card["nan_outside_artifact"]
    zip_file = ROOT / "docs/downloads" / card["zip_artifact"]
    note_file = ROOT / "docs/downloads" / dl["note_file"]

    assert hashlib.sha256(zeros_tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(nan_tif.read_bytes()).hexdigest() == card["nan_outside_sha256"]
    assert hashlib.sha256(zip_file.read_bytes()).hexdigest() == card["zip_sha256"]

    with zipfile.ZipFile(zip_file) as zf:
        assert zf.namelist() == [zeros_tif.name]
        assert hashlib.sha256(zf.read(zeros_tif.name)).hexdigest() == card["raster_sha256"]

    note = note_file.read_text().strip()
    assert 1 <= len(note) <= 140
    assert note == card["note"] == dl["note"]

    chk = submission.check_variants(zeros_tif, template)
    assert chk["format_valid"] is True
    assert chk["submission_authorized"] is False
    assert chk["checks"]["variant_strict_whole_array_no_nan_allowed"]["pass"] is True

    fresh_sel = selector.verify_selector(zeros_tif, template, card)
    assert fresh_sel["decision"] == "DO_NOT_SUBMIT"
    assert fresh_sel["ok_to_submit"] is False
    assert fresh_sel["gates"] == saved_sel["gates"]

    # 9-site executive summary completeness
    sites = {row["site"] for row in nine["sites"]}
    assert sites == {f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36)}
    assert all(row["ok_to_submit"] is False for row in nine["sites"])
    assert all("SUBMIT: NO" in row["executive_verdict"] for row in nine["sites"])

    # CLI --verify-recorded check
    cli = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_xvar1_lane.py"), "--verify-recorded"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    parsed = json.loads(cli.stdout)
    assert parsed["verified"] is True
    assert parsed["ok_to_submit"] is False


def test_gapfill_quarantine_blocks_leaked_promotion():
    """Verify PR #55's leaked gapfill packet is quarantined and cannot self-promote."""
    blocked = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_unique_submission_gapfill.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode != 0 and "QUARANTINED" in blocked.stderr
    qcard = json.loads((ROOT / "docs/data/unique_gapfill_quarantined_run_card.json").read_text())
    assert qcard.get("ok_to_submit") is False
    assert qcard.get("verdict") == "negative"

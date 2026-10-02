#!/usr/bin/env python
"""H24-1: INGENIOUS confidence-contrast reweighting of our emission, evaluated
on the quadrant-fold gate (19 convention). Exploratory (this file is the
pre-registration; results written before any submission decision).
ratio = density(MC+Inferred traces) / density(all traces smoothed) per pixel;
pred' = pred * (1 + lam*(z-scored ratio)), mass-preserving; gated for
lam in {0.15, 0.30} on h19-4 and h19-5."""
import json, sys
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/"src")); sys.path.insert(0, str(ROOT/"scripts"))
from gems import footprint, holdout, paths, confounds as cf
from scipy.ndimage import gaussian_filter

EXTJ = ROOT / "data_external" / "qfaults_v2_in_footprint.json"
if not EXTJ.exists():
    raise SystemExit("qfaults json missing — fetch via public-layers branch first")
from pyproj import Transformer
albers = "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-117 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"
tr = Transformer.from_proj(albers, "EPSG:32611", always_xy=True)
fp = footprint.load_footprint()
labf = footprint.load_band(paths.DATA_DIR/"bridge"/"labels.tif")
ho = holdout.Holdout(fp, np.nan_to_num(labf) > 0)
H, W = fp.shape
d = json.loads(EXTJ.read_text())
pts_wc, pts_other = [], []
for f in d["features"]:
    cls = f["attributes"].get("FTYPE_")
    for path_ in f["geometry"]["paths"]:
        for x, y in path_:
            (pts_wc if cls == "Well Constrained" else pts_other).append((x, y))
def dens(pts):
    a = np.asarray(pts, float)
    x, y = tr.transform(a[:, 0], a[:, 1])
    row, col = cf._utm_to_grid(x, y)
    ok = (row >= 0) & (row < H) & (col >= 0) & (col < W)
    m = np.zeros((H, W), np.float32)
    np.add.at(m, (row[ok], col[ok]), 1.0)
    return gaussian_filter(m * fp, 20.0)
den_wc, den_oth = dens(pts_wc), dens(pts_other)
ratio = den_oth / np.maximum(den_wc + den_oth, 1e-9)
z = (ratio - ratio[fp].mean()) / max(ratio[fp].std(), 1e-9)
np.clip(z, -3, 3, out=z)
print("ratio fp mean/95:", round(float(ratio[fp].mean()), 4), round(float(np.nanquantile(ratio[fp], 0.95)), 4))
res = {"generated_utc": "2026-10-01", "features_wc": len(pts_wc), "features_other": len(pts_other),
       "smoothing_sigma_px": 20, "results": {}}
for tag in ("h19-4", "h19-5"):
    src = sorted((ROOT/"inputs").glob(f"*{tag}*-nan.tif"))[-1]
    with rasterio.open(src) as s:
        e = np.nan_to_num(s.read(1).astype(np.float32), nan=0.0)
    ev = e.ravel()[np.flatnonzero(fp.ravel())]
    zv = z.ravel()[np.flatnonzero(fp.ravel())]
    base = ho.evaluate(ev, ridge=True)
    res["results"][f"{tag}-raw"] = {k: base[k] for k in ("mean_dense_dti", "mean_sparse_dti", "fold_dense", "fold_sparse")}
    print(f"{tag} raw dense {base['mean_dense_dti']:.5f}", flush=True)
    for lam in (0.15, 0.30):
        w = np.clip(1 + lam * zv, 0.4, 2.2)
        ne = ev * w
        ne = ne * (ev.sum() / max(ne.sum(), 1e-9))
        r2 = ho.evaluate(ne.astype(np.float32), ridge=True)
        res["results"][f"{tag}-h241-lam{lam}"] = {k: r2[k] for k in ("mean_dense_dti", "mean_sparse_dti", "fold_dense", "fold_sparse")}
        res["results"][f"{tag}-h241-lam{lam}"]["fold_delta_dense"] = [round(a - b, 5) for a, b in zip(r2["fold_dense"], base["fold_dense"])]
        print(f"{tag} lam={lam}: dense {r2['mean_dense_dti']:.5f} ({r2['mean_dense_dti']-base['mean_dense_dti']:+.5f}) folds {r2['fold_dense']}", flush=True)
        if lam == 0.30:
            w2 = np.clip(1 + lam * z, 0.4, 2.2)
            e2 = np.clip(e * w2, 0, 1).astype(np.float32)
            e2 = e2 * (e.sum() / max(e2.sum(), 1e-9))
            outp = ROOT / "out" / f"{tag}-h241-confidence-contrast.tif"
            outp.parent.mkdir(exist_ok=True)
            prof = dict(driver="GTiff", width=W, height=H, count=1, dtype="float32", crs=footprint.CRS,
                        transform=footprint.TRANSFORM, nodata=np.nan, compress="zstd", tiled=True)
            with rasterio.open(outp, "w", **prof) as dd:
                dd.write(np.where(fp, e2, np.nan).astype(np.float32), 1)
            res["results"][f"{tag}-h241-lam{lam}"]["raster"] = str(outp.relative_to(ROOT))
paths.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
(paths.EVIDENCE_DIR / "h24_1_gate.json").write_text(json.dumps(res, indent=2))
print("wrote evidence/h24_1_gate.json")

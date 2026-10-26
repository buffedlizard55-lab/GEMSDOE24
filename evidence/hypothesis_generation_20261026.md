# Hypothesis Generation 2026-10-26

## 1. Magnetic and Gravity Phase-Tensor / Tilt Anti-Correlation with Relief (H24-PTAR)
**Layers Involved:** `rtp`, `tmi_vg`, `tmi_hg` (to compute Magnetic Tilt), `iso_grav_anom` gradients (Gravity Tilt), and `det_local_relief`.
**Physical Signature Target:** Edge-detection via Phase Tensor (Tilt angle) amplitude normalized by local relief. Large structural phase boundaries in areas of absolutely zero topographic relief.
**Why it catches missing faults:** The USGS/INGENIOUS catalogue heavily relies on surficial expressions (scarps, springs). Concealed faults in basin interiors have no local relief but can have massive magnetic/gravity phase signatures (which normalize amplitude, revealing deep sources).
**Difference from Repo:** While GVC1 and TRSG1 used Miller-Singh tilt inside a massive 52-channel HGB model, this isolates the phase-tensor signature combined specifically as an anti-correlation with relief (flat basins) as a direct, label-free physical transform, avoiding all structural training bias.
**Expected DTI Improvement:** High (Targets blind basin faults completely missed by current structural models).
**Implementation Cost:** Low (Fast array manipulation of existing `data/prepared/features.npy`).

## 2. Geodetic Strain Rate Divergence at Isostatic Gravity Saddles (H24-GSD)
**Layers Involved:** `geod_dilaterate`, `geod_shearrate`, and `iso_grav_anom`.
**Physical Signature Target:** Spatial coincidence of geodetic strain rate anomalies (high shear/dilation) intersecting gravity saddles (Hessian determinant < 0 of isostatic gravity).
**Why it catches missing faults:** Geothermal permeability often forms at transtensional step-overs (strain anomalies) in the basement (gravity saddles). These deep step-overs might not have surficial fault lines in the catalog, as they accommodate diffuse basin strain.
**Difference from Repo:** H24-CON used strain product to weight a surface conductivity breach. This uses strain directly to weight deep basement saddles (gravity), removing the reliance on surficial `cond_surf` which is heavily confounded by playas/agricultural drains.
**Expected DTI Improvement:** Medium-High.
**Implementation Cost:** Low (Can be built as a lightweight label-free detector like CON).

## 3. Topographic and Magnetic Cross-Gradient Divergence (H24-TMCG)
**Layers Involved:** `det_elev`, `rtp` (or `tmi`).
**Physical Signature Target:** Cross-gradient of topography and magnetic anomaly (Topographic gradient vector cross Magnetic gradient vector).
**Why it catches missing faults:** A cross-gradient measures the structural alignment between surface morphology and subsurface geology. Misalignments (high cross-gradient) indicate structural decoupling (e.g., deep fault not controlling modern surface erosion).
**Difference from Repo:** EUL1 added gravity-magnetic cross-gradient to a 52-channel model. This calculates Topo-Magnetic cross-gradient directly to find buried structures that are decoupled from surface morphology.
**Expected DTI Improvement:** Medium.
**Implementation Cost:** Medium (Requires calculating dot products/cross products of gradient arrays).

## Ranking:
1. **H24-PTAR** (High Expected DTI, Low Cost, purely label-free and relies on known physics of basin-concealed faults).
2. **H24-GSD** (Medium-High Expected DTI, Low Cost).
3. **H24-TMCG** (Medium Expected DTI, Medium Cost).

Action: Proceeding with **H24-PTAR** for the spatially-blocked holdout validation.

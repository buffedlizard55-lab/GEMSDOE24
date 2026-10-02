# 07 · Geoscience digest — what the sources I read this session say (2026-10-02)

Only statements I read at the cited page are listed under **READ**. Anything I add is marked **INFERENCE**. Earlier sessions' digests of
Faulds & Hinz and the Great Basin play-fairway study are in `03_verified_sources_2026-10-02.md` and `docs/data/sources.json`; they were not re-read here.

## Competition framing (organizers) — [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
* **READ.** The ground-truth catalogue "is known to be incomplete and may even contain some inaccurate data". The test set is new faults identified by fault experts that are not in the public USGS database; after the initial round, an expert panel uses submitted predictions to update labels for the final round.
* **READ.** About page: geologists detect faults from field observations, geophysical surveys and remote sensing; "Most faults in the GeoDAWN region of Nevada are more subtle, and many are hidden below the surface, requiring geophysical data to detect."
* **READ.** The About page cites deep-learning fault-mapping papers: Mattéo et al. 2021 (JGR Solid Earth, doi 10.1029/2020JB021269) and Hermant et al. 2025 (below).

## Hermant, Kiersnowski & Bellanger (2025), Stanford Geothermal Workshop — [PDF](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf)
* **READ.** In the Great Basin "most of the hydrothermal systems are fault-controlled"; accurate, complete fault mapping matters for defining the structural network, its orientation relative to the stress field, and favourable settings such as step-overs and accommodation zones.
* **READ.** Quaternary fault databases exist across the western USA but mapping accuracy and homogeneity between regions is "sometimes insufficient"; the local imprecision "may be due to the resolution of the available data at the time"; in north-central Nevada the distance between USGS Quaternary faults and the authors' fault labels "can be up to 400 m" (Figure 2 caption).
* **READ.** Many faults "induce local topographic variations (fault scarp) that can be mapped from elevation, slope or satellite imagery"; Walker Lane accommodates about 20 % of Pacific–North America motion as right-lateral shear; the Basin and Range extends WNW.
* **INFERENCE.** The catalogue's positional error (≈125 m nominal at 1:250,000; up to ~400 m observed elsewhere) is comparable to the metric's 300 m kernel, so a correction of an existing trace can matter; this motivates, but does not validate, hypothesis H25-6.

## GeoDAWN release — [USGS ScienceBase](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
* **READ.** Airborne magnetic and radiometric surveys (EDCON-PRJ, 2021-11-01 to 2022-11-20) with coordinated 3DEP lidar; Area 1 (Clayton Valley; Li-clay/brine focus; 200 m lines, 100/150 m clearance) and Area 2 (remainder; geothermal focus; 400 m lines, 150/200 m clearance); four acquisition blocks Winnemucca, Fallon, Hawthorne, Tonopah; total 149,030 line-km over 51,857 km². Magnetic processing includes diurnal, aircraft-field, tie-line leveling, micro-leveling and IGRF corrections; "variable terrain clearance should be considered when modeling".
* **INFERENCE.** Different line spacings, clearances and aircraft per block are real instrument seams; any detector that is not block-aware can mistake a seam for a structure, which is why the audit includes block membership.

## Seismic-hazard fault compilations (descriptions only) — [NSHM23 fault sections](https://www.usgs.gov/data/earthquake-geology-inputs-us-national-seismic-hazard-model-nshm-2023-western-us-ver-20), [Nature Sci. Data 2022](https://www.nature.com/articles/s41597-022-01609-7), [NBMG open data](https://data-nbmg.opendata.arcgis.com/pages/geology)
* **READ (descriptions).** NSHM23 FSD = 1,017 simplified fault sections of Quaternary-active faults compiled from the USGS Quaternary Fault and Fold Database and the literature; NBMG offers free 1:500,000 geologic map, contact and fault data (other map GIS data are for sale).
* **INFERENCE.** Neither is an independent expert re-mapping with lidar, so neither is a likely source of the hidden labels; not pursued. A free data release of slip/dilation tendency for Great Basin Quaternary faults ([Siler, USGS](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d)) is derived from the same fault database.

## Staff statements that shape the target — see `docs/data/sources.json`
New truth may lie within 300 m of known traces (corrections); "new fault" includes new geometry of existing systems; hand-labelling is allowed if labels are saved; Phase 2 labels come from expert review of all submissions.

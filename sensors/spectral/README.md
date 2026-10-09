# Spectral curves

Tabulated spectral curves referenced by sensor-spec entries: detector QE, optics transmission, filters.
Real files, hashed with the sensor library; no symlinks.

Layout: `spectral/<kind>/<name>.csv`, where `<kind>` is `qe`, `optics`, or `filter`. A curve is shared by any
sensor that references it; a measured curve is added under a new name, not over a synthetic one.

## Format `spectral-curve/1`

UTF-8, LF line endings. Leading `#` lines carry `key: value` metadata (a line beginning `#   ` continues the
previous value). One header row, then data rows.

| key | meaning |
|---|---|
| `name` | equals the file stem |
| `quantity` | `qe_absolute` (electrons/photon) or `transmission` (dimensionless); both lie in [0, 1] |
| `x` | `wavelength_um`; second column is the quantity |
| `range_um` | first and last wavelength in the file |
| `interpolation` | `linear` between rows |
| `extrapolation` | `none`: a job bandpass outside `range_um` is an error; zero is written as data, never implied |
| `provenance` | `synthetic`, `vendor_typical`, `measured` |

Wavelength is strictly ascending; the grid may be non-uniform. Read with
`pandas.read_csv(path, comment="#")`.

## Range

Curves span 0.150-14.000 um at 1 nm so any modeled bandpass lies inside `range_um`. A physical detector
responds over a fraction of that range; the remainder is written as 0. The DIRSIG job bandpass is set from the
sensor's nonzero support, not from `range_um`.

## Files

All three are synthetic placeholders for pipeline development, not vendor data.

| File | Content |
|---|---|
| `qe/synthetic_visgaas.csv` | VisGaAs-like QE, 0.28-1.72 um, 0.55-0.80 |
| `qe/synthetic_silicon.csv` | silicon-like QE, 0.19-1.12 um, peak 0.90 |
| `optics/synthetic_vis_lens.csv` | AR-coated refractive optics, 0.34-2.40 um, 0.94 falling to 0.90 |

## Referencing a curve

A sensor-spec names a curve as `{name: spectral/<kind>/<file>.csv, content_hash: "sha256:..."}`, resolved against
`sensors/`, in `optics.throughput_reference`, `channels[].qe_reference`, or `channels[].srf_reference`
(CONOPS and Guide §4). `scripts/stamp_hashes.py` stamps the hash; the loader verifies it.

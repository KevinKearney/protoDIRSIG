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

Optional keys, written by `scripts/import_curve.py`: `source` (document, revision, figure), `acquired` (date the
data were obtained), `measured_range_um` (first and last measured wavelength), `padding` (present only when zero
rows were added outside the measured range, and says where), `units`, `description`.

Wavelength is strictly ascending; the grid may be non-uniform. Read with
`pandas.read_csv(path, comment="#")`.

## Range

The synthetic curves span 0.150-14.000 um at 1 nm so any modeled bandpass lies inside `range_um`. A physical
detector responds over a fraction of that range; the remainder is written as 0. The DIRSIG job bandpass is set
from the sensor's nonzero support, not from `range_um`.

## Importing vendor or measured data

    python scripts/import_curve.py SCION_QE.csv --kind qe --name teledyne_scion_visgaas_typ \
        --wavelength-unit nm --percent --provenance vendor_typical \
        --source "Teledyne SCION datasheet rev C, fig. 3" --acquired 2026-10-01 --pad-zero-to 0.150,14.000

The input is two numeric columns, comma- or whitespace-separated, with any header line. The file keeps the
input's own grid (coarse and non-uniform is fine), converted to um and sorted; an exactly repeated row is kept
once and a wavelength given two different values is refused. Values must lie in [0, 1] after `--percent`,
within 0.001; anything further out is refused, not clipped. An existing file is never overwritten.

A real curve covers less than a job needs (SCION: about 0.3-1.7 um, against the template's 0.41-2.0 um), and
`extrapolation: none` makes the generator refuse it. `--pad-zero-to LO,HI` states what the detector does
outside the measured range: zero rows 1 nm beyond each measured end and at LO and HI, and a `padding` header line.
Nothing is padded unless asked.

Pad to `0.150,14.000`, the library range, not to the template's bandpass edges. A curve describes the detector,
not one job: padded to the library range it works with any template bandpass, and the generator's
outside-the-bandpass check sees the whole response. Padding to 0.41-2.0 would tie the file to the
`AurorNIRDetector` template and fail under a template with another bandpass.

## Files

All three are synthetic placeholders for pipeline development, not vendor data.

| File | Content |
|---|---|
| `qe/synthetic_visgaas.csv` | VisGaAs-like QE, 0.28-1.72 um, 0.55-0.80 |
| `qe/synthetic_silicon.csv` | silicon-like QE, 0.19-1.12 um, peak 0.90 |
| `optics/synthetic_vis_lens.csv` | AR-coated refractive optics, 0.34-2.40 um, 0.94 falling to 0.90 |

## Referencing a curve

A sensor-spec names a curve as `{name: spectral/<kind>/<file>.csv, content_hash: "sha256:..."}`, resolved against
`manifold_sensors/`, in `optics.throughput_reference`, `channels[].qe_reference`, or `channels[].srf_reference`
(CONOPS and Guide §4). `scripts/stamp_hashes.py` stamps the hash; the loader verifies it.

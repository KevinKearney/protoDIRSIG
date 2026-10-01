# dirsig_demos — dirfm reimplementations of the RIT DIRSIG demos

`dirfm` ports of the demonstration scenarios shipped with DIRSIG5. Each port builds the same run tree the RIT demo ships as hand-authored files, but constructs it programmatically through `dirfm` and invokes `scene2hdf` / `dirsig5` from Python.

The ports exist to establish `dirfm`'s coverage empirically. A demo that cannot be reproduced identifies a gap, and the gap — not the image — is the result.

## Upstream source

```
/home/kevin-kearney/DIRSIG/dirsig-2026.38.0.a020954-Linux-x86_64/demos/
├── index.html          catalogue, grouped by category, with per-demo compatibility notes
├── thumbnails/
└── zips/               151 demo archives, one per scenario
```

The catalogue is the authority for category membership and for the DIRSIG version each demo is compatible with. Read `index.html` before porting a demo; the per-demo *Compatibility* block records which DIRSIG releases a demo is valid against, and several demos predate the installed build.

A RIT demo archive unpacks to a flat tree:

```
StkImport1/
├── README.html, README.txt     scenario description
├── demo.jsim                   entry point (some demos ship several)
├── demo.platform
├── demo.tasks
├── demo.motion                 or .ppd
├── simple.atm
├── geometry/, materials/       where the demo carries scene assets
└── images/                     reference renders: demo.png, video.gif, video.mp4
```

`images/demo.png` is the reference output. A port is not complete until its render has been compared against it.

## Layout here

One subfolder per demo, named exactly as the upstream archive:

```
dirsig_demos/
└── StkImport1/
    ├── build.py        constructs the run tree with dirfm and runs DIRSIG
    ├── README.md       what the demo exercises, what dirfm covers, what it does not
    └── outputs/        generated tree and renders (gitignored)
```

Rules:

**Name the folder after the archive.** `StkImport1`, not `stk_import` or `stk-import-1`. The upstream name is the join key to `index.html`, to the archive, and to the compatibility note.

**Never modify the RIT demo tree.** The install directory is read-only by convention. `build.py` reads from it (for assets a port reuses) and writes only into `outputs/`.

**`outputs/` is not source.** Gitignored except for a placeholder. Generated trees, `.hdf` scene compilations and renders are reproducible from `build.py` and are not committed.

**The per-demo `README.md` records the gap, not the success.** A port that reproduces the demo cleanly needs two lines. A port that cannot needs the specific `dirfm` API that is missing or wrong, and what was done instead.

**Reuse scene assets, rebuild inputs.** Geometry, materials and maps are copied or referenced from the unpacked archive. The `.jsim`, `.platform`, `.tasks` and motion files are what `dirfm` generates — regenerating those is the point of the exercise.

## Coverage

Counts are upstream demos per category. Ported counts are maintained by hand; update them in the same commit as the port.

| Category | Upstream | Ported |
|---|---:|---:|
| Static Scene Geometry | 2 | 0 |
| Moving Scene Geometry | 7 | 0 |
| Built-in Scene Geometry | 3 | 0 |
| Reference/Calibration Geometry | 2 | 0 |
| Advanced Scene Geometry | 13 | 0 |
| Optical Properties | 4 | 0 |
| Property Maps | 13 | 0 |
| Water | 2 | 0 |
| Atmosphere | 4 | 0 |
| Clouds and Plumes | 7 | 0 |
| Radiometry | 3 | 0 |
| Secondary Sources | 7 | 0 |
| Platform Mounts | 9 | 0 |
| Platform Motion | 3 | 0 |
| Advanced Platform Concepts | 15 | 0 |
| Alternative Sensor Plugins | 5 | 0 |
| Thermal | 10 | 0 |
| LIDAR | 16 | 0 |
| Polarization | 4 | 0 |
| Space Domain Awareness (SDA) | 8 | 0 |
| Synthetic Aperture Radar (SAR) | 2 | 0 |
| **Catalogued total** | **139** | **0** |

Twelve archives in `zips/` have no entry in `index.html` and are not counted above: `AnimatedObject1`, `Blackadar1`, `ChipMaker1`, `LidarBounces1`, `NormalMap2`, `PointCollectors2`, `Polarization3`, `RossLi1`, `SensorPosition1`, `SpatialResponse1`, `Starfield1`, `TrafficLights1`. These are superseded or in-development demos; treat them as unsupported and port one only with a reason recorded in its `README.md`.

### Priority

SDA and Platform Motion first — `Ssa1`–`Ssa3`, `StkImport1`, `EarthShine1`, `LightCurve1`, `SpaceRendezVous1` — per the project's Phase 2 scope. `StkImport1` is the only orbit-to-ground scenario in the catalogue; the rest of the SDA set is satellite-to-satellite.

LIDAR (16) and SAR (2) exercise the `source` / `transmitter` / `receiver` branch of the platform file and are out of scope until a passive-EO baseline is complete.

## Known `dirfm` limitations

Carried forward from the MANIFOLD DIRSIG analysis; a port blocked by one of these records it in its own `README.md` rather than restating the cause.

| Area | State |
|---|---|
| Quaternion orientation engine | No `dirfm` counterpart |
| STK report import | No counterpart. `StkImport1` needs the ephemeris path, not the report path |
| `up type="velocity"` | `dirfm` writes a fixed up vector only |
| `EarthGrid` plugin | No counterpart |
| DIRSIG native `sgp4` | Not used. No UT1−UTC correction; ~33 m LEO position error on the protoDIRSIG test date. Propagate with skyfield and write waypoints |
| Location and orientation jitter | Not implemented |
| `uniform` and `classic` radiative transfer | Not implemented |
| Turbulence, `uniformweather`, `spin` and `velocity` orientation engines | Not implemented |

## Running a port

Environment setup is in the repository root `README.md`. `DIRSIG_HOME` and the `bin/` entry on `PATH` are set inside `build.py`, not at the shell level, for the same reason the notebooks do it: a conda environment does not inherit an interactive shell's `PATH`.

```bash
conda activate protodirsig
python dirsig_demos/StkImport1/build.py
```

`build.py` asserts that `scene2hdf` and `dirsig5` resolve before doing anything else.

Note that `scene2hdf` writes `<scene>.hdf` beside the `.scene` file and has no output-path option. Ports that compile a scene must stage the `.scene` file into `outputs/`, never compile in place inside the DIRSIG install.

## Reproducibility

Unseeded DIRSIG runs are statistically but not bitwise reproducible — radiance differences up to 3.6 × 10⁻⁴ were observed. A port that compares against a reference render compares statistically. Pass an explicit seed through `dirfm`'s `set_seed()` where a run needs to be repeatable, and record it in the port's `README.md`.

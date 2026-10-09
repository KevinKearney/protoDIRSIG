# DIRSIG Platform Decomposition and the MANIFOLD Sensor Descriptor

Sep 30, 2026 · Kevin Kearney · Draft

Tutorial. Non-normative. Part I describes the `.platform` file's object tree as DIRSIG5 defines it, read from `joe_dirsig_file_schemata/platform.json`. Part II relates that tree to `descriptor.sensor`, the `EopticDetectorConfigDatasetFacet` v2.0.0-shaped block of the MANIFOLD run spec. `AV_MANIFOLD_Detector_v02` and `AV_MANIFOLD_Metadata_v02` prevail where they differ from this document.

---

# Part I — The `.platform` decomposition

## 1. What the file is

A `.platform` file is one of the five parameter-class inputs of a DIRSIG run tree (role `dirsig:platform`; the five are listed in `AV_MANIFOLD_Configuration_v02` §6.2). It describes the *observing apparatus* and nothing else: no scene, no trajectory, no epoch, no task. Position and attitude of the vehicle come from the motion file; when the instrument observes comes from the tasks file; what it observes comes from the scene. The platform file answers only *what is the instrument, how is it pointed relative to the vehicle, and how does it convert incident radiance into a recorded frame*.

The file is XML with a schema-equivalent JSON projection. Attribute-valued nodes are written `@name` below, following the JSON projection's convention; in the XML they are attributes of the element.

## 2. The container chain

The tree has one hard rule and one soft one. The hard rule: **every instrument is reached through a mount, and every mount is reached through an attachment.** The soft one: attachments nest, so the chain is recursive and the depth is unbounded.

```
platform
├── attachment[]                        the vehicle's mount points
│   ├── affinetransform                 2-D placement of this attachment
│   ├── mount                           articulation between vehicle and instrument
│   │   ├── @type                       static | gimbal | scan | ...
│   │   ├── data                        rotations, scan limits, target lock
│   │   ├── rotationdeviates            stochastic pointing error
│   │   ├── uncertainty                 stochastic position error
│   │   └── attachment[]                ← recursion: a mount carries mounts
│   └── instrument
│       ├── frame                       instrument reference frame + output of pose
│       ├── properties                  the optics
│       ├── options                     ray-tracing controls
│       ├── clock / datetime            instrument-level timing
│       ├── focalplane[]                one per focal plane
│       ├── source / transmitter / receiver    active-sensor branch
│       └── output                      per-instrument output file
├── clocktable                          named clock entries referenced by @name
└── metadata                            free key/value entries
```

`platform` itself carries almost nothing. It is a list head. The physics lives three levels down.

### 2.1 `attachment`

An attachment is a **mounting point on the vehicle**. Its `affinetransform` gives a planar placement (`xtranslate`, `ytranslate`, `xrotate`, `yrotate`) — a deliberately thin transform, because the substantive articulation belongs to the mount below it. An attachment holds exactly one `mount` and one `instrument`; the pair is the unit of "a sensor on this vehicle".

Multiplicity at this level is the multi-sensor case: three attachments is a three-instrument rig, each independently mounted.

### 2.2 `mount`

The mount is the articulation model. `@type` selects the kinematic class — a fixed bracket, a two-axis gimbal, a scanning mirror — and `data` supplies whatever that class needs:

| `mount.data` field | Meaning |
|---|---|
| `xrotation`, `yrotation`, `zrotation` | Fixed Euler offsets, order given by `@rotationorder`, units by `@angularunits` |
| `alongtrack`, `acrosstrack` | Angular travel limits (`minimumangle` / `maximumangle`) of a scanning or gimballed mount |
| `scanrange` (`start`, `stop`), `scanscript` | Scan law: swept limits, or an external script |
| `targetname`, `targetoffset.point` | Target-lock pointing: the mount slews to hold a named scene object |
| `clock` | Mount's own clock, when articulation is time-driven |
| `entry[]` | Tabulated pointing, one entry per time or index |

Two sibling blocks make the mount stochastic rather than exact:

- `rotationdeviates` — per-axis random rotation (`@type` distribution, `values.mean`, `values.standarddeviation`) applied to pointing. This is jitter.
- `uncertainty` — per-axis positional variance (`xlocation`, `ylocation`, `zlocation`), enabled by `@enabled`.

**The recursion matters.** `mount.attachment[]` means a mount can carry further attachments, each with its own mount and instrument. This is how a gimbal carrying a two-instrument head is expressed: outer attachment → gimbal mount → inner attachments → per-instrument static mounts → instruments. The composed pose of an instrument is the ordered product of every transform on the path from `platform` to that instrument. There is no field recording that composition; it is implied by the tree.

### 2.3 `instrument`

The instrument is the optical system: one entrance pupil, one set of optics, one or more focal planes behind it.

**`properties` — the optics.**

| Field | Meaning |
|---|---|
| `aperturediameter` | Entrance pupil diameter. No unit attribute on the field |
| `focallength` | Effective focal length. No unit attribute |
| `aperturethroughput` | Band-averaged transmission of the common path |
| `focusdistance`, `magnification` | Conjugate |
| `distortion` (`k1`,`k2`,`k3`,`p1`,`p2`) | Brown–Conrady coefficients |
| `telecentricity` | Chief-ray condition |
| `receiverradius`, `receiverthroughput` | Active-sensor receive path |
| `signalgate`, `dynamicgateinfo` | Range gating (lidar) |

`@spatialunits` on `properties` governs the spatial quantities in that block. It does not disambiguate `aperturediameter` against `focallength` individually, which is the source of the unit ambiguity noted in §5 below.

**`frame`** declares the instrument's reference frame `@type` and whether `location` and `orientation` are written to the output (`@enabled`, `format`). It is an output-reporting control, not a frame *definition* in the sense the descriptor requires.

**`options`** are Monte Carlo controls — `maxbounces`, `samples`, `nodemergeradius`, `repeatableseed`, `nodemapfile`. These describe the *computation*, not the instrument. They belong with `convergence` in `capturemethod` as render-quality knobs, and MANIFOLD routes them to `engine.run` rather than to the sensor description.

**`source` / `transmitter` / `receiver`** are the active-sensor branch: illumination `spatial` / `spectral` / `temporal` profiles, `polarizer`, `modulation` (`chirprate`), pulse energy and duration. A passive EO/IR instrument leaves these absent. The branch is structurally large and semantically disjoint from the passive path.

### 2.4 `focalplane`

A focal plane is the pairing of a **detector array** (the geometry of the sampling lattice) with a **capture method** (how each sample is formed, integrated, and written). One instrument may hold several; `@enabled` switches one off without deleting it.

```
focalplane
├── capturemethod          radiometry, spectral sampling, integration, output
├── detectorarray          the sampling lattice
└── truthcollection[]      per-plane truth products
```

### 2.5 `detectorarray` — the lattice

| Field | Meaning |
|---|---|
| `xelementcount`, `yelementcount` | Array dimensions in detectors |
| `xelementspacing`, `yelementspacing` | **Pitch**, centre to centre |
| `xelementsize`, `yelementsize` | Active detector extent. `size / spacing` is linear fill |
| `xarrayoffset`, `yarrayoffset` | Lattice offset from the optical axis |
| `xoversample`, `yoversample` | Output oversampling factor |
| `xsubsamples`, `ysubsamples` | Sub-detector sampling for the spatial response integration |
| `xflipaxis`, `yflipaxis` | Axis inversion |
| `@rollingreadout` | Rolling versus global readout |
| `fieldcount` | Interlaced fields |
| `clock`, `clockrate` | Frame or line rate |
| `filename`, `selectorfilename`, `selectorlist` | External lattice definition; active-element selection |
| `@spatialunits` | Units for the spacing and size fields |

`@type` selects the array class (framing, pushbroom, whiskbroom). Note that pitch is `spacing` and fill factor is derived, not stored.

### 2.6 `capturemethod` — everything else

This node carries the radiometry, the spectral sampling, the temporal integration, the detector electronics, the sampling strategy, and the output format. It is the largest node in the file and the one whose contents are most heterogeneous.

**Spectral.** `spectralresponse` holds either a `channellist` (explicit channels) or a `channelpattern` (generated), plus a `bandpass` (`minimum`, `maximum`, `delta`, `@spectralunits`). A channel carries `center`, `width`, and `@shape` (`gaussian`, `tophat`, …). The `bandpass` is the **radiative-transfer integration range**, not the filter edge — it bounds where DIRSIG computes spectral radiance, and is typically far wider than any channel.

**Temporal.** `temporalintegration` gives `time` (integration period), `samples` (temporal samples within it), and `@tdi` (time-delay integration stages).

**Electronics.** `detectormodel` gives `bitdepth`, `readnoise`, `maxelectrons` (full well), `minelectrons`, `quantumefficiency`, `darkcurrentdensity`. `gainresponse.gainmodel[]` gives per-channel `gain` and `bias`, or a `lut` of `entry` pairs for a non-linear response.

**Spatial response.** `spatialresponse` samples the per-detector spatial weighting over a sub-element grid (`@xsubelements`, `@ysubelements`, `@xsamples`, `@ysamples`, `@spatialsampling`) with `entry` values. `psf` supplies an image-based or parametric point spread function (`image`, `scale`, `width`). `spatialsampling` gives the sample counts used.

**Sampling and convergence.** `samplestrategy` (`@type`, `maxsamples`, `maxfraction`, `hypersamplingmultiplier`) and `convergence` (`minimumsamples`, `maximumsamples`, `threshold`) control Monte Carlo termination. Render quality, not instrument description.

**Output.** `imagefile` carries `basename`, `extension`, `datatype`, `schedule`, `defaultbands`, and — significantly — `@fluxunits` and `@areaunits`. `@fluxunits="electronspersecond"` declares that the recorded quantity is electron flux rather than radiance; that attribute is the only statement of the radiometric reference in the file. `outputmethod`, `outputfile`, `processing.task[]`, `compressionlevel`, and `deltahistogramoutput` complete the block.

**Active.** `pulsecompression`, `samplespertimebin` serve the lidar path.

### 2.7 `truthcollection`

A list of truth products emitted alongside the image: `collectorlist.collector[]` names each (material ID, range, surface normal, abundance, …), with its own `imagefile`. Truth is a *label-generation* concern — L6 in the MANIFOLD layering — not a sensor property. It appears here because DIRSIG emits it per focal plane.

### 2.8 `clocktable` and `metadata`

`clocktable.entry[]` defines named clocks referenced by `@name` from mounts, instruments and arrays. `metadata.entry[]` is an untyped key/value bag; DIRSIG does not interpret it.

## 3. What the decomposition asserts

Reading the tree as a model rather than a file format:

**Pose is compositional and implicit.** An instrument's pose is the ordered composition of every `affinetransform` and `mount.data` rotation on its root path, plus whatever `rotationdeviates` samples. Nothing in the file states the composed result.

**Multiplicity is at three levels with three different meanings.** `attachment[]` means several sensors on one vehicle. `focalplane[]` means several planes behind one aperture. `channellist` means several spectral bands on one plane. These are physically distinct and the file distinguishes them correctly.

**Units are attribute-scoped and incomplete.** `@spatialunits`, `@spectralunits`, `@temporalunits`, `@angularunits`, `@areaunits`, `@fluxunits` cover their blocks. `properties.aperturediameter` and `properties.focallength` share one `@spatialunits` and are routinely written in different units (metres and millimetres), which the file cannot express.

**Computation and instrument are interleaved.** `options`, `convergence`, `samplestrategy`, and the sub-sampling fields on `detectorarray` are solver settings sitting inside the instrument description. Any consumer that treats the platform file as a sensor description has to partition them out.

---

# Part II — Relating the decomposition to `descriptor.sensor`

## 4. What `descriptor.sensor` is

The run spec is a YAML or JSON file with two sections. `engine` is the DIRSIG body, read only by the generator. `descriptor` is the governed metadata, written in the controlled vocabulary, and is the authority for the catalog's search columns. `descriptor.sensor` is the sub-tree of the descriptor that describes the observing apparatus, and it has the structure of `EopticDetectorConfigDatasetFacet` v2.0.0.

`descriptor.sensor` is **not generated from** the platform file at run time. It is either authored as a config-repo library entry and *validated* against the platform file by the extractor, or, on the direct path, hand-written. The extractor reads `.platform` and emits a `sensor` instance; the generator asserts that instance equals the authored one. Disagreement rejects the tree (MD-13). The mapping below is therefore a *conformance relation*, not a transformation.

## 5. The descriptor's structure

The section omits the facet header (`_schemaURL`, `contract_version`) and `system_configuration_id`, which are set at admission and carried by the emitted `eoptic_detectorConfig` facet and the parameter-set record (`AV_MANIFOLD_Detector_v02` §6.1, §7.3).

```
sensor
├── sensor_system
│   ├── system_id
│   ├── reference_frame                   name, origin, handedness, axis_convention
│   └── frame_association                 policy, reference_channel, tolerance
└── entries[]                             one per mount–instrument pair
    ├── entry_id
    ├── identity                          instrument_id, sensor_class, Device* fields
    ├── mount                             kind, translation, rotation, tolerances
    ├── optics                            aperture_diameter, focal_length, f_number,
    │                                     throughput_in_band, focus_distance, distortion
    └── focal_planes[]
        ├── optical_path                  split, splitter_type, throughput, f_number
        ├── mtf_at_nyquist_row/column
        ├── array                         SensorWidth/Height, SensorPixelWidth/Height,
        │                                 fill_factor, channel_layout, cfa_pattern,
        │                                 defect_fraction, defect_map_reference
        ├── readout                       SensorShutterMode, AdcBitDepth,
        │                                 timestamp_reference, rolling_line_period,
        │                                 tdi_stages, exposure_time_min/max,
        │                                 acquisition_frame_rate_max
        └── channels[]
            ├── channel_id, band, band_center, bandwidth, cut_on, cut_off
            ├── srf_reference, qe_reference, qe_peak, qe_at_band_center
            ├── full_well, conversion_gain, read_noise, dark_current
            ├── noise_figure, noise_class, linearity_error
            └── radiometric_reference     quantity, unit, scale, offset
```

## 6. The controlled vocabulary — four mechanisms

The descriptor's vocabulary control is not one mechanism but four, and they govern different things.

**(a) Closed in-schema enumerations.** Fixed at the contracts tag, `additionalProperties: false`. `mount.kind` ∈ {`fixed`, `gimballed`, `scanned`}. `distortion.model` ∈ {`none`, `brown_conrady`, `division`, `tabulated`}. `optical_path.split` ∈ {`none`, `transmitted`, `reflected`, `relayed`}. `array.channel_layout` ∈ {`single`, `cfa`, `stripe`, `stacked`}. `readout.timestamp_reference` ∈ {`exposure_start`, `exposure_midpoint`, `exposure_end`, `readout_complete`, `host_receipt`}. `SensorShutterMode` ∈ {`Global`, `Rolling`, `GlobalReset`, `Tdi`, `None`}. `radiometric_reference.quantity` ∈ {`radiance`, `spectral_radiance`, `irradiance`, `brightness_temperature`, `digital_number`}. `noise_figure.kind` ∈ {`nedt`, `nesr`, `nei`, `nep`}. Changing one of these is a schema version bump.

**(b) External vocabularies, `x-vocabulary`.** The schema names the vocabulary; the members live in `schemas/vocabulary/<axis>.schema.json` of the contracts repository and version independently, and a second validation pass checks membership. `band` → `sensor_band` (L7 band axis: NIR, SWIR, MWIR, LWIR, …). `identity.sensor_class` → `sensor_class` (framing, pushbroom, whiskbroom, staring_array, single_element). `channel.noise_class` → `noise_class`, resolved at registration from `noise_figure` by a per-band, versioned banding rule. `assetRef.role` → `sensor_asset_role` (renamed from `asset_role`). The L3 axes other than `sensor_band` have no vocabulary file yet and are not enforced at M1. Adding a band is a vocabulary release, not a schema release — the distinction that makes the L7 axes extensible without breaking registered descriptors.

**(c) Term identity, `x-term`.** Every field carries an `eoptic:` term resolved in the contracts-repository term registry, which records an external citation where one exists and an explicit null where none does. This is what discharges MD-6. The schema itself carries no external terms.

**(d) Naming discipline.** PascalCase keys are GenICam SFNC feature names adopted verbatim and marked `x-sfnc` (`SensorWidth`, `SensorPixelWidth`, `AdcBitDepth`, `SensorShutterMode`, `DeviceModelName`). snake_case keys are program-minted. An SFNC name is never reused for a quantity SFNC does not name. Two declared departures: `AdcBitDepth` is an integer rather than the SFNC enumeration, to admit non-enumerated converter widths; `SensorShutterMode` adds `Tdi` and `None` to the SFNC values.

**Units.** `x-unit` is a UCUM code, mandatory on every dimensional field. Electron and digital-number counts use UCUM annotations `{e}` and `{DN}`, since UCUM defines neither. Lengths are `mm` for optics, `um` for pixel pitch — fixed by the schema, not carried per instance.

**The quantity wrapper.** A field that is measured, specified, or modelled is not a bare number. It is an object: `{value, provenance, uncertainty?, uncertainty_kind?, conditions?}`. `provenance` ∈ {`measured`, `specified`, `modeled`, …}; `uncertainty_kind` is required whenever `uncertainty` is present, because an uncertainty of unstated interpretation is unusable. `conditions` carries the determination context — `detector_temperature`, `scene_temperature`, `integration_time`, `f_number` — or a `standard` / `standard_release` citation in place of restating them. Quantities *fixed by design* are bare numbers: `aperture_diameter`, `focal_length`, `f_number`, `SensorPixelWidth`, `band_center`, `bandwidth`. Quantities that are not: `throughput_in_band`, `qe_peak`, `full_well`, `read_noise`, `dark_current`, `conversion_gain`, `linearity_error`, `noise_figure.value`.

This is the sharpest single difference from the platform file. DIRSIG stores `aperturethroughput: 0.875`. The descriptor stores `throughput_in_band: {value: 0.875, provenance: specified}`. The number is the same; the descriptor additionally records that nobody measured it.

## 7. Structural correspondence

| DIRSIG node | `descriptor.sensor` node | Relation |
|---|---|---|
| `platform` | `sensor_system` | Container. DIRSIG's is anonymous; the descriptor's carries `system_id` and a declared `reference_frame` |
| `attachment` (mount + instrument) | `entries[]` member | **The pairing is preserved.** One attachment is one entry |
| `mount` | `entry.mount` | Kinematic class and pose |
| `instrument` | `entry.identity` + `entry.optics` | **Split.** DIRSIG's instrument node holds identity, optics, timing, focal planes and solver options in one object |
| `instrument.properties` | `entry.optics` | Direct |
| `instrument.focalplane[]` | `entry.focal_planes[]` | Direct |
| `detectorarray` | `focal_plane.array` | Lattice geometry |
| `capturemethod` | `focal_plane.readout` + `focal_plane.channels[]` + `descriptor.settings` | **Split three ways** |
| `capturemethod.spectralresponse.channellist` | `focal_plane.channels[]` | Direct |
| `capturemethod.detectormodel` | fields on `channels[]` | Per-plane in DIRSIG, per-channel in the descriptor |
| `truthcollection[]` | — | No counterpart. L6 concern |
| `instrument.options`, `convergence`, `samplestrategy` | — | Solver settings → `engine.run` |
| `source` / `transmitter` / `receiver` | — | No counterpart |
| `clocktable`, `metadata` | — | No counterpart |

## 8. Field mapping, worked on the Auror NIR instrument

Values from `platforms/AurorNIRDetector.platform` of the Auror / Tahoe tree.

| DIRSIG field | Value | `sensor` field | Note |
|---|---|---|---|
| `detectorarray.xelementcount` / `yelementcount` | 500 / 500 | `array.SensorWidth` / `SensorHeight` | Direct |
| `detectorarray.xelementspacing` / `yelementspacing` | 10.0 µm | `array.SensorPixelWidth` / `SensorPixelHeight` | Pitch is spacing, not size |
| `xelementsize / xelementspacing` | 1.0 | `array.fill_factor` | Derived, not stored |
| `properties.aperturediameter` | 0.085 | `optics.aperture_diameter` | Descriptor requires mm. Source unit unattributed |
| `properties.focallength` | 306.0 | `optics.focal_length` | Unattributed. If mm, f/# = 306/85 = 3.6 |
| — | | `optics.f_number` | Carried, not derived. Working F/# at the stated conjugate |
| `properties.aperturethroughput` | 0.875 | `optics.throughput_in_band` | Wrapped: `{value, provenance: specified}` |
| `mount @type=static`, no rotation | | `mount.kind=fixed`, translation `[0,0,0]`, rotation `[1,0,0,0]` | DIRSIG Euler + order → descriptor quaternion |
| `channel.center` | 0.85 µm | `channels[].band_center` | Direct |
| `channel.center` | 0.85 µm | `channels[].band` | **Lookup** into `sensor_band` → `NIR` |
| `channel.width`, `@shape=gaussian` | 0.0637 | `channels[].bandwidth` | Descriptor requires FWHM. If the DIRSIG width is σ, FWHM = 2.3548 σ |
| `spectralresponse.bandpass` min/max | 0.41 / 2.0 µm | **none** | Integration range, not a filter edge. Not `cut_on` / `cut_off` |
| `imagefile @fluxunits=electronspersecond` | | `radiometric_reference.quantity`, `unit` | Requires an electron-flux member of the quantity enum; protoDIRSIG proposes `electron_exposure`, `e-/m2` (CONOPS and Guide, C-20) |
| `channel @gain` / `@bias` | 1 / 0 | — (`descriptor.settings`) | Per-channel in DIRSIG, per-entry in `settings` |
| `detectorarray.clock.rate` | 1000 Hz | — (`descriptor.settings` frame rate) | `readout.acquisition_frame_rate_max` is a device limit, not a setting |
| `capturemethod.temporalintegration` | 0.005 s, 10 samples | — (`descriptor.settings`) | Integration time is a setting, not a device property |
| `truthcollection` (11 collectors) | | **none** | L6 |

### 8.1 Required descriptor fields with no source in this file

`SensorShutterMode`, `AdcBitDepth`, `timestamp_reference`, `optical_path`, `sensor_system.system_id`, and `reference_frame` (name, origin, handedness, axis convention). These are assigned in the library entry with `provenance: specified` or `modeled`, and their catalog columns are `unvalidated`.

**A qualification worth making.** The claim is true of the *Auror instance*, not of the *format*. `capturemethod.detectormodel` defines `bitdepth`, `readnoise`, `maxelectrons`, `quantumefficiency` and `darkcurrentdensity`; `detectorarray.@rollingreadout` distinguishes rolling from global readout; `temporalintegration.@tdi` gives TDI stages. A platform file that populates these has a genuine source for `AdcBitDepth`, `read_noise`, `full_well`, `qe_peak`, `dark_current`, and the `Global`/`Rolling`/`Tdi` distinction. The extractor should read them where present rather than treating the whole electronics block as unsourced, and the library entry should supply only what the file actually omits. Auror omits `detectormodel` entirely, which is a property of that authored instance.

`timestamp_reference`, `optical_path`, `system_id` and `reference_frame` have no source in any platform file. Those are irreducibly authored.

## 9. Where the correspondence breaks

**Recursion is flattened.** `entries[]` is a flat list of mount–instrument pairs. A DIRSIG gimbal carrying two instruments is a three-level tree; the descriptor represents it as two entries whose `mount.rotation` values must carry the *composed* pose. The composition is performed by the extractor and is not recoverable from the descriptor. Where a gimbal's articulation is time-varying, `mount.kind: gimballed` records the class but the descriptor has no field for the scan law — `scanrange`, `scanscript`, `targetname` have no counterpart. This is the largest single loss in the mapping and it is invisible: a validated descriptor for a gimballed instrument is silent about what the gimbal did.

**Pointing stochastics have no counterpart.** `rotationdeviates` and `uncertainty` — jitter and mount positional variance — map to nothing. `mount.alignment_tolerance` is a static bound, not a distribution. A run that enables jitter and one that does not produce identical `descriptor.sensor` blocks.

**`capturemethod` splits across a device/setting boundary the file does not draw.** DIRSIG holds integration time, gain, bias and clock rate in the same node as bit depth and quantum efficiency. The descriptor separates *what the device is* (`readout`, `channels`) from *how it was configured for this collection* (`descriptor.settings`). The split is the right one and it is a genuine re-modelling, not a rename: the extractor must partition `capturemethod` by semantics, not by path.

**Spectral bandpass is not a filter.** The most available error in the mapping is reading `spectralresponse.bandpass` into `cut_on` / `cut_off`. It is the radiative-transfer integration range — 0.41 to 2.0 µm for a 0.85 µm NIR channel. Mapping it would assert a 1.6 µm-wide filter.

**Gaussian width is ambiguous.** DIRSIG's `channel.width` with `@shape=gaussian` is not documented as σ or FWHM; the descriptor requires FWHM. The factor is 2.3548. This is an open item, and until it closes every Gaussian-shaped channel in the catalog carries a possible 2.35× bandwidth error.

**Units are asserted, not read.** Every descriptor dimensional field has a fixed UCUM unit. The platform file's `@spatialunits` does not resolve `aperturediameter` against `focallength` when they are written in different units, which the Auror values suggest they are. The extractor must impose a convention and the convention must be recorded, because nothing in the file supports it.

**The spatial response model does not survive.** `spatialresponse` (a sampled sub-element weighting grid), `psf` (image or parametric), and `distortion` together constitute DIRSIG's spatial transfer model. The descriptor carries `distortion` in full, and `mtf_at_nyquist_row` / `mtf_at_nyquist_column` as scalars. A sampled PSF grid reduces to two numbers, or to an `assetRef`.

**Truth and active sensing are outside the model.** `truthcollection` is L6. `source` / `transmitter` / `receiver` have no representation at all: `descriptor.sensor` is shaped for passive EO/IR and a lidar or radar platform file cannot be described in it.

## 10. Direction of authority

The relation runs in one direction at registration and the other at authoring.

At authoring: the engineer writes the run spec's `descriptor.sensor`, or references a config-repo library entry that supplies it. The `.platform` file is a separate config-repo artifact, published by merge request.

At generation and registration: the extractor reads the `.platform` file from the staged tree and emits its own `sensor` instance. The generator asserts equality with the authored instance (§5.4, sensor equality); the admission gate compares extractor values against the descriptor (MD-13). Inequality rejects the tree.

So the descriptor is authored but not trusted. Fields with an extractor source are `validated` in the catalog's common core; fields without one — `platform.class`, `timestamp_reference`, `reference_frame` — are `unvalidated`, and the distinction is carried to the consumer. The controlled vocabulary makes the comparison decidable: `band: NIR` is comparable against a lookup from `channel.center: 0.85` only because `sensor_band` has a versioned member list and a defined lookup rule. An uncontrolled string would make MD-13 unenforceable for that column.

## 11. Open items bearing on the mapping

| Item | Effect if unresolved |
|---|---|
| Units of `aperturediameter` and `focallength` | f/# wrong by 10³; every derived GSD and Airy figure wrong |
| Gaussian `width`: σ or FWHM | `bandwidth` wrong by 2.3548 on every Gaussian channel |
| Scene axis convention | `reference_frame.axis_convention` unsupported by the file |
| Electron-flux member of `radiometric_reference.quantity` | `@fluxunits=electronspersecond` unmappable; proposed `electron_exposure` (CONOPS and Guide, C-20) |
| Band and array-size columns for multi-entry, multi-channel systems | Common-core projection rule undefined |
| Whether `eoptic_detectorConfig` is a copy of `descriptor.sensor`, extractor output, or separately authored | Determines whether §10's two-direction relation holds at execution as well as registration |

---

## Sources

- `joe_dirsig_file_schemata/platform.json` — DIRSIG `.platform` schema
- `EopticDetectorConfigDatasetFacet_v2-0-0.json` — descriptor `sensor` schema
- `fixtures/synthetic_dirsig_lwir.json` — conformant instance
- `A&T_DIRSIG_example.md` §2, §5, §9 — run tree, run spec, extractor mapping
- `AV_MANIFOLD_Configuration_v02` A.2, A.8 — role list, engine body
- `AV_MANIFOLD_Metadata_v02` — descriptor and admission gate
- `AV_MANIFOLD_Detector_v02` — L3 detector view

# The MANIFOLD run-spec YAML: structure and the DIRSIG example

**Date:** 7 October 2026
**For:** Kevin Kearney
**Consolidates:** `AV_MANIFOLD_Metadata_v02.md` §6 (descriptor and admission gate) and
`AV_MANIFOLD_Configuration_v02.md` Appendix A.8 (`engine` body, DIRSIG origin), which a reader
otherwise has to cross between to read one YAML file. Field tables are not reproduced in full;
each section cites the authoritative table and states what is not obvious from reading it cold.
Companion file: `auror_ref_run_spec.yaml`, a run spec for the real
`AUROR_ref` tree built against this structure.

## 1. Top level

A run spec is one YAML (or JSON) document with three keys (`AV_MANIFOLD_Metadata_v02` §6.3):

| Key | Required | Content |
|---|---|---|
| `spec_version` | Yes | `run-spec/<major>`, currently `run-spec/1`. Not a contracts-repository tag. |
| `descriptor` | Yes | Engine-independent. Authored in the governed vocabulary, with units, frames and provenance stated. Authority for catalog search. |
| `engine` | No | Origin-specific generator input. Absent for field data. One schema per origin; `dirsig-engine/1` for DIRSIG. Not indexed, not searchable. |

The split is the document's organizing fact: `descriptor` is what gets registered, searched and hashed into identity's provenance record; `engine` is what the generator and executor consume to produce the run tree. A field collection has no `engine` section at all — its sidecar is a run spec whose only section is `descriptor`.

## 2. `descriptor`

Eight blocks, of which six are required for `run-spec/1` (`meta`, `origin`, `collection`, `sensor`, `settings`, `fidelity`); `field` is required exactly when `origin.kind` is `field`; `extras` is always optional. Unknown keys are rejected at every level except `extras` — this is the mechanism that turns a typo into an admission failure rather than a silently ignored field.

**`meta` / `origin`.** `meta.name` is an immutable alias to one `parameter_set_id`; it does not change if the descriptor is corrected. `origin` is two axes, not one: `origin.kind` (`synthetic` or `field`) and `origin.engine` (`dirsig`, `satsim`, `usd`, or `field`), linked by an if/then — `engine: field` iff `kind: field`. For DIRSIG, `origin: {kind: synthetic, engine: dirsig}`.

**`collection`.** Conditions under which the observation was made: epoch, platform position, geometry/illumination/atmosphere/background regime terms, and a target list. This block holds vocabulary terms and derived or converted quantities, not raw engine parameters — `atmosphere.regime` is a governed term like `mid_latitude_summer`, not a DIRSIG preset name or plugin choice (that's in `extras` and `engine.atmosphere`, §3 below). `epoch` is phenomenon time, not execution time — it is when the observation was (or is modeled as being), and is read from `.tasks` for DIRSIG. `geometry.range` becomes required the moment `targets` is non-empty.

**`sensor`.** The full L3 structure — sensor system plus one or more instrument entries (optics, focal planes, array, readout, channels) — delegated in full to `AV_MANIFOLD_Detector_v02`; this document references it, it does not retype it. `entry_id` is the join key used again in `settings` and at L5. Several required fields have no DIRSIG source at all (`SensorShutterMode`, `AdcBitDepth`, `timestamp_reference`, `optical_path`, `system_id`, `reference_frame`) and are assigned in the library entry with `provenance: specified` or `modeled`, not read from any file. A sensor system shared across runs is typically authored once as a `sensor-spec/1` document and referenced rather than repeated inline — §7.

**`settings`.** Commanded, per-entry values for the collection — exposure time, frame rate, gain, black level, ROI, binning. One member per `sensor.entries[]` member; `entry_id` must resolve.

**`fidelity`.** Four lists (`modeled`, `approximated`, `absent`) plus a free-text `valid_for`. Authored, not derived, and carries no query semantics — it is a statement for a human reader about what the corpus can be used to study, not a filterable field.

**`extras`.** The one block that admits unlisted keys, namespaced `<origin>.<name>` (e.g. `dirsig.atmosphere_preset`, `dirsig.weather_file`). Anything origin-specific that doesn't belong in the governed `collection`/`sensor` vocabulary lands here, stored in a `jsonb` column with no query guarantees beyond presence.

**Quantities.** Any field typed `quantity` is an object — `{value, provenance, uncertainty?, uncertainty_kind?, conditions?}` — never a bare number. `provenance` is one of `measured`, `specified`, `modeled`, `inherited_from_type`; `conditions` is required when `provenance` is `measured`. A field fixed by design (e.g. `split_channels`) is typed plain `boolean`/`number` and is not a quantity.

## 3. `engine` — DIRSIG body (`dirsig-engine/1`)

Eight members (`AV_MANIFOLD_Configuration_v02` Appendix A.8.1): `generator` (R), `scenes` (R), `platform` (R), `motion` (R), `tasks` (R), `atmosphere` (R), `weather` (O), `ephemeris` (O), `run` (O). `run` carries execution parameters — seed, convergence, thread count — that are not in the manifest, not part of identity, and recorded on the execution record rather than the registered spec.

**Division of labor with `descriptor`.** Values the descriptor already states (epoch, exposure time, frame rate, gain, black level) are not repeated in `engine` — the generator reads them from `descriptor` and writes them into the DIRSIG files (`.tasks`, `.platform`). Values the `engine` body states and the descriptor could derive (platform position at epoch) are emitted by the generator and may be omitted from an authored spec. Getting this backwards — restating an exposure time under both `descriptor.settings` and some `engine` field — is not how the schema is built; there is no such duplicate key.

**`scenes[]`.** A list of library scene references (`.scene` plus everything it pulls in — geometry, materials, maps), each with an optional `[x,y,z]` offset for compositing more than one. Like every `engine` ref, `scenes[].ref.name` resolves against the engine-asset tree root (§7 states the general rule and contrasts it with `descriptor`-side refs; §9 gives the physical layout). `scene2hdf` compiles the scene's HDF at run time, beside the `.scene` file, with no output-path option; the HDF is derived, excluded from the manifest, and never pre-compiled in the library.

**`platform`.** References a library `.platform` file by name and hash, pairs it with a `library_entry` whose `sensor` instance the extractor checks for equality against the file, and states `output_prefix`, `split_channels`, `integration_samples`. The `.platform` file itself is not regenerated from `descriptor.sensor` — current practice is a per-run patched copy when `settings` differs from the library file's baked-in values.

**`motion`.** `kind: static | waypoints | orbit`. `static` writes a `.ppd` directly from `position.xyz` and an Euler orientation; `waypoints`/`orbit` write a FlexMotion file instead. Orbit propagation (skyfield + SGP4 with a UT1−UTC correction, per A.12) happens outside DIRSIG entirely — DIRSIG's own `sgp4` engine has no such correction and was measured to accumulate ~33 m of LEO position error. Only the resulting ECEF waypoint samples cross into the engine body.

**`tasks`.** A list of `{start, stop}` windows relative to `descriptor.collection.epoch`; `start == stop` is a single static sample.

**`atmosphere` / `weather` / `ephemeris`.** `atmosphere.plugin` is `four_curve` or `basic` in the current schema — these are the only two values A.8.7 defines. `ephemeris.plugin: spice` takes no inputs in the examined trees; it reads kernels from the DIRSIG installation, which is why those kernels are covered by the engine data hash rather than the manifest (§4).

**What is not in the body yet** (A.7): quaternion orientation, STK report import, velocity-tracking `up`, `EarthGrid`, `locationjitter`/`orientationjitter`, uniform/classic radiative transfer, turbulence, uniform weather. A tree needing any of these is registered directly with a hand-written descriptor rather than generated — the body covers what dirfm covers, not all of DIRSIG.

## 4. What is not in either section

Two categories of data that affect a run and are deliberately in neither `descriptor` nor `engine`:

Installation-resident data — the `FourCurveAtmosphere` preset contents, SPICE kernels, `ThermWeather` files read with `weather.source: install` — is covered by a Merkle hash computed once per DIRSIG installation (`engine_data_sha256`) and recorded on the execution record, not hashed per run.

Execution parameters (`engine.run`) — seed, convergence bounds, thread count — are recorded on the execution record, not the registered spec; the run spec is not stored with the registered tree, so `run` here is a default an authoring application copies into the launch configuration (AD A-45).

## 5. Admission and the descriptor-to-file mapping

For a generated tree, the sequence is fixed (`AV_MANIFOLD_Metadata_v02` §6.12): the generator emits both the files and the descriptor from one run spec; admission validates and hashes *that emitted descriptor*, never the authored one. After the gate passes, four fields are set on the record and are never authored: `contract_version`, `_schemaURL`, `system_configuration_id`, `noise_class`. An authored value for any of them is a validation failure.

The extractor closes the loop by reading values back out of the registered files and comparing them against the descriptor (MD-13) for every column it can reach — `.tasks` for epoch, `.platform` for exposure/gain/black level/array size, motion file plus scene origin for position. A column with no extractor path (platform class, several `sensor` fields) is `unvalidated`, not wrong — it is author-asserted and recorded as such.

## 6. Where the DIRSIG example in the architecture views is inconsistent

Both source documents carry an "illustrative instance" claimed to be the Auror run tree (`AV_MANIFOLD_Metadata_v02` §6.11; `AV_MANIFOLD_Configuration_v02` A.8.10), and between them they expose three problems worth fixing before either is trusted as a fixture:

`meta.name: tacoma-nir-baseline` in the §6.11 instance, despite every value in it — epoch, platform position, target track, channel geometry — matching Auror, not Tacoma. The name is stale from an earlier draft.

`scenes[].ref.name: scenes/tahoe` follows the config-repository's intended nested layout (`scenes/<scene>/<scene>.scene`); the real `AUROR_ref` tree has `tahoe.scene` at its root with `geometry/`, `materials/`, `maps/` as siblings, not descendants. Neither illustrative instance reconciles this, and it remains an open item for those two documents' own illustrative instances, independent of the YAML structure itself (config-repository authoring, not a schema question). This prototype's own run spec resolves it directly, via a real `config_repo/` (§9), as of Stage 04.

`atmosphere: {plugin: four_curve, conditions: mls_rural_50km}` in both instances describes a plugin the real tree does not use. `ROLE_PROPOSAL_2026-10-05.md` establishes, from the actual tree, that Auror's atmosphere comes from `NewAtmosphere` reading a prebuilt HDF5 database (role `dirsig:atmosphere_db`), not `FourCurveAtmosphere` reading an installation preset. A.8.7 has no `new_atmosphere` plugin value — the engine-body schema has not caught up to what the ratified role list already states about this tree. The prototype below carries a marked, non-adopted extension for this rather than silently reusing `four_curve`.

## 7. `sensor-spec/1`: splitting the sensor for reuse

A sensor system (`descriptor.sensor`, §2) does not depend on any one run — the same `auror-nir` optical/detector definition is reusable across every run spec built against that sensor. `sensor-spec/1` is that block pulled into its own document: `spec_version: sensor-spec/1`, a `meta` stanza (`name`, `tags`, `description`), and `sensor` exactly as §2 defines it, nothing else. A run spec then carries `descriptor.sensor: {ref: {name: "sensors/<name>.yaml", content_hash: "sha256:<hash>"}}` in place of the inline block — the same `ref` *shape* (`{name, content_hash}`) already used for `engine.scenes[]` and `engine.platform`, though its resolution root is different (below).

**Resolution root: by which side of the schema the ref is on, not a single tree.** An `engine` ref — `scenes[].ref`, `platform.ref`, `atmosphere.database.ref`, `weather.file` — names a DIRSIG input file and resolves against the engine-asset tree root: the generator's config repository, `config_repo/` in protoDIRSIG as of Stage 04 (§9). `AUROR_ref/` is the received source those assets were copied from once; it is not where refs resolve. A `descriptor` ref names another descriptor-schema document, authored in the same governed vocabulary as the run spec itself, not an engine file — so it resolves against the document store the run spec was loaded from, i.e. relative to the run spec's own location, not the engine tree. `descriptor.sensor.ref.name` is read against `auror_ref_run_spec.yaml`'s own directory; `sensors/auror-nir.yaml` sits beside it in this folder, not under `config_repo/`. The two roots coincide in this guide's own `04-guides/` folder only by convenience (it holds both the run spec and `sensors/`); in protoDIRSIG they are two physically distinct folders (`run_specs/sensors/` vs `config_repo/`) by construction, not accident — this is the general rule, not a one-off for `sensor`: any `descriptor`-side ref this schema adds later resolves against the spec's own document store, the same way, regardless of where the engine-asset repository lives.

`settings` stays with the run spec, not the sensor file. §2 already defines `settings` as the commanded, per-collection value — exposure time, frame rate, gain — and a sensor profile two different runs reuse can legitimately command different exposure times on each run; splitting `settings` out alongside `sensor` would turn the sensor file into a template for one operating point rather than a hardware definition, which is a narrower and different kind of reuse than "an imaging scientist just picks a sensor." This narrows the grouping first suggested for this split (sensor and settings together) to sensor alone, once writing the spec made the distinction between a reusable system and a commanded value concrete.

Trust model: by name, on the same terms as every other `ref` in the engine body. `content_hash` is present and carried through exactly as `engine.scenes[].ref.content_hash` and `engine.platform.ref.content_hash` already are — authored, not yet computed or verified by anything in this codebase (§4, §6). Holding sensor refs to a stricter standard than scene or platform refs would be inconsistent without a reason the schema doesn't otherwise give; the hash becomes load-bearing only once the registry-side strict loader this document already defers (§3) exists.

`sensors/auror-nir.yaml`, in this folder, is the `sensor-spec/1` extraction of `auror_ref_run_spec.yaml`'s `descriptor.sensor` block, unchanged in content. `auror_ref_run_spec.yaml`'s `descriptor.sensor` now references it. The `sensors/` subfolder is where a future library of validated sensor profiles accumulates — this is its first entry. Whether that sensor library eventually joins the same physical repository as the engine-side assets (§9) — rather than staying beside the run specs that reference it — is an open question Stage 04 deliberately left alone rather than deciding under the asset-repository migration's own time pressure; this section's rule (resolve by schema side) holds either way.

An inline `descriptor.sensor` block (the pre-§7 shape) is no longer accepted: `protoDIRSIG`'s schema and resolution checks both reject it now that a ref is required (`FINDINGS.md`, Stage 03). This document does not define a transitional dual-accept period; adopting the split means authoring against it.

## 8. Prototype

`auror_ref_run_spec.yaml`, in this folder, fixes the three items in §6 for a `descriptor` and `engine` pairing built against the real tree: an Auror-named `meta`, the atmosphere corrected to `NewAtmosphere`/`atmosphere_db` with the schema gap flagged inline, and `engine.scenes`/`platform`/`atmosphere.database`/`weather.file` refs that now point into a real `config_repo/` (§9) in the library layout A.8 specifies, closing the flat/nested mismatch §6 flags in the architecture views' own illustrative instances. It also sets `run.seed` (closed — see `FINDINGS.md`, Stage 02) and writes a `fidelity.valid_for` that states plainly that this corpus is not yet valid for target-visibility studies, given the unexplained vehicle-not-appearing finding in `FINDINGS.md`. Its `descriptor.sensor` is a `ref` to `sensors/auror-nir.yaml` (§7), not an inline block.

## 9. `config_repo/`: the physical library layout

Phase 5 of the roadmap (`PLAN_2026-10-08_conformance-template-roadmap.md`) stands up the config repository `AV_MANIFOLD_Configuration_v02.md` describes in the abstract (its §"config repository" section): a human-authored library, separate from any one received or generated tree, laid out as

```
config_repo/
  scenes/<scene>/<scene>.scene          # plus geometry/, materials/, maps/ as descendants
  platforms/<platform>/<platform>.platform
  weather/<name>.wth
  atmosphere/<name>                      # proposed, see below
```

`scenes/` and `platforms/` are exactly the Configuration doc's own layout (A.8.3 and surrounding text). `weather/<name>.wth` is already flat in that spec and needed no change. DIRSIG's own scene documentation independently confirms the `scenes/<scene>/` nesting is correct, not just a MANIFOLD convention: `$SCENE_DIR` defaults to the folder containing the `.scene` file, and RIT's own reference layout nests `geometry/`, `materials/` and `maps/` as direct children of that same folder — precisely this structure (dirsig.cis.rit.edu, `scene.html`).

`atmosphere/<name>`, flat, is a convention this prototype proposes, not one A.8 defines — there is no library path for a `new_atmosphere` database because the plugin itself is not an adopted A.8.7 value (§6). It is modeled on `weather/<name>.wth`'s flat, single-file shape rather than invented from nothing, and should be revisited if and when `new_atmosphere` (or its database) is formally adopted into the schema.

`config_repo/` is populated once, by copying `AUROR_ref/`'s scene, platform, weather and atmosphere-database files into the nested layout above (`FINDINGS.md`, Stage 04) — not a dual-maintenance pattern; `AUROR_ref/` was the received tree these were copied from; since protoDIRSIG Stage 05 it has been retired, its remaining `motion/` and `tasks/` files kept only as a test fixture (`tests/fixtures/auror_ref/`). `run_spec.py`'s resolver reads engine refs against `config_repo/` directly now; the flat/nested fallback search this prototype's scene resolution previously needed (§6) is no longer necessary once the library is laid out correctly, rather than being worked around.

Two things explicitly do not move into `config_repo/` with this migration. `sensors/auror-nir.yaml` stays in `run_specs/sensors/`, resolved per §7's descriptor-side rule — see the open question at the end of §7. And `AUROR_ref/`'s `motion/` and `tasks/` files were never library content: they are per-run execution artifacts the generator emits from `engine.motion`/`engine.tasks`, and since protoDIRSIG Stage 05 it does exactly that, writing them into each job's work directory (static motion only; `FINDINGS.md`, Stage 05), so they are not in scope for a library layout at all (§3).

# User manual

For a DIRSIG5 user who wants images from DIRSIG through the `manifold` SDK without reading the repository. The words in this manual are defined where they first appear; [the glossary](User_glossary.md) maps your words (simulation, sensor, scene, settings, result, check before running) to the SDK's. A first run without reading further: [the quick start](../notebooks/quickstart_sdk.ipynb).

## 1. What the SDK is, and is not

| Term | One sentence |
|---|---|
| engine | The simulator that makes the image: DIRSIG5 here (SatSim is the second engine); the SDK never renders anything itself. |
| SDK | The Python packages `manifold.core` and `manifold.sim` (with one package per engine) that check a simulation, start the engine, and hand back the files it wrote; its entry point is the class `Workspace`. |
| library | Read-only folders of named files the SDK picks from: recipes, scenarios and engine profiles (`manifold_run_specs/`), sensors (`manifold_sensors/`), and DIRSIG scenes, platforms and atmospheres (`manifold_config_repo/`). |
| recipe | The small YAML file (or Python dict) you edit: it names a sensor, a scenario and an engine profile from the library and gives the camera settings and a statement of what the simulation models. |
| run spec | The single document the SDK makes from a recipe by merging the files it names; it is what gets checked and run, and you do not edit it. |
| run id | A 64-hex-digit fingerprint of the run spec: the same inputs give the same run id, and a second submission of the same run returns the first one's result. |

The SDK is not a scene editor, not a DIRSIG installer, and not an image viewer: you bring DIRSIG and the scenes, and you read the images with your own tools.

## 2. Install and check

From a fresh clone of the repository, `python scripts/bootstrap.py install` links your DIRSIG installation (from `$DIRSIG_HOME` or `~/DIRSIG/<version>`) as `external/dirsig`; it never copies it. Check what is linked:

<!-- run: shell -->
```bash
python scripts/bootstrap.py status
```

Each line names an item (`dirfm`, `agent-docs`, `dirsig`) and says `ok` or what is wrong. Then ask the SDK which engines it can run. Run this and every later example from the repository's root folder; `outputs/manual` is the work root, the folder where the SDK keeps every run (any folder will do).

<!-- run: always -->
```python
from manifold.sim import Workspace

ws = Workspace.local(work="outputs/manual")
for engine in ws.list_engines().items:
    print(engine.engine_id, "available" if engine.available else f"not available: {engine.reason}")
```

`dirsig available` means the SDK found `dirsig5` and the DIRSIG engine package; otherwise the reason says what is missing; the checks below still work, and the examples that run DIRSIG need it.

## 3. One image

Pick a shipped recipe, make its window small, check it, run it. `auror_ref` is the AUROR NIR staring sensor over DIRSIG's Tahoe scene from 550 km; as shipped it renders 500 x 500 pixels, so the window (the `roi`, region of interest) is cut to 16 x 16 here, which renders in seconds.

<!-- run: always -->
```python
recipe = ws.get_recipe("auror_ref").document
recipe["settings"][0]["roi"].update(Width=16, Height=16)
check = ws.validate(recipe)
print("ready to run:", check.runs[0].valid)
```

`validate` is the check before running: it runs every check the SDK applies before it accepts a simulation (the documents' structure, every named file found in the library, every library file unchanged since it was recorded, the sensor and its settings) and starts nothing. Add `engine_check="dry_run"` to have DIRSIG itself read the generated input files too.

<!-- run: engine -->
```python
status = ws.submit_run(recipe)
final = ws.wait(status.run_id, timeout=600)
print(final.state, final.verdict)
```

`submit_run` repeats the checks, starts DIRSIG in the background and returns at once; `wait` polls until the run is `rendered`, `failed` or `cancelled`. The verdict is `complete` when every output file DIRSIG should write is there.

You changed two fields. Every other value came from the library, and you typed no file hash: the SDK computes the sensor's, and the library's other files carry theirs already.

## 4. A sweep over sensors

A sweep is one recipe that lists several sensors and gives one run per sensor. `sensor_sweep_tahoe` lists the library's three sensors over the same scene, at 32 x 32; here 16 x 16.

<!-- run: engine -->
```python
sweep = ws.get_recipe("sensor_sweep_tahoe").document
for member in sweep["settings"]:
    member["roi"].update(Width=16, Height=16)
started = ws.submit_sweep(sweep)
for run in started.runs:
    done = ws.wait(run.run_id, timeout=600)
    print(run.name, done.state, done.verdict)
```

The settings of a sweep are keyed by `entry_id`, the sensor file's name for its camera (`auror-nir`, `deepscan-850-306-nir-1280`, `synthetic-600-200-vis-1920`). To swap the sensor of a one-sensor recipe, change `sensor` and the `entry_id` of its settings member together; `auror_ref` also sets `engine_overrides` (DIRSIG's own Gaussian channel shape), which a sensor with a measured spectral curve refuses, so remove it as well.

## 5. A space-to-space run

The space-to-space scenarios are complete run specs, one per geometry, in `manifold_run_specs/s2s/` (`index.json` lists each with its run id). This one images a 20 m plate from 25 km, Sun behind the sensor; its window is cut to 16 x 16.

<!-- run: engine -->
```python
import yaml

spec = yaml.safe_load(open("manifold_run_specs/s2s/s2s-hyperresolved-r25km-v0mps-e5ms-l0-z0-d0.yaml"))
spec["descriptor"]["settings"][0]["roi"].update(Width=16, Height=16)
plate = ws.wait(ws.submit_run(spec).run_id, timeout=600)
print(plate.state, plate.verdict)
```

Pass the spec as a dict, as here: the SDK then takes its sensor from the workspace's sensor library. Passed as a file name, it looks for the sensor beside the file's folder and refuses (see section 7); `Workspace.local(sensor_library="manifold_sensors")` fixes that. [Notebook stage 06](../notebooks/stage_06_space_to_space.ipynb) shows these scenarios' results against their closed forms.

## 6. Reading the result

A run's status has its `state`, its `verdict` and its `artifacts`: the files the run kept, each with a role, a name, a media type and a sha256. Roles: `product` (the image), `truth` (DIRSIG's truth images), `metadata` (ENVI headers), `log` (DIRSIG's logs), `config` (the run spec as run), `preview`.

<!-- run: engine -->
```python
for a in ws.list_artifacts(final.run_id).artifacts:
    print(f"{a.role:9s} {a.name}")
```

The SDK hands over bytes, not arrays. `save_artifact` writes a file and checks its sha256; the image is an ENVI file, and `spectral` (installed with the SDK) reads it with its header.

<!-- run: engine -->
```python
from pathlib import Path
import spectral

folder = Path("outputs/manual-files")
folder.mkdir(parents=True, exist_ok=True)
names = {a.name for a in final.artifacts}
image = next(a.name for a in final.artifacts if a.role == "product" and a.name.endswith(".img"))
header = next(h for h in (image + ".hdr", image[:-4] + ".hdr") if h in names)
ws.save_artifact(final.run_id, image, folder)
ws.save_artifact(final.run_id, header, folder)
cube = spectral.envi.open(str(folder / header), str(folder / image)).load()
print(image, cube.shape, float(cube.mean()))
```

The shape is lines x samples x bands. The values are electrons per square metre of focal plane (DIRSIG's radiometry through the sensor's optics and spectral response), not digital counts.

Where the files are on disk: `<work root>/runs/<run id>/output/`. Each artifact's `uri` is the `file://` address of the file.

## 7. When the SDK refuses

A refusal is raised as a `manifold.core.errors.ProblemError` with a `problem`: a `title` (one of five), a `detail` naming what is wrong, and, when an authored file caused it, the `layer` (the library file, or `(recipe document)` for a dict) and the `field` in it. `validate` reports the same messages without raising, check by check.

<!-- run: always -->
```python
import copy
from manifold.core.errors import ProblemError

bad = copy.deepcopy(recipe)
bad["sensor"] = "synthetic_600_200_vis_1920.yaml"
try:
    ws.validate(bad)
except ProblemError as e:
    print(e.problem["title"])
    print(e.problem["detail"])
```

| Title | What the detail says (example) | What it means | What to do |
|---|---|---|---|
| The recipe does not compose | `settings[0].entry_id: 'auror-nir' names no entry of the listed sensors` | you changed the sensor but not the settings | set `entry_id` to the new sensor's (its file's `entry_id`) |
| The recipe does not compose | `meta.name: missing or not a string` | the recipe lacks a required field | add the field the detail names |
| The recipe does not compose | `scenarios/tahoe_static_pose.yaml: not found` | a recipe file outside the library's `recipes/` folder looks for its scenario beside itself | pass the recipe as a dict (`yaml.safe_load`), or save it in `<library>/recipes/` |
| The submission failed admission | `channel_response native cannot carry a spectral curve` | the recipe's `engine_overrides` does not suit the new sensor | remove `engine_overrides` |
| The submission failed admission | `platform could not be rendered from the sensor-spec: KeyError: 'gain'` | a settings member lacks `gain` (or `exposure_time`, `frame_rate`, `black_level`) | add it, as `{value: ..., provenance: specified}` |
| The submission failed admission | `sensor 'auror-nir.yaml' not found in the sensor library` | a run-spec file looks for sensors beside its own folder | pass the spec as a dict, or `Workspace.local(sensor_library=...)` |
| The submission failed admission | `carry a placeholder instead of a stamped value; run scripts/stamp_hashes.py` | a library file you wrote has `sha256:<hash>` where a file hash belongs | in the repository, run `python scripts/stamp_hashes.py`; elsewhere compute the hash (`docs/Authoring_friction_audit.md`, section 4) |
| The submission failed admission | `content_hash ... does not match the file` | a library file changed after its hash was recorded | if you changed it on purpose, restamp; if not, restore the file |
| Not found | `No recipe 'auror_reff'.` | no such name in the library | `ws.list_recipes()` lists the names |
| The request is not valid | `the recipe composes to 3 runs (it names several sensors); submit it with submit_sweep` | a sweep sent to `submit_run` | use `submit_sweep` |
| The run failed while executing | `Run <name> (<run id>) failed while executing: ...` | DIRSIG started and failed; the run's status lists this in `errors` | read the run's `log` artifacts and `<work root>/runs/<run id>/worker.log` |

## 8. The layers and where each lives

A recipe names three other files, the layers: the scenario (`manifold_run_specs/scenarios/`: when, from where, what kind of geometry, atmosphere and target), the engine profile (`manifold_run_specs/engine_profiles/`: the DIRSIG scene, platform template, motion, capture times, atmosphere, weather and seed) and the sensor (`manifold_sensors/`). The engine-asset library (`manifold_config_repo/`) holds the DIRSIG files the engine profile names. Writing your own layers is the subject of [the authoring guide](Authoring_layered_form.md) (the layered form against DIRSIG's own input files); adding an engine is the subject of [the engine author guide](Engine_author_guide.md). What each costs in files, fields and hashes is counted in [the friction audit](Authoring_friction_audit.md).

## 9. Reproducibility

The run id depends only on the run spec: composing the same recipe again gives the same id, and submitting it again returns the run already stored under that id without rendering.

<!-- run: always -->
```python
again = ws.compose(recipe).runs[0].run_id
print(again == check.runs[0].run_id)
```

The engine profile's `run.seed` is DIRSIG's random seed. A seed alone does not make two renders byte-identical: at DIRSIG's default thread count some scenes sample in a different order from run to run. One thread does: an engine profile or run spec with `resources: {cpu_threads: 1}` (every space-to-space spec has it) renders the same bytes every time. The run id does not include the thread count's effect on the bytes, only the request: a spec that asks for one thread has a different run id from one that does not.

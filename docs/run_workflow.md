# From user YAML to run tree

Each node: function in plain terms, then (in italics) where it lives. Edge labels state what the flow does.
`<name>` is a file stem; `<run>` is a composed run name; `<job>` is a job directory under `outputs/`.

```mermaid
flowchart TB
  subgraph AUTH["USER INPUT - authored YAML, one file per concern"]
    RC["<b>Recipe</b><br/>names the layers; run name, tags, settings<br/>(exposure, ROI, gain), fidelity, engine overrides<br/><i>manifold_run_specs/recipes/&lt;name&gt;.yaml</i>"]
    SC["<b>Scenario</b><br/>the observation: epoch, platform position,<br/>geometry, atmosphere regime, targets<br/><i>manifold_run_specs/scenarios/&lt;name&gt;.yaml</i>"]
    EP["<b>Engine profile</b><br/>how DIRSIG is driven: scene, motion, tasks,<br/>atmosphere, generator, run seed<br/><i>manifold_run_specs/engine_profiles/&lt;name&gt;.yaml</i>"]
  end

  subgraph LIB["LIBRARIES - reused across runs, never copied into a recipe"]
    SL["<b>Sensor</b><br/>engine-independent sensor-spec:<br/>optics, focal plane, channels<br/><i>manifold_sensors/&lt;sensor&gt;.yaml</i>"]
    CV["<b>Spectral curves</b><br/>QE, optics, filter transmission<br/><i>manifold_sensors/spectral/{qe,optics,filter}/*.csv</i>"]
    CR["<b>Engine assets</b><br/>scenes, platform template, weather,<br/>atmosphere database<br/><i>manifold_config_repo/</i>"]
    CT["<b>Contracts</b><br/>sensor-spec schema; compose<br/>conformance vectors<br/><i>manifold_contracts/</i>"]
  end

  COMP["<b>Composer</b> (input constructor)<br/><i>src/protodirsig/compose.py, scripts/compose.py</i>"]
  RS["<b>Composed run spec</b> run-spec/1<br/>the single document handed to MANIFOLD;<br/>generated, never edited<br/><i>manifold_run_specs/&lt;run&gt;.yaml</i>"]
  ADM["<b>Admission</b><br/>schema check, reference resolution against the<br/>libraries, hash verification, library-file check,<br/>DIRSIG dry-run<br/><i>LocalRegistry.submit; run_spec.py, simulation.py</i>"]
  ASM["<b>Assembler</b><br/>builds the run tree from the accepted run<br/><i>Simulation._assemble</i>"]
  PG["<b>Platform generator</b><br/><i>platform_gen.render_platform</i>"]
  MT["<b>Motion and tasks generator</b><br/><i>motion_tasks.generate_motion, generate_tasks</i>"]

  subgraph INTREE["RUN TREE: input/   (outputs/&lt;job&gt;/input/)"]
    direction LR
    I1["scene reference<br/>(geometry, materials linked)"]
    I2["weather file<br/>(byte copy)"]
    I3["atmosphere database<br/>(byte copy)"]
    I4["generated .platform"]
    I5["generated .ppd, .tasks"]
  end

  EX["<b>Executor</b><br/>compiles the scene, then renders;<br/>seeded by engine.run.seed<br/><i>dirfm DIRSIG.run: scene2hdf + dirsig5</i>"]

  subgraph OUTTREE["RUN TREE: output/   (outputs/&lt;job&gt;/output/)"]
    direction LR
    O1["imagery<br/>e- per m2 of focal plane (ENVI)"]
    O2["truth bands"]
    O3["run log<br/>(log_info.json)"]
  end

  MAN["<b>Manifest / execution record</b> - NOT BUILT<br/>stand-in: per-run state in LocalRegistry<br/>MANIFOLD: materialize into &lt;work&gt;/&lt;run_id&gt;/inputs<br/>plus an execution record (C-21, C-22)"]

  RC -->|"names scenario, engine profile<br/>and sensor by file name"| COMP
  SC -->|"descriptor.collection"| COMP
  EP -->|"origin, engine block, engine extras;<br/>recipe may override one allowed path"| COMP
  SL -->|"referenced by name + sha256 of bytes<br/>(or block inlined); settings entries and<br/>ROI checked against the sensor"| COMP
  CT -.->|"vectors test the composer"| COMP
  COMP -->|"layers own disjoint members; overlap is an error.<br/>A sweep recipe (sensors: list)<br/>yields one run spec per sensor"| RS
  RS -->|"submitted as one document"| ADM
  ADM -->|"accepted runs only"| ASM

  CR -->|"scene copied by reference;<br/>weather and atmosphere database<br/>copied byte-identical"| ASM
  ASM -->|"settings: exposure, ROI, gain,<br/>black level (must be 0)"| PG
  ASM -->|"epoch, motion kind, task windows<br/>-> static pose and capture times"| MT
  CR -->|"library .platform is a TEMPLATE: keeps names,<br/>mount, truth collections, spatial<br/>response, hypersampling"| PG
  SL -->|"sensor values substituted<br/>into the template"| PG
  CV -->|"optics x channel shape x QE tabulated<br/>into each channel response (0.41-2.0 um)"| PG

  ASM --> I1
  ASM --> I2
  ASM --> I3
  PG --> I4
  MT --> I5
  INTREE -->|"inputs consumed"| EX
  EX --> OUTTREE
  ASM -.->|"records state"| MAN
  EX -.->|"records state"| MAN
```

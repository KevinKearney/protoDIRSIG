# external/

Third-party code and installs the prototype depends on. Everything here except this file, `pins.json` and
`snapshots/` is gitignored. `pins.json` records the exact commit or version of each dependency.

    python scripts/bootstrap.py status                     # what is present, and whether it matches the pins
    python scripts/bootstrap.py install                    # clone dirfm and agent-docs at the pinned commits; link DIRSIG
    python scripts/bootstrap.py install --link dirfm=~/dev/dirsig-file-maker   # reuse an existing checkout

| Folder | Content | Future home in MANIFOLD |
|---|---|---|
| `dirsig-file-maker/` | `dirfm`, RIT's DIRSIG input-file library. Read-only. | pinned dependency of the SDK |
| `agent-docs/` | Rendered.ai agent-context reference. | not a dependency |
| `dirsig/` | link to the DIRSIG installation | the DIRSIG runtime mounted by the executor (AD A-44) |
| `assets/satsim/` | SatSim's data assets, pinned by sha256 and size with their source URL (`kind: asset` in `pins.json`): `de421.bsp` (JPL ephemeris) and `finals2000A.all` (a dated IERS snapshot); read-only, seen by the engine-asset library through the link `manifold_config_repo/satsim/assets`. `python scripts/bootstrap.py assets --status` verifies them; `assets` without `--status` fetches a missing one from its URL and keeps it only when its digest matches the pin | engine assets held by MANIFOLD's registry |
| `snapshots/` | tracked: `finals2000A.all`, the dated IERS snapshot (3.8 MB, public IERS data), which cannot be fetched again; `bootstrap.py assets` restores `assets/satsim/finals2000A.all` from it, offline, after checking it against the pin's `tracked` member, size and sha256 | the archive of asset snapshots (C-36) |

To change a pin, edit `pins.json` in a commit of its own.

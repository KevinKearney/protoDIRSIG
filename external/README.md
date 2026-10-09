# external/

Third-party code and installs the prototype depends on. Everything here except this file and `pins.json`
is gitignored. `pins.json` records the exact commit or version of each dependency.

    python scripts/bootstrap.py status                     # what is present, and whether it matches the pins
    python scripts/bootstrap.py install                    # clone dirfm and agent-docs at the pinned commits; link DIRSIG
    python scripts/bootstrap.py install --link dirfm=~/dev/dirsig-file-maker   # reuse an existing checkout

| Folder | Content | Future home in MANIFOLD |
|---|---|---|
| `dirsig-file-maker/` | `dirfm`, RIT's DIRSIG input-file library. Read-only. | pinned dependency of the SDK |
| `agent-docs/` | Rendered.ai agent-context reference. | not a dependency |
| `dirsig/` | link to the DIRSIG installation | the DIRSIG runtime mounted by the executor (AD A-44) |

To change a pin, edit `pins.json` in a commit of its own.

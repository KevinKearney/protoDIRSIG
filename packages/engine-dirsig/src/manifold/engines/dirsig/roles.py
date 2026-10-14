"""The DIRSIG run-tree role list (round 46 spike): the closed, namespaced list of Cfg A.2
(`AV_MANIFOLD_Configuration_v02.md`), each role with its default read class (Cfg 6.2), and the table that assigns a role
from the element that references a file.

Evidence, not the SDK's implementation: the list is held in `schemas/manifest/` of the contracts repository; this copy is
what `closure.walk` assigns from, so a walk over the prototype's trees can count the files no role covers.

A role is assigned from the referencing element, never from the file's extension (Cfg A.2): a `.ppd` named by
`BasicPlatform`'s `motion_filename` is `dirsig:motion`, a `.ppd` named in a geometry list's `<dynamicinstance>` is
`dirsig:instance_motion`. `REFERENCES` is that table: `(referrer, field) -> role`, `referrer` the kind of file that holds
the reference (itself assigned by the reference that reached it), `field` the element, JSON key or material-file
`BLOCK.KEY` that names the file. A reference whose `(referrer, field)` is not in the table reaches a file with no role:
the walker reports it, and such a file cannot enter a manifest (Cfg 2.4).

Core's two artifact-role constants (`manifold.core.engine.ROLES`, five members, and `manifold.core.artifacts.ROLES`, six)
differ in one member, `CORE_ROLE_DIFFERENCE`. Both are vocabularies of a run's *outputs*; this list is a vocabulary of
its *inputs* and follows neither: it follows Cfg A.2. The engine package's output side (`adapter.PASSTHROUGH_ROLES`)
emits `preview`, so it follows `artifacts.ROLES`. Neither core constant is edited.
"""

ORIGIN = "dirsig"
ENTRY_ROLE = "dirsig:sim"
PARAMETER, ASSET = "parameter", "asset"

# Cfg A.2, in its order; the read class is its last column (Cfg 6.2 names the eight parameter roles).
ROLES = {
    "dirsig:sim": PARAMETER,
    "dirsig:tasks": PARAMETER,
    "dirsig:motion": PARAMETER,
    "dirsig:platform": PARAMETER,
    "dirsig:platform_input": PARAMETER,
    "dirsig:weather": PARAMETER,
    "dirsig:atmosphere": PARAMETER,
    "dirsig:atmosphere_db": ASSET,
    "dirsig:ephemeris": ASSET,
    "dirsig:scene": ASSET,
    "dirsig:geometry_list": ASSET,
    "dirsig:geometry_object": ASSET,
    "dirsig:instance_motion": PARAMETER,
    "dirsig:material_db": ASSET,
    "dirsig:emissivity": ASSET,
    "dirsig:extinction": ASSET,
    "dirsig:map_image": ASSET,
    "dirsig:volume": ASSET,
    "dirsig:other_input": ASSET,
}

CORE_ROLE_DIFFERENCE = "preview"   # in manifold.core.artifacts.ROLES (six), not in manifold.core.engine.ROLES (five)
FOLLOWS = "Cfg A.2"                # neither core constant: those name output artifacts, this list names input files

# (referrer, field) -> role. Referrers: the entry (`jsim` JSON, `sim` legacy XML), and the kinds the walker reads.
REFERENCES = {
    # .jsim plugin inputs (Cfg A.2 dirsig:sim row) and the scene list
    ("jsim", "scene_list.inputs"): "dirsig:scene",
    ("jsim", "BasicPlatform.platform_filename"): "dirsig:platform",
    ("jsim", "BasicPlatform.motion_filename"): "dirsig:motion",
    ("jsim", "BasicPlatform.tasks_filename"): "dirsig:tasks",
    ("jsim", "ThermWeather.filename"): "dirsig:weather",
    ("jsim", "NewAtmosphere.hdf_filename"): "dirsig:atmosphere_db",
    ("jsim", "FourCurveAtmosphere.database"): "dirsig:atmosphere_db",
    ("jsim", "BasicAtmosphere.atmosphere_filename"): "dirsig:atmosphere",
    # legacy .sim (XML): <scene externalfile=...> and its siblings
    ("sim", "scene"): "dirsig:scene",
    ("sim", "platform"): "dirsig:platform",
    ("sim", "platformmotion"): "dirsig:motion",
    ("sim", "tasklist"): "dirsig:tasks",
    ("sim", "atmosphericconditions"): "dirsig:atmosphere",
    # .atm (<atmosphericconditions>): weather and database
    ("atmosphere", "classicdata.filename"): "dirsig:weather",
    ("atmosphere", "adbfile"): "dirsig:atmosphere_db",
    # .platform: any file it names (Cfg A.2 dirsig:platform_input)
    ("platform", "filename"): "dirsig:platform_input",
    # .scene
    ("scene", "geometrylistinclude"): "dirsig:geometry_list",
    ("scene", "matfilename"): "dirsig:material_db",
    ("scene", "materialmap.filename"): "dirsig:map_image",
    ("scene", "texturemap.filename"): "dirsig:map_image",
    # geometry list (.glist)
    ("geometry_list", "glist.filename"): "dirsig:geometry_list",
    ("geometry_list", "basegeometry.filename"): "dirsig:geometry_object",
    ("geometry_list", "localmaterials"): "dirsig:material_db",
    ("geometry_list", "dynamicinstance.filename"): "dirsig:instance_motion",
    # material file (.mat): BLOCK.KEY
    ("material_db", "REFLECTANCE_PROP.EMISSIVITY_FILE"): "dirsig:emissivity",
    ("material_db", "EMISSIVITY_PROP.FILENAME"): "dirsig:emissivity",
    ("material_db", "REFLECTANCE_PROP.TXT_FILENAME"): "dirsig:other_input",
    ("material_db", "TRANSMITTANCE_PROP.TXT_FILENAME"): "dirsig:other_input",
    ("material_db", "EMISSIVITY_PROP.TXT_FILENAME"): "dirsig:other_input",
    ("material_db", "EXTINCTION_PROP.FILENAME"): "dirsig:extinction",
    ("material_db", "IMAGE.FILENAME"): "dirsig:map_image",
    ("material_db", "MATERIAL_MAP.IMAGE_FILENAME"): "dirsig:map_image",
    ("material_db", "TEMP_SOLVER.IMAGE_FILENAME"): "dirsig:map_image",
}

# Referenced fields this table deliberately leaves without a role, with the reason: a walk that reaches such a file
# reports it as unroled. Each is a judgment against A.2's wording, not a gap in the walker.
UNROLED = {
    ("material_db", "REFLECTANCE_PROP.BRDF_FIT_FILE"): "a BRDF model fit, not a reflectance curve (other_input's scope)",
    ("material_db", "REFLECTANCE_PROP.PARAMETER_FILE"): "a BRDF model parameter file, not a curve",
    ("material_db", "TEMP_SOLVER.FILENAME"): "a temperature table: no role names temperature input",
    ("material_db", "MATERIAL_ENTRY.SOURCE_SHAPE"): "a light-source shape (.ies): no role names source input",
    ("material_db", "MATERIAL_ENTRY.BUNDLE_FILENAME"): "a compiled material bundle (.mat.hdf): material_db names source "
                                                       "definitions",
    ("atmosphere", "modtrantape5file"): "a MODTRAN tape5 card: atmosphere_db names the built database only",
}


def role_for(referrer, field):
    """The role `REFERENCES` assigns to a file named by `field` in a `referrer` file, or None (no role covers it)."""
    return REFERENCES.get((referrer, field))


def read_class(role):
    """`parameter` or `asset`; KeyError for a role outside the closed list."""
    return ROLES[role]

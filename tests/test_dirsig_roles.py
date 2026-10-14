"""The DIRSIG run-tree role list (round 46 A): the closed, namespaced list of Cfg A.2 with each role's read class, the
table that assigns a role from the referencing element, and the recorded difference between core's two artifact-role
constants (read, not edited)."""
from manifold.core import artifacts, engine
from manifold.engines.dirsig import adapter, roles

# Cfg A.2, in order; the last column is the read class.
CFG_A2 = ["sim", "tasks", "motion", "platform", "platform_input", "weather", "atmosphere", "atmosphere_db", "ephemeris",
          "scene", "geometry_list", "geometry_object", "instance_motion", "material_db", "emissivity", "extinction",
          "map_image", "volume", "other_input"]
# Cfg 6.2: the parameter roles of the dirsig origin; every other role is an asset role.
CFG_62_PARAMETER = {"dirsig:sim", "dirsig:tasks", "dirsig:motion", "dirsig:platform", "dirsig:platform_input",
                    "dirsig:weather", "dirsig:atmosphere", "dirsig:instance_motion"}


def test_the_list_is_cfg_a2_namespaced_and_in_order():
    assert list(roles.ROLES) == [f"dirsig:{name}" for name in CFG_A2]
    assert all(r.startswith(roles.ORIGIN + ":") for r in roles.ROLES)


def test_each_role_carries_the_read_class_of_cfg_62():
    assert {r for r, c in roles.ROLES.items() if c == roles.PARAMETER} == CFG_62_PARAMETER
    assert {r for r, c in roles.ROLES.items() if c == roles.ASSET} == set(roles.ROLES) - CFG_62_PARAMETER
    assert roles.read_class("dirsig:scene") == "asset"


def test_the_entry_role_is_dirsig_sim():
    assert roles.ENTRY_ROLE == "dirsig:sim" and roles.ENTRY_ROLE in roles.ROLES


def test_every_assigned_role_is_in_the_closed_list():
    assert set(roles.REFERENCES.values()) <= set(roles.ROLES)


def test_a_ppd_takes_its_role_from_the_referencing_element():
    """Cfg A.2: a `.ppd` named by `BasicPlatform` is `dirsig:motion`; one named in a `<dynamicinstance>` is
    `dirsig:instance_motion`. The table is keyed by referrer and field, never by extension."""
    assert roles.role_for("jsim", "BasicPlatform.motion_filename") == "dirsig:motion"
    assert roles.role_for("sim", "platformmotion") == "dirsig:motion"
    assert roles.role_for("geometry_list", "dynamicinstance.filename") == "dirsig:instance_motion"
    assert not any("." + ext in field for _, field in roles.REFERENCES for ext in ("ppd", "glist", "mat", "ems"))


def test_a_field_without_a_role_returns_none_and_unroled_fields_are_not_assigned():
    assert roles.role_for("material_db", "REFLECTANCE_PROP.BRDF_FIT_FILE") is None
    assert roles.role_for("jsim", "PointCollectors.input") is None
    assert not set(roles.UNROLED) & set(roles.REFERENCES)


def test_the_core_difference_is_recorded_and_core_is_unchanged():
    """`manifold.core.engine.ROLES` (five) and `manifold.core.artifacts.ROLES` (six) differ in one member; both name
    output artifacts and this input list follows neither (Cfg A.2). The engine package's output roles include it."""
    assert len(engine.ROLES) == 5 and len(artifacts.ROLES) == 6
    assert set(artifacts.ROLES) - set(engine.ROLES) == {roles.CORE_ROLE_DIFFERENCE}
    assert set(engine.ROLES) <= set(artifacts.ROLES)
    assert roles.FOLLOWS == "Cfg A.2"
    assert not {f"dirsig:{r}" for r in artifacts.ROLES} & set(roles.ROLES)
    out = {role for _, role in adapter.PASSTHROUGH_ROLES}
    assert roles.CORE_ROLE_DIFFERENCE in out and out <= set(artifacts.ROLES)

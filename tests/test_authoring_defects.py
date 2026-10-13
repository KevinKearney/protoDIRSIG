"""Round 35's authoring defects fixed outside `packages/core` in round 41 (BACKLOG "Authoring friction (round 35)"):
a missing settings member is refused naming it, a recipe file outside a `recipes/` folder composes through `Workspace`,
and the engine packages' wrong-hash refusals print both digests in full. Round 41 also wrote an absent `black_level` as
0; round 43 reverted that (a second run id for one job), so an absent `black_level` is refused by name like the other
three members. Engine-free: nothing is rendered."""
import copy
import re
from pathlib import Path

import pytest
import yaml

from manifold.core.run_spec import RunSpecError
from manifold.sim import Workspace

ROOT = Path(__file__).resolve().parents[1]
FULL = re.compile(r"sha256:[0-9a-f]{64}")


@pytest.fixture(scope="module")
def ws(tmp_path_factory):
    return Workspace.local(work=tmp_path_factory.mktemp("authoring") / "work")


@pytest.fixture(scope="module")
def recipe(ws):
    return ws.get_recipe("auror_ref").document


def _without(doc, member):
    d = copy.deepcopy(doc)
    del d["settings"][0][member]
    return d


@pytest.mark.parametrize("member", ("exposure_time", "frame_rate", "gain", "black_level"))
def test_a_missing_settings_member_is_refused_by_name(ws, recipe, member):
    run = ws.validate(_without(recipe, member)).runs[0]
    check = next(c for c in run.checks if not c.passed)
    assert not run.valid and check.check == "library_files"
    detail = check.errors[0].detail
    assert f"descriptor.settings[0] (entry 'auror-nir') has no {member!r}" in detail and "KeyError" not in detail


def test_an_absent_black_level_is_refused_because_a_default_would_be_a_second_run_id(ws, recipe):
    """Round 41 wrote an absent `black_level` as 0; round 43 reverted it (review report section 3.1). The platform DIRSIG
    renders was the same, but the composed spec without the member is another spec, so its run id is not the explicit
    0's: one job under two run ids. The refusal names the member, as for the other three."""
    assert recipe["settings"][0]["black_level"]["value"] == 0
    stated, omitted = ws.compose(recipe).runs[0].run_spec, ws.compose(_without(recipe, "black_level")).runs[0].run_spec
    assert stated != omitted and omitted["descriptor"]["settings"][0] == {
        k: v for k, v in stated["descriptor"]["settings"][0].items() if k != "black_level"}
    run = ws.validate(_without(recipe, "black_level")).runs[0]
    check = next(c for c in run.checks if not c.passed)
    assert not run.valid and check.check == "library_files"
    assert "descriptor.settings[0] (entry 'auror-nir') has no 'black_level'" in check.errors[0].detail
    assert ws.validate(recipe).runs[0].valid


def test_the_black_level_refusal_still_refuses_a_non_zero_value(ws, recipe):
    bad = copy.deepcopy(recipe)
    bad["settings"][0]["black_level"]["value"] = 12
    with pytest.raises(Exception, match="use 0 or omit it"):
        ws.validate(bad)


def test_a_recipe_file_outside_a_recipes_folder_composes_as_its_document(ws, recipe, tmp_path):
    path = tmp_path / "elsewhere" / "my_recipe.yaml"
    path.parent.mkdir()
    path.write_text(yaml.safe_dump(recipe))
    by_file, by_dict = ws.validate(path).runs[0], ws.validate(yaml.safe_load(path.read_text())).runs[0]
    assert by_file.valid and by_file.run_id == by_dict.run_id
    assert ws.compose(path).recipe.name == "my_recipe"
    assert ws.validate("auror_ref").runs[0].run_id == by_dict.run_id     # a library recipe as before


def test_the_pass_through_wrong_hash_refusal_prints_both_digests(tmp_path):
    from manifold.engines.dirsig.passthrough_spec import resolve_passthrough
    (tmp_path / "demos" / "x").mkdir(parents=True)
    (tmp_path / "demos" / "x" / "a.sim").write_text("x\n")
    spec = {"engine": {"passthrough": {"directory": {"name": "demos/x", "content_hash": "sha256:" + "0" * 64},
                                       "simulation": "a.sim"}}}
    with pytest.raises(RunSpecError, match="does not match the directory") as e:
        resolve_passthrough(spec, tmp_path)
    assert len(FULL.findall(str(e.value))) == 2 and "..." not in str(e.value)


def test_the_satsim_wrong_hash_refusal_prints_both_digests(tmp_path):
    from manifold.engines.satsim.adapter import resolve_config
    (tmp_path / "satsim").mkdir()
    (tmp_path / "satsim" / "c.yaml").write_text("sim: {}\n")
    block = {"config": {"name": "satsim/c.yaml", "content_hash": "sha256:" + "0" * 64}}
    with pytest.raises(RunSpecError, match="does not match") as e:
        resolve_config(block, tmp_path)
    assert len(FULL.findall(str(e.value))) == 2 and "..." not in str(e.value)

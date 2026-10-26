import copy

import pytest

from gems.artifact_inventory import compare, git_sha, inventory, summarize

SHA = "a" * 40
BLOB = "b" * 40


def tree():
    return {
        "sha": SHA,
        "truncated": False,
        "tree": [
            {
                "path": "docs/downloads/a.TIF",
                "sha": BLOB,
                "size": 12,
                "mode": "100644",
                "type": "blob",
            }
        ],
    }


def test_inventory_and_changes():
    old = inventory(tree(), SHA)
    new = copy.deepcopy(old)
    new["docs/downloads/a.TIF"]["git_blob_sha1"] = "c" * 40
    new["new.tif"] = copy.deepcopy(next(iter(old.values())))
    rows = compare(old, new)
    assert summarize(rows) == {"added": 1, "changed": 1, "removed": 0, "unchanged": 0}
    assert summarize(compare(old, old))["unchanged"] == 1
    assert summarize(compare(old, {}))["removed"] == 1
    assert old["docs/downloads/a.TIF"]["git_blob_sha1"] == BLOB
    assert old["docs/downloads/a.TIF"]["content_validation"] == "not_performed"


@pytest.mark.parametrize(
    "change", [{"truncated": True}, {"truncated": None}, {"sha": "c" * 40}, {"tree": None}]
)
def test_incomplete_tree_rejected(change):
    value = tree()
    value.update(change)
    with pytest.raises(ValueError):
        inventory(value, SHA)


@pytest.mark.parametrize(
    "change",
    [
        {"path": "../bad.tif"},
        {"path": "/absolute.tif"},
        {"path": ""},
        {"sha": "not-a-sha"},
        {"size": True},
        {"size": -1},
        {"size": None},
        {"mode": "160000"},
    ],
)
def test_bad_entry_rejected(change):
    value = tree()
    value["tree"][0].update(change)
    with pytest.raises(ValueError):
        inventory(value, SHA)


def test_duplicate_paths_rejected():
    value = tree()
    value["tree"] *= 2
    with pytest.raises(ValueError):
        inventory(value, SHA)


def test_archives_symlinks_and_non_artifacts():
    value = tree()
    value["tree"] += [
        {**value["tree"][0], "path": "a.zip"},
        {**value["tree"][0], "path": "b.tiff", "mode": "120000"},
        {"path": "docs", "type": "tree"},
        {"path": "README.md", "type": "blob"},
    ]
    result = inventory(value, SHA)
    assert len(result) == 3
    assert result["b.tiff"]["mode"] == "120000"


@pytest.mark.parametrize("value", [None, 123, "a" * 39, "A" * 40, "../main"])
def test_full_sha_required(value):
    with pytest.raises(ValueError):
        git_sha(value)

"""The engine discovers nodes only through this entry-point group, so a typo'd
module path or a renamed class breaks node loading without failing any other
test. These guard the publisher-side contract."""

from importlib.metadata import entry_points

NODES_GROUP = "aceteam_workflow_engine.nodes"

EXPECTED_NODES = {
    "LLM",
    "APICall",
    "BrowserFetch",
    "XPathExtract",
    "Equal",
    "NotEqual",
    "GreaterThan",
    "GreaterThanEqual",
    "LessThan",
    "LessThanEqual",
    "And",
    "Or",
    "Not",
}


def test_all_nodes_advertised():
    names = {ep.name for ep in entry_points(group=NODES_GROUP)}
    assert names == EXPECTED_NODES


def test_entry_points_load_and_type_matches_name():
    for ep in entry_points(group=NODES_GROUP):
        cls = ep.load()
        assert cls.model_fields["type"].default == ep.name

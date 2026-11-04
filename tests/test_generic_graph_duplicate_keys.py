"""Ambiguous JSON must not lose data before resource dispatch or preview."""

import json

import pytest

from opensmell.experimental.generic_graph import generic_graph_loads, generic_graph_to_dict


ENVELOPE = '{"format":"org.opensmell.experimental.generic-resource-graph","version":"0.1",'


@pytest.mark.parametrize("body", [
    '"resources":[],"version":"0.1"',
    '"resources":[],"extension":{"value":1,"value":2}',
    '"resources":[],"extension":{"value":1,"value":1}',
    r'"resources":[],"extension":{"value":1,"\u0076alue":2}',
    '"resources":[{"id":"future","type":"custom","payload":[{"x":1,"x":2}]}]',
    '"resources":[{"id":"first","id":"second","type":"custom"}]',
])
def test_generic_graph_rejects_duplicate_keys_at_every_depth(body):
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        generic_graph_loads(ENVELOPE + body + "}")


def test_distinct_objects_and_case_sensitive_keys_remain_lossless():
    text = ENVELOPE + '"resources":[{"id":"future","type":"custom","payload":[{"x":1},{"x":2}]}],"extension":{"x":1,"X":2}}'
    assert generic_graph_to_dict(generic_graph_loads(text)) == json.loads(text)

"""Tests for the experimental Annotation resource type."""

from __future__ import annotations

import pytest

from opensmell.experimental.annotation import (
    ANNOTATION_RESOURCE_TYPE,
    ANNOTATION_RESOURCE_TYPE_VERSION,
    Annotation,
    annotation_from_dict,
    annotation_to_dict,
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (
    GenericResource,
    GenericResourceGraph,
    ResourceTypeRegistry,
    create_default_resource_type_registry,
    generic_graph_from_dict,
    generic_graph_to_dict,
)
from opensmell.experimental.molecule import (
    Molecule,
    register_molecule_resource_type,
)
from opensmell.experimental.resources import (
    Reference,
)
from opensmell.experimental.scheme import (
    Scheme,
)


SEMANTIC_ANNOTATION_SCHEME_ID = (
    "org.opensmell.semantic.annotations"
)
SEMANTIC_ANNOTATION_SCHEME_VERSION = "0.1"


def _semantic_scheme() -> Scheme:
    return Scheme(
        id=SEMANTIC_ANNOTATION_SCHEME_ID,
        version=SEMANTIC_ANNOTATION_SCHEME_VERSION,
    )


def _semantic_data() -> dict[str, object]:
    return {
        "annotations": [
            {
                "value": "floral",
                "language": "en",
                "state": "present",
            },
            {
                "value": "spice",
                "language": "en",
                "state": "absent",
            },
            {
                "value": "woody&mossy",
                "language": "en",
                "state": "unknown",
            },
        ]
    }


def _annotation(
    *,
    annotation_id: str = "annotation-1",
    subject_id: str = "molecule-1",
) -> Annotation:
    return Annotation(
        id=annotation_id,
        subject=Reference(
            resource_id=subject_id,
        ),
        scheme=_semantic_scheme(),
        data=_semantic_data(),
    )


def _registry() -> ResourceTypeRegistry:
    registry = create_default_resource_type_registry()

    register_molecule_resource_type(
        registry
    )
    register_annotation_resource_type(
        registry
    )

    return registry


def test_annotation_resource_constants() -> None:
    assert (
        ANNOTATION_RESOURCE_TYPE
        == "org.opensmell.annotation"
    )
    assert (
        ANNOTATION_RESOURCE_TYPE_VERSION
        == "0.1"
    )


def test_annotation_uses_generic_scheme() -> None:
    annotation = _annotation()

    assert isinstance(
        annotation.scheme,
        Scheme,
    )
    assert (
        annotation.scheme.id
        == SEMANTIC_ANNOTATION_SCHEME_ID
    )
    assert (
        annotation.scheme.version
        == SEMANTIC_ANNOTATION_SCHEME_VERSION
    )


def test_annotation_accepts_valid_resource() -> None:
    annotation = _annotation()

    assert annotation.id == "annotation-1"
    assert (
        annotation.subject.resource_id
        == "molecule-1"
    )
    assert (
        annotation.scheme.id
        == SEMANTIC_ANNOTATION_SCHEME_ID
    )
    assert annotation.data == _semantic_data()


@pytest.mark.parametrize(
    ("value", "exception"),
    [
        ("", ValueError),
        (None, TypeError),
        (123, TypeError),
    ],
)
def test_annotation_rejects_invalid_id(
    value: object,
    exception: type[Exception],
) -> None:
    with pytest.raises(exception):
        Annotation(
            id=value,
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme=_semantic_scheme(),
            data={},
        )


def test_annotation_requires_reference_subject() -> None:
    with pytest.raises(TypeError):
        Annotation(
            id="annotation-1",
            subject="molecule-1",
            scheme=_semantic_scheme(),
            data={},
        )


def test_annotation_requires_generic_scheme() -> None:
    with pytest.raises(TypeError):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme={
                "id": SEMANTIC_ANNOTATION_SCHEME_ID,
                "version": "0.1",
            },
            data={},
        )


def test_annotation_requires_dict_data() -> None:
    with pytest.raises(TypeError):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme=_semantic_scheme(),
            data=[],
        )


def test_annotation_requires_dict_extra() -> None:
    with pytest.raises(TypeError):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme=_semantic_scheme(),
            data={},
            extra=[],
        )


@pytest.mark.parametrize(
    "reserved_field",
    [
        "type",
        "type_version",
        "id",
        "subject",
        "scheme",
        "data",
    ],
)
def test_annotation_rejects_reserved_extra_fields(
    reserved_field: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="reserved",
    ):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme=_semantic_scheme(),
            data={},
            extra={
                reserved_field: "conflict",
            },
        )


def test_annotation_data_must_be_json_compatible() -> None:
    with pytest.raises(TypeError):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme=_semantic_scheme(),
            data={
                "invalid": object(),
            },
        )


def test_annotation_data_object_keys_must_be_strings() -> None:
    with pytest.raises(TypeError):
        Annotation(
            id="annotation-1",
            subject=Reference(
                resource_id="molecule-1"
            ),
            scheme=_semantic_scheme(),
            data={
                "nested": {
                    1: "invalid",
                }
            },
        )


def test_annotation_serialization() -> None:
    annotation = _annotation()

    document = annotation_to_dict(
        annotation
    )

    assert document == {
        "type": "org.opensmell.annotation",
        "type_version": "0.1",
        "id": "annotation-1",
        "subject": {
            "resource_id": "molecule-1",
        },
        "scheme": {
            "id": (
                "org.opensmell.semantic.annotations"
            ),
            "version": "0.1",
        },
        "data": _semantic_data(),
    }


def test_annotation_round_trip() -> None:
    original = _annotation()

    document = annotation_to_dict(
        original
    )

    recovered = annotation_from_dict(
        document
    )

    assert recovered == original
    assert isinstance(
        recovered.scheme,
        Scheme,
    )
    assert (
        annotation_to_dict(
            recovered
        )
        == document
    )


def test_annotation_preserves_resource_extensions() -> None:
    original = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1"
        ),
        scheme=_semantic_scheme(),
        data=_semantic_data(),
        extra={
            "provenance": {
                "source": "OdorNet",
            },
            "org.example.extension": {
                "value": 42,
            },
        },
    )

    document = annotation_to_dict(
        original
    )
    recovered = annotation_from_dict(
        document
    )

    assert recovered.extra == original.extra
    assert (
        annotation_to_dict(
            recovered
        )
        == document
    )


def test_annotation_copies_extra_on_construction() -> None:
    extra = {
        "provenance": {
            "source": "OdorNet",
        }
    }

    annotation = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1"
        ),
        scheme=_semantic_scheme(),
        data={},
        extra=extra,
    )

    provenance = extra["provenance"]
    assert isinstance(
        provenance,
        dict,
    )

    provenance["source"] = "changed"

    assert annotation.extra == {
        "provenance": {
            "source": "OdorNet",
        }
    }


def test_annotation_preserves_reference_extensions() -> None:
    original = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1",
            extra={
                "role": "annotated-resource",
            },
        ),
        scheme=_semantic_scheme(),
        data=_semantic_data(),
    )

    document = annotation_to_dict(
        original
    )
    recovered = annotation_from_dict(
        document
    )

    assert recovered.subject.extra == {
        "role": "annotated-resource",
    }
    assert (
        annotation_to_dict(
            recovered
        )
        == document
    )


def test_annotation_preserves_scheme_extensions() -> None:
    original = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1"
        ),
        scheme=Scheme(
            id=SEMANTIC_ANNOTATION_SCHEME_ID,
            version="0.1",
            extra={
                "vocabulary": {
                    "id": "org.example.taxonomy",
                    "version": "1.0",
                }
            },
        ),
        data=_semantic_data(),
    )

    document = annotation_to_dict(
        original
    )
    recovered = annotation_from_dict(
        document
    )

    assert isinstance(
        recovered.scheme,
        Scheme,
    )
    assert (
        recovered.scheme.extra
        == original.scheme.extra
    )
    assert (
        annotation_to_dict(
            recovered
        )
        == document
    )


def test_annotation_preserves_unicode() -> None:
    original = Annotation(
        id="annotation-unicode",
        subject=Reference(
            resource_id="molecule-unicode"
        ),
        scheme=Scheme(
            id="org.example.semantic",
            version="0.1",
        ),
        data={
            "annotations": [
                {
                    "value": "цветочный",
                    "language": "ru",
                    "state": "present",
                },
                {
                    "value": "épicé",
                    "language": "fr",
                    "state": "absent",
                },
            ]
        },
        extra={
            "note": "аромат 🌸",
        },
    )

    document = annotation_to_dict(
        original
    )
    recovered = annotation_from_dict(
        document
    )

    assert recovered == original
    assert (
        annotation_to_dict(
            recovered
        )
        == document
    )


@pytest.mark.parametrize(
    "resource_type",
    [
        "annotation",
        "org.example.annotation",
        "org.opensmell.molecule",
    ],
)
def test_annotation_parser_rejects_wrong_type(
    resource_type: str,
) -> None:
    document = annotation_to_dict(
        _annotation()
    )
    document["type"] = resource_type

    with pytest.raises(
        ValueError,
        match="unexpected",
    ):
        annotation_from_dict(
            document
        )


@pytest.mark.parametrize(
    "version",
    [
        "0.2",
        "1.0",
        "9.9",
    ],
)
def test_annotation_parser_rejects_unsupported_version(
    version: str,
) -> None:
    document = annotation_to_dict(
        _annotation()
    )
    document["type_version"] = version

    with pytest.raises(
        ValueError,
        match="unsupported",
    ):
        annotation_from_dict(
            document
        )


@pytest.mark.parametrize(
    "field",
    [
        "subject",
        "scheme",
        "data",
    ],
)
def test_annotation_parser_requires_fields(
    field: str,
) -> None:
    document = annotation_to_dict(
        _annotation()
    )
    del document[field]

    with pytest.raises(ValueError):
        annotation_from_dict(
            document
        )


def test_annotation_registration() -> None:
    registry = ResourceTypeRegistry()

    register_annotation_resource_type(
        registry
    )

    handler = registry.handler_for_resource_type(
        ANNOTATION_RESOURCE_TYPE,
        ANNOTATION_RESOURCE_TYPE_VERSION,
    )

    assert handler is not None
    assert handler.python_type is Annotation


def test_annotation_not_registered_by_default() -> None:
    registry = (
        create_default_resource_type_registry()
    )

    handler = registry.handler_for_resource_type(
        ANNOTATION_RESOURCE_TYPE,
        ANNOTATION_RESOURCE_TYPE_VERSION,
    )

    assert handler is None


def test_future_annotation_version_falls_back_to_generic() -> None:
    registry = _registry()

    document = annotation_to_dict(
        _annotation()
    )
    document["type_version"] = "9.9"
    document["future_field"] = {
        "preserve": True,
    }

    graph_document = {
        "format": (
            "org.opensmell.experimental."
            "generic-resource-graph"
        ),
        "version": "0.1",
        "resources": [
            document,
        ],
    }

    graph = generic_graph_from_dict(
        graph_document,
        registry=registry,
    )

    assert len(graph.resources) == 1

    resource = graph.resources[0]

    assert isinstance(
        resource,
        GenericResource,
    )
    assert (
        resource.type
        == ANNOTATION_RESOURCE_TYPE
    )
    assert resource.type_version == "9.9"

    recovered = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    assert recovered == graph_document


def test_molecule_and_annotation_can_share_graph() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = _annotation()

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    assert len(graph.resources) == 2
    assert graph.get(
        "molecule-1"
    ) is molecule
    assert graph.get(
        "annotation-1"
    ) is annotation


def test_annotation_subject_resolves_to_molecule() -> None:
    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = _annotation()

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    resolved = graph.resolve(
        annotation.subject
    )

    assert resolved is molecule


def test_annotation_may_reference_unresolved_subject() -> None:
    annotation = _annotation(
        subject_id="external-molecule"
    )

    graph = GenericResourceGraph(
        resources=[
            annotation,
        ]
    )

    assert (
        graph.resolve(
            annotation.subject
        )
        is None
    )


def test_molecule_annotation_graph_round_trip() -> None:
    registry = _registry()

    molecule = Molecule(
        id="molecule-1",
        smiles="CCO",
    )

    annotation = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1"
        ),
        scheme=_semantic_scheme(),
        data=_semantic_data(),
        extra={
            "provenance": {
                "source": "OdorNet",
            }
        },
    )

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
        ]
    )

    document = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    recovered = generic_graph_from_dict(
        document,
        registry=registry,
    )

    assert len(recovered.resources) == 2

    recovered_molecule = recovered.get(
        "molecule-1"
    )
    recovered_annotation = recovered.get(
        "annotation-1"
    )

    assert isinstance(
        recovered_molecule,
        Molecule,
    )
    assert isinstance(
        recovered_annotation,
        Annotation,
    )
    assert isinstance(
        recovered_annotation.scheme,
        Scheme,
    )

    assert (
        recovered.resolve(
            recovered_annotation.subject
        )
        is recovered_molecule
    )

    assert (
        recovered_annotation.data
        == _semantic_data()
    )

    assert (
        recovered_annotation.extra
        == {
            "provenance": {
                "source": "OdorNet",
            }
        }
    )

    assert (
        generic_graph_to_dict(
            recovered,
            registry=registry,
        )
        == document
    )


def test_unknown_resource_can_coexist_with_annotation() -> None:
    registry = _registry()

    annotation = _annotation()

    unknown = GenericResource(
        id="future-resource-1",
        type="org.example.future-resource",
        type_version="7.0",
        data={
            "payload": {
                "hello": "world",
            }
        },
    )

    graph = GenericResourceGraph(
        resources=[
            annotation,
            unknown,
        ]
    )

    document = generic_graph_to_dict(
        graph,
        registry=registry,
    )

    recovered = generic_graph_from_dict(
        document,
        registry=registry,
    )

    recovered_annotation = recovered.get(
        "annotation-1"
    )
    recovered_unknown = recovered.get(
        "future-resource-1"
    )

    assert isinstance(
        recovered_annotation,
        Annotation,
    )
    assert isinstance(
        recovered_unknown,
        GenericResource,
    )

    assert (
        recovered_unknown.type
        == "org.example.future-resource"
    )
    assert (
        recovered_unknown.type_version
        == "7.0"
    )

    assert (
        generic_graph_to_dict(
            recovered,
            registry=registry,
        )
        == document
    )


def test_annotation_data_is_independent_from_input_mapping() -> None:
    data = _semantic_data()

    annotation = Annotation(
        id="annotation-1",
        subject=Reference(
            resource_id="molecule-1"
        ),
        scheme=_semantic_scheme(),
        data=data,
    )

    annotations = data["annotations"]
    assert isinstance(
        annotations,
        list,
    )

    first = annotations[0]
    assert isinstance(
        first,
        dict,
    )

    first["state"] = "changed"

    stored_annotations = (
        annotation.data["annotations"]
    )
    assert isinstance(
        stored_annotations,
        list,
    )

    stored_first = stored_annotations[0]
    assert isinstance(
        stored_first,
        dict,
    )

    assert (
        stored_first["state"]
        == "present"
    )


def test_serialized_annotation_is_independent_from_resource() -> None:
    annotation = _annotation()

    document = annotation_to_dict(
        annotation
    )

    raw_data = document["data"]
    assert isinstance(
        raw_data,
        dict,
    )

    raw_annotations = raw_data["annotations"]
    assert isinstance(
        raw_annotations,
        list,
    )

    first = raw_annotations[0]
    assert isinstance(
        first,
        dict,
    )

    first["state"] = "changed"

    stored_annotations = (
        annotation.data["annotations"]
    )
    assert isinstance(
        stored_annotations,
        list,
    )

    stored_first = stored_annotations[0]
    assert isinstance(
        stored_first,
        dict,
    )

    assert (
        stored_first["state"]
        == "present"
    )


def test_annotation_does_not_interpret_scheme_data() -> None:
    annotation = Annotation(
        id="annotation-opaque",
        subject=Reference(
            resource_id="resource-1"
        ),
        scheme=Scheme(
            id="org.example.custom",
            version="42",
        ),
        data={
            "anything": {
                "is": [
                    "allowed",
                    123,
                    True,
                    None,
                ]
            }
        },
    )

    recovered = annotation_from_dict(
        annotation_to_dict(
            annotation
        )
    )

    assert recovered == annotation
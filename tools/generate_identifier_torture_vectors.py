"""Generate interoperability torture vectors for experimental Resource IDs.

The generated vectors exercise canonical JSON serialization, UTF-8 encoding,
Unicode preservation, escaping, structural boundaries, and deterministic
UUIDv5 generation.

Composite source-identity keys are structural OpenSmell role names and are
therefore restricted to canonical ASCII identifiers.

Unicode remains fully supported in source-identity values.

Nothing in this module is normative OpenSmell 0.1.
"""

from __future__ import annotations

import json
from pathlib import Path

from opensmell.experimental.identifiers import (
    canonical_generation_name,
    deterministic_resource_id_from_source,
)


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    ROOT
    / "examples"
    / "identifier_torture_vectors.json"
)


VECTOR_INPUTS = [
    {
        "name": "ASCII",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee",
    },
    {
        "name": "Latin NFC",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "café",
    },
    {
        "name": "Latin decomposed NFD-like",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "cafe\u0301",
    },
    {
        "name": "CJK",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "咖啡",
    },
    {
        "name": "Emoji",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee ☕",
    },
    {
        "name": "Quote",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": 'coffee"bean',
    },
    {
        "name": "Backslash",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\\bean",
    },
    {
        "name": "Newline",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\nbean",
    },
    {
        "name": "Tab",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\tbean",
    },
    {
        "name": "Carriage return",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\rbean",
    },
    {
        "name": "Backspace",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\bbean",
    },
    {
        "name": "Form feed",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\fbean",
    },
    {
        "name": "Control U+0001",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\u0001bean",
    },
    {
        "name": "Line separator U+2028",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\u2028bean",
    },
    {
        "name": "Paragraph separator U+2029",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": "coffee\u2029bean",
    },
    {
        "name": "Composite special characters",
        "dataset": "torture",
        "resource_type": "observation",
        "source_identity": {
            "stimulus": 'coffee|"\\bean',
            "target": "subject\n001",
        },
    },
    {
        "name": "Composite ASCII key ordering",
        "dataset": "torture",
        "resource_type": "target",
        "source_identity": {
            "z_field": "ascii",
            "a_field": "first",
            "unicode_latin": "café",
            "unicode_cjk": "咖啡",
        },
    },
]


def build_vector(vector_input: dict) -> dict:
    """Build one complete golden interoperability vector."""

    dataset = vector_input["dataset"]
    resource_type = vector_input["resource_type"]
    source_identity = vector_input["source_identity"]

    canonical = canonical_generation_name(
        dataset=dataset,
        resource_type=resource_type,
        source_identity=source_identity,
    )

    resource_id = deterministic_resource_id_from_source(
        dataset=dataset,
        resource_type=resource_type,
        source_identity=source_identity,
    )

    return {
        "name": vector_input["name"],
        "dataset": dataset,
        "resource_type": resource_type,
        "source_identity": source_identity,
        "canonical": canonical,
        "utf8_hex": canonical.encode("utf-8").hex(),
        "uuid": resource_id,
    }


def main() -> None:
    vectors = [
        build_vector(vector_input)
        for vector_input in VECTOR_INPUTS
    ]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            vectors,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    print(
        "OpenSmell RFC-0006 identifier torture vectors"
    )
    print("=" * 72)
    print()
    print(f"Vectors generated : {len(vectors)}")
    print(f"Output            : {OUTPUT_PATH}")
    print()

    for vector in vectors:
        print(vector["name"])
        print("-" * 72)
        print(
            "Canonical:",
            repr(vector["canonical"]),
        )
        print(
            "UTF-8 hex:",
            vector["utf8_hex"],
        )
        print(
            "UUID:",
            vector["uuid"],
        )
        print()

    print("SUCCESS")


if __name__ == "__main__":
    main()
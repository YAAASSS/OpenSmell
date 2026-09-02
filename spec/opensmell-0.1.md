# OpenSmell 0.1 Specification

- **Status:** Experimental
- **Version:** 0.1
- **Date:** September 2026
- **Related:** None

---

## 1. Introduction

OpenSmell is an open interoperability framework for digital olfaction.

This document defines the experimental OpenSmell 0.1 serialization
format.

The purpose of version 0.1 is not to provide a complete digital
olfaction standard.

Its purpose is to establish a minimal, extensible, machine-readable
container for digital odor representations that can be implemented,
exchanged, validated, and tested across applications.

OpenSmell does not define a universal scientific model of smell and
does not require any particular physical odor reproduction technology.

---

## 2. Design Principles

OpenSmell 0.1 follows these principles:

1. Odor identity is separate from odor representation.

2. An odor may contain multiple representations.

3. Representation schemes are independently defined and versioned.

4. OpenSmell does not define a universal scientific model of smell.

5. OpenSmell data is independent from rendering hardware.

6. Rendering instructions are not part of odor identity.

7. Unknown representation types and schemes do not invalidate an
   otherwise structurally valid OpenSmell document.

8. Implementations should preserve information they do not understand
   where practical.

9. OpenSmell should reuse existing scientific representations and
   identifiers when appropriate rather than redefining them.

10. Version 0.1 should remain deliberately small.

---

## 3. File Format

An OpenSmell 0.1 document MUST be encoded as UTF-8 JSON.

The recommended file extension is:

    .osmell

Example:

    coffee.osmell

An OpenSmell implementation MUST parse the file as JSON before
attempting OpenSmell-specific validation.

The `.osmell` extension identifies an OpenSmell document but does not
change the underlying JSON encoding.

---

## 4. Top-Level Structure

An OpenSmell 0.1 document MUST contain:

- `opensmell`
- `odor`

Example:

```json
{
  "opensmell": "0.1",
  "odor": {}
}
```

No rendering or device instructions are defined at the top level in
OpenSmell 0.1.

---

## 5. `opensmell`

`opensmell` identifies the version of the OpenSmell serialization
specification used by the document.

For this specification, its value MUST be:

```json
"opensmell": "0.1"
```

Implementations MUST NOT silently interpret a document using an
unsupported OpenSmell version as version 0.1.

A future OpenSmell specification may define explicit compatibility
rules between specification versions.

---

## 6. `odor`

The `odor` object represents one conceptual olfactory object.

It MUST contain:

- `id`
- `representations`

It MAY contain:

- `metadata`

Example:

```json
{
  "odor": {
    "id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
    "representations": [
      {
        "type": "semantic",
        "scheme": {
          "id": "org.opensmell.semantic.descriptors",
          "version": "0.1"
        },
        "data": {
          "descriptors": [
            {
              "value": "coffee",
              "language": "en"
            }
          ]
        }
      }
    ]
  }
}
```

---

## 7. Odor Identifier

`odor.id` MUST be a non-empty string.

OpenSmell 0.1 RECOMMENDS the use of a UUID URN for newly created
OpenSmell odor objects.

Example:

```json
"id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000"
```

The identifier identifies the OpenSmell odor object itself.

It MUST NOT be interpreted as a universal identifier for an odor
concept.

For example, two independently created OpenSmell objects describing
"rose" MAY have different identifiers.

Likewise, sharing an identifier MUST NOT by itself be interpreted as
proof that two physical odor samples are chemically or perceptually
identical.

OpenSmell 0.1 does not define a global odor registry.

A future specification or RFC MAY define mechanisms for associating
OpenSmell objects with external identifiers, scientific databases,
controlled vocabularies, or registries.

---

## 8. Metadata

`odor.metadata` is OPTIONAL.

OpenSmell 0.1 defines two optional metadata fields:

- `labels`
- `description`

Example:

```json
{
  "metadata": {
    "labels": {
      "en": "Coffee",
      "fr": "Café"
    },
    "description": "Example coffee odor used by OpenSmell."
  }
}
```

Metadata is intended primarily for human presentation.

Applications MUST NOT use human-readable labels as substitutes for
representation semantics or odor identity.

Metadata MUST NOT be required to interpret the technical
representations of an odor.

---

## 9. Labels

`metadata.labels` MUST be a JSON object when present.

Each key represents a language tag.

Each value MUST be a non-empty string.

Example:

```json
{
  "labels": {
    "en": "Coffee",
    "fr": "Café",
    "ru": "Кофе"
  }
}
```

OpenSmell 0.1 RECOMMENDS BCP 47 language tags.

Labels MUST NOT be treated as globally unique odor identifiers.

---

## 10. Description

`metadata.description` MUST be a string when present.

It is intended to provide additional human-readable information about
the odor object.

Example:

```json
{
  "description": "Example odor containing chemical and semantic representations."
}
```

Applications MUST NOT depend on `description` for machine
interpretation of representations.

---

## 11. Representations

`odor.representations` MUST be a non-empty array.

Each entry represents one digital representation associated with the
odor.

An odor MAY contain multiple representations.

Example:

```json
{
  "representations": [
    {
      "type": "chemical",
      "scheme": {
        "id": "org.opensmell.chemical.smiles",
        "version": "0.1"
      },
      "data": {
        "smiles": "O=C1OC2=CC=CC=C2C=C1"
      }
    },
    {
      "type": "semantic",
      "scheme": {
        "id": "org.opensmell.semantic.descriptors",
        "version": "0.1"
      },
      "data": {
        "descriptors": [
          {
            "value": "sweet",
            "language": "en"
          }
        ]
      }
    }
  ]
}
```

The presence of multiple representations asserts that the producer
associates them with the same OpenSmell odor object.

OpenSmell does not verify their chemical, perceptual, or physical
equivalence.

---

## 12. Representation Structure

Every representation MUST contain:

- `type`
- `scheme`
- `data`

Example:

```json
{
  "type": "perceptual",
  "scheme": {
    "id": "org.example.perceptual",
    "version": "1.0"
  },
  "data": {
    "vector": [
      0.18,
      0.72,
      0.04
    ]
  }
}
```

`type` identifies a broad representation family.

`scheme` identifies the specific rules used to interpret the
representation.

`data` contains the scheme-specific information.

---

## 13. Representation Type

`type` MUST be a non-empty string.

OpenSmell 0.1 recognizes the following standard representation type
names:

    semantic
    perceptual
    chemical
    mixture

These names identify broad representation families only.

They do not define the internal structure or meaning of `data`.

That responsibility belongs to the representation scheme.

Implementations MUST NOT assume that these are the only representation
types that may exist.

Unknown representation types MUST NOT make an otherwise structurally
valid OpenSmell document invalid.

An implementation MAY report such a representation as unsupported.

---

## 14. Semantic Representation

The `semantic` representation family describes an odor using
human-readable or vocabulary-based semantic information.

Examples include:

- free descriptors;
- controlled vocabulary terms;
- taxonomy identifiers;
- semantic labels defined by a scientific dataset.

OpenSmell itself does not assign universal meanings to semantic terms.

The exact interpretation MUST be defined by the associated scheme.

---

## 15. Perceptual Representation

The `perceptual` representation family describes an odor according to
a perceptual or computational representation scheme.

Possible examples include:

- perceptual vectors;
- embeddings;
- coordinates in an odor space;
- outputs produced by machine-learning models.

OpenSmell Core does not define:

- vector dimensionality;
- dimension meaning;
- normalization;
- distance metrics;
- prediction methodology.

Those properties belong to the referenced scheme.

---

## 16. Chemical Representation

The `chemical` representation family describes chemical information
associated with an odor.

Possible examples include:

- molecular structures;
- chemical identifiers;
- molecular representations such as SMILES.

A chemical representation does not imply that the represented chemical
information is sufficient to reproduce the perceived odor.

Likewise, OpenSmell MUST NOT interpret chemical representation data as
instructions for synthesis, handling, or physical emission.

---

## 17. Mixture Representation

The `mixture` representation family describes an odor using components
defined by a mixture scheme.

Example:

```json
{
  "type": "mixture",
  "scheme": {
    "id": "org.example.primary-system",
    "version": "1.0"
  },
  "data": {
    "components": [
      {
        "id": "primary-001",
        "amount": 0.32
      },
      {
        "id": "primary-007",
        "amount": 0.71
      }
    ]
  }
}
```

OpenSmell Core does not define the physical meaning, units, or
interpretation of `amount`.

Those semantics MUST be defined by the referenced scheme.

A mixture representation MUST NOT automatically be interpreted as a
device command.

---

## 18. Scheme

Every representation MUST contain a `scheme` object.

The scheme MUST contain:

- `id`
- `version`

Example:

```json
{
  "scheme": {
    "id": "org.opensmell.semantic.descriptors",
    "version": "0.1"
  }
}
```

Both values MUST be non-empty strings.

The scheme defines how the representation's `data` object is
interpreted.

---

## 19. Scheme Identifier

`scheme.id` identifies the interpretation scheme.

Example:

    org.opensmell.semantic.descriptors

OpenSmell 0.1 does not require scheme identifiers to be URLs.

Resolving a scheme identifier over a network MUST NOT be required to
parse an OpenSmell document.

OpenSmell 0.1 does not define a mandatory global scheme registry.

Applications MAY maintain registries of supported schemes.

---

## 20. Scheme Version

`scheme.version` identifies the version of the representation scheme.

Example:

    0.1

Scheme versions are independent from the OpenSmell specification
version.

For example, the following is conceptually possible:

    OpenSmell specification: 0.1
    Scheme version: 4.2

An implementation MAY support one version of a scheme without
supporting another.

---

## 21. Representation Data

`data` MUST be a JSON object.

Its internal structure is determined by the representation scheme.

OpenSmell Core MUST NOT attempt to infer unknown scheme semantics
solely from the contents of `data`.

For example:

```json
{
  "data": {
    "vector": [
      0.18,
      0.72,
      0.04
    ]
  }
}
```

is meaningful only when interpreted according to its associated
scheme.

---

## 22. Built-in Semantic Descriptor Scheme

OpenSmell 0.1 defines the built-in scheme:

    org.opensmell.semantic.descriptors

Scheme version:

    0.1

Representation type:

    semantic

The scheme data MUST contain:

- `descriptors`

`descriptors` MUST be a non-empty array.

Each descriptor MUST be a JSON object containing:

- `value`

A descriptor MAY contain:

- `language`

Example:

```json
{
  "type": "semantic",
  "scheme": {
    "id": "org.opensmell.semantic.descriptors",
    "version": "0.1"
  },
  "data": {
    "descriptors": [
      {
        "value": "sweet",
        "language": "en"
      },
      {
        "value": "vanilla-like",
        "language": "en"
      }
    ]
  }
}
```

`value` MUST be a non-empty string.

`language`, when present, MUST be a string.

OpenSmell does not assign universal scientific meaning to descriptor
values.

---

## 23. Built-in Chemical SMILES Scheme

OpenSmell 0.1 defines the built-in scheme:

    org.opensmell.chemical.smiles

Scheme version:

    0.1

Representation type:

    chemical

The scheme data MUST contain:

- `smiles`

Example:

```json
{
  "type": "chemical",
  "scheme": {
    "id": "org.opensmell.chemical.smiles",
    "version": "0.1"
  },
  "data": {
    "smiles": "O=C1OC2=CC=CC=C2C=C1"
  }
}
```

`smiles` MUST be a non-empty string.

OpenSmell Core validation verifies only the OpenSmell structure and
the requirements defined by this scheme.

It does not guarantee that the string represents a chemically valid
SMILES structure.

Chemical validity MAY be checked by specialized software.

A SMILES representation describes molecular structure information. It
MUST NOT be interpreted as proof that the molecule alone reproduces
the odor represented by the containing OpenSmell object.

---

## 24. Structural Validity

An OpenSmell document is structurally valid when:

- it is valid UTF-8 JSON;
- it contains the required OpenSmell fields;
- required values have the correct JSON types;
- required arrays and strings are non-empty where specified.

Structural validity does not imply that an implementation understands
every representation.

Structural validity also does not imply scientific validity.

---

## 25. Scheme Validation

Known representation schemes MAY define additional validation rules
for their `data`.

For example:

    org.opensmell.semantic.descriptors

requires a non-empty descriptor array.

An implementation that supports a scheme SHOULD validate its
scheme-specific data.

Failure to satisfy the requirements of a known scheme makes that
representation invalid for that scheme.

An unknown scheme, however, MUST NOT cause an otherwise structurally
valid document to fail solely because the implementation does not
recognize it.

---

## 26. Representation Support

An implementation SHOULD distinguish between at least:

    VALID
    UNSUPPORTED
    INTERPRETABLE
    RENDERABLE

These states describe different properties.

For example:

    Document valid:         YES
    Representation known:  YES
    Scheme supported:      NO
    Renderable:            NO

`VALID` means that the representation satisfies the applicable
structural requirements.

`UNSUPPORTED` means that the implementation does not understand the
representation or scheme sufficiently to interpret it.

`INTERPRETABLE` means that the implementation understands the
representation's scheme.

`RENDERABLE` means that the implementation has a mechanism capable of
using the representation as part of an odor rendering process.

A valid representation is not necessarily interpretable.

An interpretable representation is not necessarily renderable.

---

## 27. Unknown Data

Implementations SHOULD preserve fields and representation data they do
not understand when reading and rewriting OpenSmell documents where
practical.

Unknown representation types or schemes MUST NOT be silently
reinterpreted as known types or schemes.

An unknown scheme MUST NOT be rejected solely because it is unknown.

This behavior is important for forward compatibility and
interoperability between implementations supporting different scheme
sets.

---

## 28. Serialization and Round Trips

An implementation serializing an OpenSmell object SHOULD produce
UTF-8 JSON.

A read/write operation intended to be lossless SHOULD preserve:

- odor identity;
- metadata;
- representations;
- scheme identifiers;
- scheme versions;
- representation data;
- unsupported representation data where practical.

Serialization does not require identical whitespace, indentation, or
JSON object key ordering.

Semantic preservation is more important than textual equality.

---

## 29. Rendering

OpenSmell 0.1 does not define a standardized rendering request
serialization format.

The following concepts therefore do NOT belong to the odor identity:

    intensity
    duration
    start time
    playback schedule
    target device

An implementation API MAY expose such parameters separately.

Conceptually:

    device.render(
        odor,
        intensity=0.75
    )

A future specification or RFC MAY define a standardized rendering
request.

Such a specification MUST preserve the distinction between an odor
representation and an instruction to render that odor.

---

## 30. Devices

OpenSmell 0.1 does not define a mandatory physical device protocol.

Device integrations belong to implementation adapters.

Conceptually:

    OpenSmell Odor
          |
          v
    Representation / Mapper
          |
          v
    Device Adapter
          |
          v
    Manufacturer SDK / Protocol
          |
          v
    Olfactory Device

OpenSmell Core MUST NOT require a specific:

- scent cartridge system;
- pump;
- valve;
- airflow mechanism;
- electrical interface;
- manufacturer protocol.

A future specification or RFC MAY define standardized device
capability or adapter interfaces.

---

## 31. External Identifiers and References

OpenSmell 0.1 does not define a standardized `references` structure.

Implementations MAY associate OpenSmell objects with external
identifiers outside the core document model.

Possible external sources may include:

- chemical databases;
- scientific datasets;
- controlled vocabularies;
- published models;
- future odor registries.

A future OpenSmell RFC may define a standard mechanism for including
such references directly in an OpenSmell document.

External identifiers MUST NOT replace `odor.id` unless a future
specification explicitly defines such behavior.

---

## 32. Security and Safety

OpenSmell files MUST be treated as untrusted input.

Implementations SHOULD:

- enforce reasonable input size limits;
- reject malformed JSON;
- validate required structures;
- avoid executing arbitrary code referenced by representation data;
- avoid automatically loading untrusted plugins based solely on a
  file;
- avoid automatic network access while parsing.

Physical odor rendering introduces additional safety considerations.

An OpenSmell representation MUST NOT be interpreted as evidence that
a substance or mixture is safe to:

- synthesize;
- mix;
- heat;
- aerosolize;
- emit;
- inhale;
- ingest;
- otherwise expose to humans or animals.

Physical safety requirements are outside the scope of OpenSmell 0.1.

---

## 33. Canonical Example

The following example represents coumarin using both chemical and
semantic representations:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
    "metadata": {
      "labels": {
        "en": "Coumarin",
        "fr": "Coumarine"
      },
      "description": "Example odor with chemical and semantic representations."
    },
    "representations": [
      {
        "type": "chemical",
        "scheme": {
          "id": "org.opensmell.chemical.smiles",
          "version": "0.1"
        },
        "data": {
          "smiles": "O=C1OC2=CC=CC=C2C=C1"
        }
      },
      {
        "type": "semantic",
        "scheme": {
          "id": "org.opensmell.semantic.descriptors",
          "version": "0.1"
        },
        "data": {
          "descriptors": [
            {
              "value": "sweet",
              "language": "en"
            },
            {
              "value": "vanilla-like",
              "language": "en"
            }
          ]
        }
      }
    ]
  }
}
```

This example demonstrates that multiple representations may coexist
inside the same OpenSmell odor object.

The chemical representation and semantic representation provide
different information about the object.

OpenSmell does not assert that either representation can automatically
be derived from the other.

---

## 34. Conformance

An implementation claiming OpenSmell 0.1 parsing support MUST:

1. parse UTF-8 JSON OpenSmell documents;

2. validate the required top-level structure;

3. validate odor identity and representation structure;

4. support multiple representations;

5. preserve the distinction between unsupported and invalid
   representations;

6. not reject an otherwise valid representation solely because its
   scheme is unknown;

7. not require network access to parse an OpenSmell document;

8. preserve unknown representation data during a lossless read/write
   operation where practical.

An implementation does NOT need to support every representation scheme
to claim OpenSmell 0.1 Core parsing support.

Support for physical scent devices is NOT required for OpenSmell 0.1
conformance.

---

## 35. Experimental Status

OpenSmell 0.1 is experimental.

Breaking changes are expected before a stable 1.0 specification.

Version 0.1 exists to validate the architecture through:

- reference implementations;
- automated tests;
- example documents;
- interoperability experiments;
- scientific model integrations;
- future device adapters.

Features SHOULD NOT be added to the OpenSmell Core solely because they
may be useful in the future.

New concepts should first demonstrate a concrete interoperability need.

The objective of OpenSmell 0.1 is to establish a small and robust
foundation on which future digital olfaction interoperability can be
built.
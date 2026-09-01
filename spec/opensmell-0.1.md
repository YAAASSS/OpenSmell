# OpenSmell 0.1 Specification

- **Status:** Experimental
- **Version:** 0.1
- **Date:** September 2026
- **Related:** RFC-0001, RFC-0002

## 1. Introduction

OpenSmell is an open interoperability framework for digital olfaction.

This document defines the experimental OpenSmell 0.1 serialization format.

The purpose of version 0.1 is not to provide a complete digital olfaction
standard.

Its purpose is to establish a minimal, extensible, machine-readable container
for digital odor representations that can be implemented and tested.

---

## 2. Design Principles

OpenSmell 0.1 follows these principles:

1. Odor identity is separate from odor representation.
2. An odor may contain multiple representations.
3. Representation schemes are independently defined and versioned.
4. OpenSmell does not define a universal scientific model of smell.
5. OpenSmell data is independent from rendering hardware.
6. Rendering instructions are not part of odor identity.
7. Unknown representation schemes do not invalidate an otherwise valid
   OpenSmell document.
8. Version 0.1 should remain deliberately small.

---

## 3. File Format

An OpenSmell 0.1 document MUST be encoded as UTF-8 JSON.

The recommended file extension is:

    .osmell

Example:

    coffee.osmell

An OpenSmell implementation MUST parse the file as JSON before attempting
OpenSmell-specific validation.

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

Example:

```json
{
  "opensmell": "0.1"
}
```

For this specification, its value MUST be:

    0.1

Implementations SHOULD reject unsupported major specification versions.

Handling of future minor versions will be defined when a compatibility model
is required.

---

## 6. `odor`

The `odor` object represents one conceptual odor object.

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
    "representations": []
  }
}
```

---

## 7. Odor Identifier

`odor.id` MUST be a non-empty string.

Version 0.1 RECOMMENDS the use of a UUID URN.

Example:

```json
"id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000"
```

The identifier identifies the OpenSmell odor object.

It MUST NOT be interpreted as proof that two physical odor samples are
chemically or perceptually identical.

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
representation semantics.

---

## 9. Labels

`metadata.labels` MUST be an object when present.

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

---

## 10. Representations

`odor.representations` MUST be a non-empty array.

Each entry represents one digital representation associated with the odor.

Example:

```json
{
  "representations": [
    {
      "type": "semantic",
      "scheme": {
        "id": "org.example.semantic",
        "version": "1.0"
      },
      "data": {}
    }
  ]
}
```

An odor MAY contain multiple representations.

The presence of multiple representations asserts that the producer associates
them with the same OpenSmell odor object.

OpenSmell does not verify their chemical or perceptual equivalence.

---

## 11. Representation Structure

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

---

## 12. Representation Type

`type` MUST be a non-empty string.

OpenSmell 0.1 defines three standard representation type names:

    semantic
    perceptual
    mixture

Implementations MUST NOT assume that these are the only representation types
that may ever exist.

Unknown representation types MUST NOT make an otherwise structurally valid
OpenSmell document invalid.

An implementation MAY report such a representation as unsupported.

---

## 13. Scheme

Every representation MUST contain a `scheme` object.

The scheme MUST contain:

- `id`
- `version`

Example:

```json
{
  "scheme": {
    "id": "org.example.perceptual",
    "version": "1.0"
  }
}
```

Both values MUST be non-empty strings.

The scheme defines how the representation's `data` object should be
interpreted.

---

## 14. Scheme Identifier

`scheme.id` identifies the interpretation scheme.

Example:

    org.example.perceptual

OpenSmell 0.1 does not require scheme identifiers to be URLs.

Resolving a scheme identifier over a network MUST NOT be required to parse an
OpenSmell document.

OpenSmell 0.1 does not yet define a global scheme registry.

---

## 15. Scheme Version

`scheme.version` identifies the version of the representation scheme.

Example:

    1.0

Scheme versions are independent from the OpenSmell specification version.

For example, the following is valid conceptually:

    OpenSmell specification: 0.1
    Scheme version: 4.2

---

## 16. Representation Data

`data` MUST be a JSON object.

Its internal structure is determined by the representation scheme.

OpenSmell Core MUST NOT attempt to infer unknown scheme semantics solely from
the contents of `data`.

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

is meaningful only when interpreted according to its associated scheme.

---

## 17. Semantic Representation

The `semantic` representation family describes an odor using semantic
information.

A scheme may define controlled vocabulary terms.

Example:

```json
{
  "type": "semantic",

  "scheme": {
    "id": "org.example.odor-taxonomy",
    "version": "1.0"
  },

  "data": {
    "terms": [
      "coffee",
      "roasted"
    ]
  }
}
```

A semantic representation MAY also contain free descriptors if allowed by
its scheme.

Example:

```json
{
  "descriptors": [
    {
      "value": "nutty",
      "language": "en"
    }
  ]
}
```

OpenSmell itself does not assign universal meanings to these terms.

---

## 18. Perceptual Representation

The `perceptual` representation family describes an odor according to a
perceptual or computational representation scheme.

Example:

```json
{
  "type": "perceptual",

  "scheme": {
    "id": "org.example.odor-space",
    "version": "2.0"
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

OpenSmell does not define:

- vector dimensionality;
- dimension meaning;
- normalization;
- distance metrics;
- prediction methodology.

Those properties belong to the referenced scheme.

---

## 19. Mixture Representation

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

OpenSmell 0.1 does not define the physical meaning or units of `amount`.

Those semantics MUST be defined by the referenced scheme.

---

## 20. Structural Validity

An OpenSmell document is structurally valid when:

- it is valid UTF-8 JSON;
- it contains the required OpenSmell fields;
- required values have the correct JSON types;
- required arrays and strings are non-empty where specified.

Structural validity does not imply that an implementation understands every
representation.

---

## 21. Representation Support

An implementation SHOULD distinguish between at least:

    VALID
    UNSUPPORTED
    INTERPRETABLE
    RENDERABLE

For example:

    Document valid:        YES
    Representation known:  YES
    Scheme supported:      NO
    Renderable:            NO

A representation using an unknown scheme remains part of the OpenSmell
document.

---

## 22. Unknown Data

Implementations SHOULD preserve fields they do not understand when reading
and rewriting OpenSmell documents where practical.

This improves forward compatibility.

Unknown representation types or schemes MUST NOT be silently reinterpreted
as known schemes.

---

## 23. Rendering

OpenSmell 0.1 does not define a rendering request serialization format.

The following concepts therefore do NOT belong to the odor representation:

    intensity
    duration
    start time
    target device

An implementation API may expose such parameters separately.

Conceptually:

    device.render(
        odor,
        intensity = 0.75
    )

A future specification may define a standardized rendering request.

---

## 24. Devices

OpenSmell 0.1 does not define a mandatory physical device protocol.

Device integrations belong to implementation adapters.

Conceptually:

    OpenSmell Odor
          |
          v
    Device Adapter
          |
          v
    Manufacturer SDK / Protocol
          |
          v
    Olfactory Device

A future RFC may define a standard capability interface for device adapters.

---

## 25. Security

OpenSmell files MUST be treated as untrusted input.

Implementations SHOULD:

- enforce reasonable input size limits;
- reject malformed JSON;
- validate required structures;
- avoid executing arbitrary code referenced by representation data;
- avoid automatically loading untrusted plugins based solely on a file;
- avoid automatic network access while parsing.

Physical rendering introduces additional safety concerns that are outside the
scope of OpenSmell 0.1.

---

## 26. Canonical Example

A minimal OpenSmell 0.1 document:

```json
{
  "opensmell": "0.1",

  "odor": {
    "id": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",

    "metadata": {
      "labels": {
        "en": "Coffee",
        "fr": "Café"
      },
      "description": "OpenSmell example coffee odor."
    },

    "representations": [
      {
        "type": "semantic",

        "scheme": {
          "id": "org.opensmell.semantic.free",
          "version": "0.1"
        },

        "data": {
          "descriptors": [
            {
              "value": "coffee",
              "language": "en"
            },
            {
              "value": "roasted",
              "language": "en"
            },
            {
              "value": "nutty",
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

## 27. Conformance

An implementation claiming OpenSmell 0.1 parsing support MUST:

1. parse UTF-8 JSON OpenSmell documents;
2. validate the required top-level structure;
3. validate odor identity and representations;
4. preserve the distinction between unsupported and invalid representations;
5. not require network access to parse a document.

Support for physical scent devices is NOT required for OpenSmell 0.1
conformance.

---

## 28. Experimental Status

OpenSmell 0.1 is experimental.

Breaking changes are expected before a stable 1.0 specification.

The purpose of this version is to validate the architecture through real
implementations and interoperability experiments.

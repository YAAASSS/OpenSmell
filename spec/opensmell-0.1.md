# OpenSmell 0.1 Specification

- **Status:** Experimental
- **Version:** 0.1
- **Date:** September 2026

---

## 1. Introduction

OpenSmell is an open interoperability framework for digital olfaction.

This document defines the experimental OpenSmell 0.1 serialization format.

The purpose of version 0.1 is not to provide a complete digital olfaction
standard.

Its purpose is to establish a minimal, extensible, machine-readable container
for digital odor representations that can be implemented, exchanged,
validated, and tested across applications.

OpenSmell does not define a universal scientific model of smell and does not
require any particular physical odor reproduction technology.

---

## 2. Design Principles

OpenSmell 0.1 follows these principles:

1. Odor identity is separate from odor representation.
2. An odor may contain multiple representations.
3. Representation schemes are independently defined and versioned.
4. OpenSmell does not define a universal scientific model of smell.
5. OpenSmell data is independent from rendering hardware.
6. Rendering instructions are not part of odor identity.
7. Unknown representation types and schemes do not invalidate an otherwise
   structurally valid OpenSmell document.
8. Implementations should preserve information they do not understand where
   practical.
9. OpenSmell should reuse existing scientific representations and identifiers
   when appropriate rather than redefining them.
10. Version 0.1 should remain deliberately small.

---

## 3. File Format

An OpenSmell 0.1 document MUST be encoded as UTF-8 JSON.

The recommended file extension is:

```text
.osmell
```

Example:

```text
coffee.osmell
```

An OpenSmell implementation MUST parse the file as JSON before attempting
OpenSmell-specific validation.

The `.osmell` extension identifies an OpenSmell document but does not change
the underlying JSON encoding.

---

## 4. Top-Level Structure

An OpenSmell 0.1 document MUST contain:

- `opensmell`
- `odor`

Example:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "example-odor",
    "representations": [
      {
        "type": "semantic",
        "scheme": {
          "id": "org.opensmell.semantic.descriptors",
          "version": "0.1"
        },
        "data": {
          "descriptors": [
            "coffee"
          ]
        }
      }
    ]
  }
}
```

Additional top-level properties MAY be present.

Implementations SHOULD preserve unknown top-level properties when performing
a document-preserving round trip where practical.

---

## 5. OpenSmell Version

The `opensmell` property identifies the OpenSmell serialization version.

For this specification, its value MUST be:

```json
"0.1"
```

Example:

```json
{
  "opensmell": "0.1"
}
```

The OpenSmell version is independent from representation scheme versions.

---

## 6. Odor Object

The `odor` property MUST contain a JSON object.

An odor object MUST contain:

- `id`
- `representations`

It MAY contain:

- `metadata`
- additional properties

Example:

```json
{
  "id": "coffee-example",
  "metadata": {
    "labels": {
      "en": "Coffee"
    }
  },
  "representations": [
    {
      "type": "semantic",
      "scheme": {
        "id": "org.opensmell.semantic.descriptors",
        "version": "0.1"
      },
      "data": {
        "descriptors": [
          "coffee",
          "roasted"
        ]
      }
    }
  ]
}
```

---

## 7. Odor Identity

The `odor.id` property identifies the odor resource within the context in
which the document is used.

It MUST be a non-empty string.

Example:

```json
{
  "id": "coffee-example"
}
```

OpenSmell 0.1 deliberately does not prescribe the internal syntax or
generation method of this identifier.

Applications MAY therefore use identifiers appropriate to their environment,
provided they are represented as non-empty strings.

OpenSmell 0.1 does not define whether two different identifiers represent
scientifically or perceptually equivalent odors.

Future specifications or RFCs may define more specific resource
identification mechanisms.

---

## 8. Metadata

The optional `metadata` property contains human-oriented descriptive
information about the odor.

It MUST be a JSON object when present.

OpenSmell 0.1 currently defines:

- `labels`
- `description`

Additional metadata properties MAY be present.

Metadata does not define the scientific or rendering semantics of an odor.

---

## 9. Labels

`metadata.labels` MAY contain human-readable labels.

When present, it MUST be a non-empty JSON object.

Each property value MUST be a non-empty string.

Example:

```json
{
  "labels": {
    "en": "Coffee",
    "fr": "Café"
  }
}
```

OpenSmell 0.1 does not require a specific language-tag standard for label
keys.

Applications SHOULD use stable and clearly documented language identifiers.

Labels are descriptive metadata and MUST NOT be used as the sole
machine-readable definition of an odor.

---

## 10. Description

`metadata.description` MAY contain a human-readable description.

When present, it MUST be a non-empty string.

Example:

```json
{
  "description": "Example coffee odor used for interoperability testing."
}
```

The description is informational.

Implementations MUST NOT infer representation semantics solely from this
field.

---

## 11. Representations

`odor.representations` MUST be a non-empty JSON array.

Each item MUST be a representation object.

An odor MAY contain multiple representations.

Example:

```json
{
  "representations": [
    {
      "type": "semantic",
      "scheme": {
        "id": "org.opensmell.semantic.descriptors",
        "version": "0.1"
      },
      "data": {
        "descriptors": [
          "coffee"
        ]
      }
    },
    {
      "type": "chemical",
      "scheme": {
        "id": "org.opensmell.chemical.smiles",
        "version": "0.1"
      },
      "data": {
        "smiles": "CCO"
      }
    }
  ]
}
```

Multiple representations do not necessarily imply that all representations
contain equivalent information.

They provide different views or encodings associated with the same odor
resource.

---

## 12. Representation Object

Each representation MUST contain:

- `type`
- `scheme`
- `data`

Additional properties MAY be present.

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
      "coffee"
    ]
  }
}
```

---

## 13. Representation Type

`representation.type` identifies the broad representation family.

It MUST be a non-empty string.

Examples include:

```text
semantic
perceptual
chemical
mixture
```

These names describe broad categories.

The exact interpretation of representation data is determined by the
associated scheme.

OpenSmell 0.1 does not restrict representation types to a closed
enumeration.

An unknown representation type therefore does not by itself make an
otherwise structurally valid document invalid.

---

## 14. Scheme Object

Every representation MUST contain a `scheme` object.

The scheme object MUST contain:

- `id`
- `version`

Both values MUST be non-empty strings.

Example:

```json
{
  "scheme": {
    "id": "org.opensmell.semantic.descriptors",
    "version": "0.1"
  }
}
```

The scheme defines how the representation's `data` object should be
interpreted.

Additional scheme properties MAY be present.

---

## 15. Scheme Identifier

`scheme.id` identifies the interpretation scheme.

It MUST be a non-empty string.

Example:

```text
org.opensmell.semantic.descriptors
```

OpenSmell 0.1 does not require scheme identifiers to be URLs.

Resolving a scheme identifier over a network MUST NOT be required to parse an
OpenSmell document.

OpenSmell 0.1 does not define a global mandatory scheme registry.

An implementation MAY provide a local registry of schemes it understands.

---

## 16. Scheme Version

`scheme.version` identifies the version of the representation scheme.

It MUST be a non-empty string.

Example:

```text
0.1
```

Scheme versions are independent from the OpenSmell serialization version.

For example:

```text
OpenSmell version: 0.1
Scheme version:    2.0
```

is conceptually valid if the implementation understands that scheme version.

---

## 17. Representation Data

`representation.data` MUST be a JSON object.

Its internal structure is determined by the representation scheme.

Example:

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

OpenSmell Core MUST NOT attempt to infer unknown scheme semantics solely from
the contents of `data`.

An empty data object is structurally permitted by the OpenSmell 0.1 core
schema, although a known representation scheme MAY impose additional
requirements.

---

## 18. Semantic Representation Family

The `semantic` representation family describes an odor using semantic
information.

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
      "coffee",
      "roasted",
      "nutty"
    ]
  }
}
```

OpenSmell Core does not assign universal scientific meanings to semantic
terms.

The associated scheme defines their interpretation.

A future or experimental scheme MAY define richer semantic annotation
structures without changing the OpenSmell 0.1 core container.

---

## 19. Perceptual Representation Family

The `perceptual` representation family may describe an odor using perceptual
measurements, descriptors, vectors, model outputs, or other
scheme-defined perceptual information.

Conceptual example:

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

OpenSmell Core does not define:

- vector dimensionality
- dimension meaning
- normalization
- distance metrics
- measurement scales
- prediction methodology

Those semantics belong to the referenced scheme.

---

## 20. Chemical Representation Family

The `chemical` representation family may describe chemical information
associated with an odor.

Example:

```json
{
  "type": "chemical",
  "scheme": {
    "id": "org.opensmell.chemical.smiles",
    "version": "0.1"
  },
  "data": {
    "smiles": "CCO"
  }
}
```

A chemical representation is not automatically equivalent to a perceptual
odor description.

OpenSmell does not assume that chemical identity alone fully determines human
odor perception.

The associated scheme defines the syntax and semantics of its chemical data.

---

## 21. Mixture Representation Family

The `mixture` representation family may describe an odor using components
defined by a mixture scheme.

Conceptual example:

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

OpenSmell 0.1 does not define the physical meaning or units of `amount` in
this conceptual example.

Those semantics MUST be defined by the referenced scheme.

A mixture representation MUST NOT be assumed to correspond directly to a
particular physical diffuser or cartridge system unless its scheme explicitly
defines such semantics.

---

## 22. Structural Validity

An OpenSmell document is structurally valid under version 0.1 when:

- it is valid UTF-8 JSON;
- `opensmell` exists and equals `"0.1"`;
- `odor` exists and is an object;
- `odor.id` is a non-empty string;
- `odor.representations` is a non-empty array;
- each representation contains valid `type`, `scheme`, and `data` fields;
- required strings and objects satisfy the OpenSmell 0.1 structural schema.

Structural validity does not imply that an implementation understands every
representation.

Structural validation and scheme-specific semantic validation are separate
operations.

---

## 23. Scheme-Specific Validation

An implementation MAY perform additional validation for schemes it
understands.

For example, a known semantic scheme may require a particular property
inside `data`.

A known chemical scheme may require another structure.

Failure to satisfy the rules of a known scheme may make that representation
invalid according to the implementation's scheme validator.

Unknown schemes MUST NOT be rejected merely because no scheme-specific
validator is available.

---

## 24. Representation Support

Applications SHOULD distinguish structural validity from implementation
capabilities.

Useful conceptual states include:

```text
VALID
SUPPORTED
INTERPRETABLE
RENDERABLE
```

For example:

```text
Document valid:        YES
Representation known:  YES
Scheme supported:      NO
Renderable:            NO
```

A representation using an unknown scheme remains part of the OpenSmell
document.

An implementation MUST NOT silently reinterpret an unknown scheme as a known
scheme.

---

## 25. Unknown Data and Forward Compatibility

OpenSmell 0.1 deliberately allows additional properties at several structural
levels.

Additional properties MAY appear at:

- document level;
- odor level;
- metadata level;
- representation level;
- scheme level.

Implementations SHOULD preserve fields they do not understand when reading
and rewriting OpenSmell documents where practical.

This behavior improves forward compatibility.

Unknown properties MUST NOT silently override the meaning of standardized
properties.

Unknown representation types or schemes MUST NOT be silently reinterpreted
as known ones.

An implementation that exposes an API which discards a containing structure
MAY be unable to preserve extensions belonging to that discarded structure.

Applications requiring lossless document-level round trips SHOULD retain the
complete document structure.

---

## 26. Rendering

OpenSmell 0.1 does not define a rendering request serialization format.

The following concepts therefore do NOT belong to odor identity merely by
virtue of using OpenSmell 0.1:

```text
intensity
duration
start time
target device
```

An implementation API may expose rendering parameters separately.

Conceptually:

```text
device.render(
    odor,
    intensity = 0.75
)
```

A future specification may define standardized rendering requests.

Such a specification should remain distinct from the core identity and
representation of an odor.

---

## 27. Devices

OpenSmell 0.1 does not define a mandatory physical device protocol.

Device integrations belong outside the core serialization model.

Conceptually:

```text
OpenSmell representation
          |
          v
     Mapper / Adapter
          |
          v
Manufacturer SDK / Protocol
          |
          v
    Olfactory Device
```

OpenSmell MUST NOT assume how an odor is physically reproduced.

A future RFC may define standardized capability or device-adapter
interfaces.

---

## 28. Parsing and Network Independence

Parsing an OpenSmell 0.1 document MUST NOT require network access.

In particular, an implementation MUST NOT require network resolution of:

- scheme identifiers;
- odor identifiers;
- unknown extension identifiers.

Applications MAY voluntarily use external services after parsing, but such
network behavior is outside core OpenSmell 0.1 parsing requirements.

This requirement supports:

- offline operation;
- reproducibility;
- security;
- long-term preservation.

---

## 29. Security

OpenSmell documents MUST be treated as untrusted input.

Implementations SHOULD:

- reject malformed JSON;
- validate required structures;
- apply reasonable resource limits when appropriate;
- avoid executing arbitrary code referenced by representation data;
- avoid automatically loading untrusted plugins based solely on document
  contents;
- avoid automatic network access while parsing.

Scheme-specific data may introduce additional security considerations.

Physical odor rendering introduces additional safety concerns outside the
scope of OpenSmell 0.1.

A structurally valid OpenSmell document MUST NOT automatically be considered
safe to physically render.

---

## 30. Extensibility

OpenSmell 0.1 is designed as an extensible container.

New representation schemes SHOULD generally be introduced without changing
the OpenSmell core schema when the existing representation structure is
sufficient.

For example:

```text
OpenSmell core
    |
    +-- semantic scheme A
    +-- semantic scheme B
    +-- perceptual scheme A
    +-- chemical scheme A
    +-- mixture scheme A
```

This allows independent scientific models and device ecosystems to coexist
without requiring OpenSmell Core to define their internal semantics.

Future OpenSmell versions may introduce new core resource structures when
extensions alone are insufficient.

---

## 31. Relationship Between Core and Schemes

OpenSmell 0.1 defines the container.

Representation schemes define interpretation.

Conceptually:

```text
OpenSmell Core
    |
    +-- identity
    +-- metadata
    +-- representation container
            |
            +-- type
            +-- scheme
            +-- data
```

The core answers:

```text
What representation is present?
Which scheme defines it?
Where is its data?
```

The scheme answers:

```text
What does this data mean?
How is it validated?
How may it be interpreted?
```

This separation is fundamental to OpenSmell's interoperability model.

---

## 32. Canonical Example

A complete OpenSmell 0.1 example:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "coffee-example",
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
          "id": "org.opensmell.semantic.descriptors",
          "version": "0.1"
        },
        "data": {
          "descriptors": [
            "coffee",
            "roasted",
            "nutty"
          ]
        }
      }
    ]
  }
}
```

The document contains:

```text
OpenSmell version
        ↓
      Odor
        ↓
  Representation
        ↓
      Scheme
        ↓
       Data
```

No physical rendering technology is implied by this example.

---

## 33. Minimal Valid Example

A minimal structurally valid OpenSmell 0.1 document is:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "example",
    "representations": [
      {
        "type": "example",
        "scheme": {
          "id": "org.example.scheme",
          "version": "1"
        },
        "data": {}
      }
    ]
  }
}
```

The representation scheme does not need to be known to OpenSmell Core for
the document to remain structurally valid.

---

## 34. Invalid Examples

The following document is invalid because `odor.id` is missing:

```json
{
  "opensmell": "0.1",
  "odor": {
    "representations": [
      {
        "type": "semantic",
        "scheme": {
          "id": "org.example.scheme",
          "version": "1"
        },
        "data": {}
      }
    ]
  }
}
```

The following document is invalid because `representations` is empty:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "example",
    "representations": []
  }
}
```

The following document is invalid because `scheme.version` is empty:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "example",
    "representations": [
      {
        "type": "semantic",
        "scheme": {
          "id": "org.example.scheme",
          "version": ""
        },
        "data": {}
      }
    ]
  }
}
```

---

## 35. Conformance

An implementation claiming OpenSmell 0.1 parsing support MUST:

1. parse UTF-8 JSON OpenSmell documents;
2. validate the required top-level structure;
3. require `opensmell` to equal `"0.1"`;
4. validate odor identity and representation structure;
5. preserve the distinction between unsupported and structurally invalid
   representations;
6. not require network access to parse a document.

Support for any particular representation scheme is NOT required for basic
OpenSmell 0.1 structural parsing conformance.

Support for physical scent devices is NOT required for OpenSmell 0.1
conformance.

An implementation claiming support for a specific representation scheme
SHOULD additionally apply that scheme's validation rules.

---

## 36. JSON Schema

The machine-readable schema for this specification is:

```text
schema/opensmell-0.1.schema.json
```

The Python package also includes a packaged copy of the schema for runtime
validation.

The packaged schema and repository schema SHOULD remain identical.

The schema uses JSON Schema Draft 2020-12.

Its identifier is:

```text
https://opensmell.org/schema/opensmell-0.1.schema.json
```

The schema identifier identifies the schema namespace.

Parsing an OpenSmell document MUST NOT require fetching that URL.

---

## 37. Experimental Status

OpenSmell 0.1 is experimental.

The following areas remain intentionally open for future work:

- richer semantic annotation models;
- quantitative perceptual measurement models;
- provenance;
- resource identification;
- stimulus and observation models;
- biological measurement models;
- mixture and renderable representations;
- mapper interfaces;
- device capabilities;
- rendering requests;
- timing and synchronization;
- cross-dataset identity;
- additional interoperability profiles.

Experimental RFCs may investigate these areas without changing normative
OpenSmell 0.1 behavior.

An experimental RFC does not automatically become part of OpenSmell 0.1.

---

## 38. Compatibility Philosophy

Future OpenSmell development SHOULD prefer additive evolution where
practical.

Version 0.1 intentionally permits unknown properties and unknown schemes so
that experimental extensions can be carried without requiring the core to
understand them.

Applications SHOULD therefore avoid unnecessarily rejecting information
solely because it was introduced after their implementation was written.

At the same time, implementations MUST NOT claim semantic understanding of
data whose scheme they do not support.

Forward compatibility means preserving unknown information, not guessing its
meaning.

---

## 39. Non-Goals of OpenSmell 0.1

OpenSmell 0.1 does not attempt to:

- define a universal odor ontology;
- define a universal perceptual odor space;
- define chemical-to-perceptual prediction;
- define a universal set of odor primaries;
- guarantee that an odor can be physically reproduced;
- define a diffuser protocol;
- define device timing;
- define exposure safety;
- define biological response models;
- define scientific equivalence between representations;
- replace existing chemical or scientific identifier systems.

These concerns may be addressed by representation schemes, adapters,
scientific models, future RFCs, or future OpenSmell versions.

---

## 40. Summary

OpenSmell 0.1 defines a small extensible JSON container for digital olfactory
information.

A document contains:

```text
OpenSmell version
        |
        v
       Odor
        |
        +-- identity
        +-- optional metadata
        |
        +-- one or more representations
                    |
                    +-- type
                    +-- scheme
                    +-- data
```

The core deliberately does not prescribe how every odor must be represented.

Instead, independently versioned schemes define representation semantics.

Unknown schemes remain structurally preservable.

Rendering and physical devices remain outside the OpenSmell 0.1 odor model.

This provides the foundation on which richer digital olfaction
interoperability can evolve without coupling the core format to one
scientific model or one hardware ecosystem.
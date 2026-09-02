# OpenSmell

**An open interoperability framework for digital olfaction.**

OpenSmell is an experimental open-source project for representing, exchanging, and eventually rendering digital olfactory information across applications and devices.

The goal is not to define how smell must physically be reproduced. Instead, OpenSmell aims to provide a common interoperability layer between odor data, software applications, scientific models, and heterogeneous olfactory rendering technologies.

> [!IMPORTANT]
> OpenSmell is currently an early-stage experimental project.
> Version `0.1` is under active development and should not be considered a stable standard.

---

## Why OpenSmell?

Digital olfaction is an emerging field involving technologies such as:

- electronic noses and chemical sensors;
- machine-learning models for odor perception;
- digital odor databases;
- scent displays and olfactory interfaces;
- VR/AR olfactory experiences;
- remote odor reproduction;
- odor digitization research.

Several projects and standards already address parts of this ecosystem.

However, these systems may represent odors differently and may rely on different hardware, models, vocabularies, or delivery technologies.

OpenSmell explores a simple question:

> **Can digital odor information be represented and exchanged independently from the technology that eventually interprets or renders it?**

The project aims to investigate this interoperability layer.

---

## Design philosophy

The core principle of OpenSmell is:

> **OpenSmell must not assume how an odor is physically reproduced.**

A future olfactory display might use:

- a small number of odor primaries;
- hundreds of chemical cartridges;
- predefined scent cartridges;
- dynamically generated mixtures;
- technologies that do not exist yet.

OpenSmell should therefore describe olfactory information without forcing every device to use the same physical reproduction mechanism.

Conceptually:

```text
Scientific data / Models / Sensors
               │
               ▼
      Digital odor information
               │
               ▼
          ┌───────────┐
          │ OpenSmell │
          └───────────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
 Application  Mapper   Storage
               │
               ▼
        Device adapter
               │
               ▼
       Olfactory device
```

OpenSmell focuses primarily on the interoperability layer, not on the physical diffuser itself.

---

## Representation model

An OpenSmell odor may contain multiple representations of the same conceptual odor.

For example:

```text
                    Coffee
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Semantic     Perceptual    Renderable
   representation representation representation
```

This allows different applications to use the representation they understand.

Potential representation categories include:

### Semantic

Human-readable descriptions of an odor.

Examples:

```text
coffee
roasted
bitter
woody
floral
```

### Perceptual

A representation of how an odor is perceived.

For example, a future model could describe an odor using a multidimensional perceptual vector.

### Chemical

Information derived from molecular or analytical measurements.

### Renderable

Information intended to help compatible systems reproduce or approximate an odor.

For example, a future system might describe a mixture of odor primaries.

These categories do **not** require OpenSmell itself to solve odor digitization.

OpenSmell provides a container and interoperability mechanism for representations produced by external systems.

---

## Representation schemes

Every representation identifies a **scheme**.

A scheme defines how the representation's `data` field should be interpreted.

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
        "value": "coffee",
        "language": "en"
      },
      {
        "value": "roasted",
        "language": "en"
      }
    ]
  }
}
```

Here:

```text
type
```

describes the broad category of information.

```text
scheme
```

defines the specific rules used to interpret that information.

This distinction allows OpenSmell to support representations created by different scientific models, organizations, or technologies.

---

## Built-in schemes

### `org.opensmell.semantic.descriptors`

Version:

```text
0.1
```

This is currently the first built-in OpenSmell representation scheme.

It represents an odor using human-readable semantic descriptors.

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
        "value": "coffee",
        "language": "en"
      },
      {
        "value": "roasted",
        "language": "en"
      },
      {
        "value": "bitter",
        "language": "en"
      }
    ]
  }
}
```

This representation describes an odor.

It does **not** specify how a physical device should reproduce it.

---

## Extensibility

OpenSmell is designed so that unknown representation schemes can still be transported and preserved.

For example, imagine a future representation:

```json
{
  "type": "perceptual",
  "scheme": {
    "id": "org.example.future-model",
    "version": "3.2"
  },
  "data": {
    "vector": [
      0.18,
      0.72,
      0.41
    ]
  }
}
```

An older OpenSmell implementation may not understand this scheme.

That should not automatically make the entire OpenSmell document invalid.

The intended behavior is:

```text
Known scheme + valid data
        │
        ▼
      ACCEPT

Known scheme + invalid data
        │
        ▼
      REJECT

Unknown scheme
        │
        ▼
      ACCEPT
        │
        ▼
Preserve opaque data
```

This is an important part of OpenSmell's forward-compatibility strategy.

---

## `.osmell` documents

OpenSmell uses JSON for the initial `0.1` format.

A simplified document looks like:

```json
{
  "opensmell": "0.1",
  "odor": {
    "id": "coffee",
    "metadata": {
      "labels": {
        "en": "Coffee",
        "fr": "Café"
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

The `.osmell` extension is used for OpenSmell documents.

---

## Python reference implementation

The repository contains an early Python reference implementation.

Supported Python versions:

```text
Python 3.10+
```

The package currently provides:

- `.osmell` document loading;
- JSON Schema validation;
- Python data models;
- representation scheme validation;
- a scheme registry;
- preservation of unknown schemes.

---

## Installation for development

Clone the repository:

```bash
git clone https://github.com/YAAASSS/OpenSmell.git
cd OpenSmell
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install OpenSmell with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

---

## Usage

Load an OpenSmell document:

```python
import opensmell

odor = opensmell.load("examples/coffee.osmell")

print(odor.id)
```

Access its metadata:

```python
print(odor.metadata.labels["en"])
```

Output:

```text
Coffee
```

Access its representations:

```python
representation = odor.representations[0]

print(representation.type)
print(representation.scheme.id)
print(representation.scheme.version)
```

Example output:

```text
semantic
org.opensmell.semantic.descriptors
0.1
```

Access representation-specific data:

```python
print(representation.data["descriptors"])
```

---

## Validation

OpenSmell currently performs two levels of validation.

### Core validation

The complete document is validated against the OpenSmell JSON Schema.

This checks the structural validity of the `.osmell` document.

### Scheme validation

If OpenSmell recognizes a representation scheme, its `data` field is validated using the corresponding scheme validator.

Conceptually:

```text
.osmell
   │
   ▼
JSON Schema validation
   │
   ▼
Representation schemes
   │
   ├── known ──────► validate data
   │
   └── unknown ────► preserve data
   │
   ▼
Python objects
```

---

## Scheme Registry

The Python implementation contains a Scheme Registry.

It maps:

```text
scheme ID + version
```

to:

```text
validator
```

For example:

```text
org.opensmell.semantic.descriptors
                 +
                0.1
                 │
                 ▼
          Scheme Registry
                 │
                 ▼
 semantic descriptor validator
```

This avoids hard-coding every representation type into the core parser and allows the architecture to evolve as new representations are introduced.

---

## Running tests

Install the development dependencies and run:

```bash
pytest
```

The test suite currently verifies core parsing and validation behavior, including representation scheme handling.

GitHub Actions automatically runs the test suite on:

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

---

## Project structure

```text
OpenSmell/
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── examples/
│   ├── coffee.osmell
│   └── invalid.osmell
│
├── rfcs/
│
├── schema/
│   └── opensmell-0.1.schema.json
│
├── spec/
│
├── src/
│   └── opensmell/
│       ├── schemas/
│       │   └── opensmell-0.1.schema.json
│       │
│       ├── schemes/
│       │   ├── __init__.py
│       │   ├── registry.py
│       │   └── semantic_descriptors.py
│       │
│       ├── __init__.py
│       ├── exceptions.py
│       ├── models.py
│       ├── parser.py
│       └── validation.py
│
├── tests/
│   └── test_parser.py
│
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## Relationship with existing work

OpenSmell does not assume that digital olfaction begins with this project.

Existing research, standards, datasets, models, and olfactory interfaces already address important parts of the problem.

Relevant work includes:

### MPEG-V / ISO/IEC 23005

MPEG-V defines representations and control mechanisms for sensory effects, including olfactory effects.

OpenSmell should investigate interoperability with MPEG-V rather than duplicate existing standardization work.

### OWidgets

OWidgets explored device-independent olfactory experience design and communication with scent-delivery devices.

Its work on mapping, scheduling, and uniform device interfaces is relevant prior art for OpenSmell.

### OpenPOM

OpenPOM provides open-source machine-learning tools related to perceptual odor mapping.

Future OpenSmell representations could potentially transport outputs from models of this kind.

### OdorNet

OdorNet provides standardized molecular olfactory labels and datasets.

Such datasets are potential sources of olfactory information rather than physical scent-rendering instructions.

### D2Smell

D2Smell is ongoing research into the digitization and remote reproduction of smell.

Future results from projects such as D2Smell may help define useful perceptual or renderable representations.

### Scentree

Scentree is an open-source olfactory display project and represents the type of hardware that could eventually be explored through an OpenSmell device adapter.

OpenSmell's objective is therefore **interoperability**, not claiming invention of digital smell transmission.

---

## Potential architecture

The long-term architecture may evolve toward:

```text
Odor datasets
     │
     ├── OdorNet
     │
Scientific / ML models
     │
     ├── OpenPOM
     │
     └── future models
     │
     ▼
Digital odor representation
     │
     ▼
┌──────────────────────────────┐
│          OpenSmell           │
│                              │
│  Representation             │
│  Specification              │
│  Python SDK                 │
│  Validation                 │
│  Scheme Registry            │
│  Adapters                   │
└──────────────────────────────┘
     │
     ├───────────────┐
     ▼               ▼
Applications     Device mapper
                     │
                     ▼
                Device adapter
                     │
             ┌───────┼────────┐
             ▼       ▼        ▼
          Scentree  MPEG-V   Future
                             devices
```

This architecture is exploratory and may change substantially as the specification develops.

---

## Roadmap

### OpenSmell 0.1

Current work focuses on the foundations:

- [x] Initial repository structure
- [x] Initial `.osmell` JSON representation
- [x] JSON Schema validation
- [x] Python data models
- [x] `.osmell` parser
- [x] Python packaging
- [x] Automated tests
- [x] GitHub Actions CI
- [x] Representation scheme architecture
- [x] Scheme Registry
- [x] Semantic descriptor scheme
- [ ] Serialization / `.osmell` writer
- [ ] Public Python creation API
- [ ] Additional representation schemes
- [ ] Scheme-specific test suite
- [ ] Specification documentation
- [ ] RFC process
- [ ] CLI tools
- [ ] Virtual olfactory device / simulator
- [ ] Device adapter interface
- [ ] MPEG-V interoperability investigation
- [ ] Experimental hardware adapter

The roadmap is intentionally incremental.

The immediate goal is not physical odor reproduction. It is establishing a technically sound and extensible representation and interoperability architecture.

---

## What OpenSmell is not

OpenSmell is currently **not**:

- a physical smell generator;
- an electronic nose;
- a chemical analysis platform;
- an odor prediction model;
- a finished networking protocol;
- a replacement for MPEG-V;
- a standardized set of universal odor primaries;
- a claim that arbitrary smells can currently be perfectly digitized and reproduced.

OpenSmell is an experimental interoperability framework intended to connect technologies that address those problems.

---

## Current status

OpenSmell is currently in **early experimental development**.

The `0.1` specification and APIs may change without backward compatibility while the fundamental architecture is being explored.

Do not rely on the current format for production systems.

---

## Contributing

OpenSmell is being developed openly.

Contributions, technical discussions, prior-art references, experiments, and criticism of the architecture are welcome.

Areas of particular interest include:

- digital olfaction research;
- olfactory perception;
- odor representation;
- machine learning for olfaction;
- scent display hardware;
- interoperability;
- sensory standards;
- VR/AR olfactory interfaces;
- serialization and protocol design.

As the project matures, formal contribution guidelines and an RFC process will be introduced.

---

## RFCs

Significant architectural decisions are intended to be documented through RFCs.

Potential RFC topics include:

```text
RFC-0001  OpenSmell vision and scope
RFC-0002  Core odor representation model
RFC-0003  Representation scheme architecture
RFC-0004  .osmell serialization format
RFC-0005  Device abstraction
```

The RFC process will allow design decisions to remain documented and open to technical discussion.

---

## License

A project license has not yet been finalized.

Before external contributions or public releases beyond the experimental stage, an explicit open-source license should be selected and added to the repository.

---

## Project

OpenSmell is developed as an independent open-source experiment into interoperability for digital olfaction.

Repository:

`YAAASSS/OpenSmell`

---

**OpenSmell — exploring an open interoperability layer for digital olfaction.**
# OpenSmell

**An open interoperability framework for digital olfaction.**

OpenSmell is an experimental open-source project for representing, exchanging, validating, and eventually rendering digital olfactory information across applications and devices.

The goal is not to define how smell must physically be reproduced. Instead, OpenSmell aims to provide a common interoperability layer between odor data, software applications, scientific models, and heterogeneous olfactory rendering technologies.

> [!IMPORTANT]
> OpenSmell is currently an early-stage experimental project.
> Version `0.1` is a pre-alpha release and should not be considered a stable standard.

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

The project aims to investigate and implement this interoperability layer.

---

## Core principle

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

## What OpenSmell 0.1 provides

The current reference implementation includes:

- a JSON-based `.osmell` document format;
- JSON Schema validation;
- Python data models;
- `.osmell` loading and serialization;
- multiple representations per odor;
- representation scheme validation;
- a scheme registry;
- semantic descriptor representations;
- chemical SMILES representations;
- builders for creating OpenSmell objects;
- forward-compatible handling of unknown schemes;
- preservation of unknown extension fields;
- document-level lossless round trips;
- an experimental OdorNet adapter;
- optional PubChem chemical identity enrichment;
- automated tests and CI;
- an RFC-based design process.

The current implementation deliberately remains small.

OpenSmell 0.1 does **not** attempt to solve physical odor reproduction.

---

## Representation model

An OpenSmell odor may contain multiple representations of the same conceptual odor.

For example:

```text
                         Odor
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         Semantic     Perceptual    Chemical
             │            │            │
             └────────────┼────────────┘
                          ▼
                     OpenSmell
```

Different applications can use the representations they understand.

OpenSmell 0.1 recognizes the following broad representation type names:

```text
semantic
perceptual
chemical
mixture
```

These are broad categories only.

The actual interpretation of a representation is defined by its **scheme**.

Unknown representation types and unknown schemes are allowed so that OpenSmell can evolve without requiring every implementation to understand every possible representation.

---

## Representation schemes

Every representation identifies a scheme.

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

identifies the broad representation family.

```text
scheme
```

defines the specific rules used to interpret the data.

This separation allows OpenSmell to transport representations produced by different scientific models, datasets, organizations, and future technologies.

---

## Built-in schemes

### `org.opensmell.semantic.descriptors`

Version:

```text
0.1
```

Representation type:

```text
semantic
```

This scheme represents an odor using human-readable semantic descriptors.

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

### `org.opensmell.chemical.smiles`

Version:

```text
0.1
```

Representation type:

```text
chemical
```

This scheme associates molecular structure information with an OpenSmell odor using SMILES.

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

OpenSmell Core verifies that the SMILES value is a non-empty string.

It does not attempt to prove chemical validity.

A chemical representation also does not imply that the represented molecule alone is sufficient to reproduce the perceived odor.

---

## `.osmell` documents

OpenSmell 0.1 uses UTF-8 JSON.

The recommended file extension is:

```text
.osmell
```

Example:

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

The same odor can therefore carry chemical and semantic information without requiring either representation to be derived from the other.

---

## Extensibility and forward compatibility

OpenSmell is designed so that information unknown to one implementation can still be transported.

Conceptually:

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

The Python implementation can preserve unknown extension fields at the following levels:

```text
Document
├── extra
└── Odor
    ├── extra
    ├── Metadata
    │   └── extra
    └── Representation
        ├── extra
        └── Scheme
            └── extra
```

This allows newer or experimental information to survive a read/write cycle even when the implementation does not understand its meaning.

Official OpenSmell fields always take precedence over extension fields.

---

## Python reference implementation

OpenSmell currently provides a Python reference implementation.

Supported versions:

```text
Python 3.10+
```

### Installation for development

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

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install OpenSmell with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

---

## Loading an odor

The simple API returns the odor contained in an OpenSmell document:

```python
import opensmell

odor = opensmell.load("examples/coffee.osmell")

print(odor.id)
```

Access metadata:

```python
print(odor.metadata.labels["en"])
```

Access representations:

```python
representation = odor.representations[0]

print(representation.type)
print(representation.scheme.id)
print(representation.scheme.version)
```

---

## Lossless document loading

Applications such as editors, converters, proxies, or interoperability tools may need to preserve information they do not understand.

For those applications, OpenSmell provides:

```python
import opensmell

document = opensmell.load_document(
    "examples/coffee.osmell"
)

opensmell.dump(
    document,
    "coffee-copy.osmell"
)
```

`load_document()` returns the complete OpenSmell document model rather than only its odor.

This allows document-level extension fields to survive the round trip.

The original API remains available:

```python
odor = opensmell.load("examples/coffee.osmell")
```

so existing code does not need to migrate to `Document` unless document-level preservation is required.

---

## Creating OpenSmell objects

OpenSmell includes builders for common representations.

Example:

```python
from opensmell import builders

semantic = builders.semantic_descriptors(
    "coffee",
    "roasted",
    language="en",
)

chemical = builders.chemical_smiles(
    "CCO"
)

odor = builders.odor(
    representations=[
        semantic,
        chemical,
    ]
)
```

An identifier can be generated automatically for newly created odor objects.

The resulting odor can be serialized:

```python
import opensmell

opensmell.dump(
    odor,
    "example.osmell"
)
```

---

## Validation

OpenSmell currently performs two levels of validation.

### Core validation

The complete document is validated against the OpenSmell 0.1 JSON Schema.

This verifies structural requirements such as:

- OpenSmell version;
- odor identifier;
- representations;
- scheme identifiers and versions;
- metadata structure;
- required JSON types.

### Scheme validation

If OpenSmell recognizes a representation scheme, its data is validated using the corresponding scheme validator.

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
   ├── known ──────► validate scheme data
   │
   └── unknown ────► preserve opaque data
   │
   ▼
Python objects
```

For registered schemes, OpenSmell also verifies that the representation type matches the type expected by the scheme.

Unknown schemes are not rejected merely because the implementation does not recognize them.

---

## Scheme Registry

The Python implementation contains a Scheme Registry.

It maps:

```text
scheme ID + version
```

to scheme-specific validation behavior.

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

This avoids hard-coding every future representation into the core parser.

---

## OdorNet adapter

OpenSmell includes an experimental adapter for importing records from OdorNet.

OdorNet provides molecular structures together with olfactory category labels.

The adapter can convert an OdorNet record into OpenSmell representations.

Conceptually:

```text
OdorNet record
     │
     ├── SMILES
     │      │
     │      ▼
     │  chemical representation
     │
     └── odor labels
            │
            ▼
       semantic representation
            │
            ▼
        OpenSmell Odor
```

The adapter does not make OdorNet part of the OpenSmell Core specification.

OdorNet is an external source of olfactory information.

The adapter is located at:

```text
src/opensmell/adapters/odornet.py
```

---

## Provenance experiment

The OdorNet adapter currently experiments with representation-level provenance.

Example:

```json
{
  "provenance": {
    "source": "OdorNet"
  }
}
```

This information is preserved through the OpenSmell extension mechanism.

Provenance is currently experimental and is being discussed through the RFC process.

It is **not yet a normative OpenSmell 0.1 Core field**.

---

## PubChem enrichment

OpenSmell also contains an optional PubChem enrichment utility.

It can resolve a SMILES structure to chemical identity information such as:

```text
PubChem title
IUPAC name
canonical/connectivity SMILES
InChIKey
```

Example conceptual workflow:

```text
SMILES
  │
  ▼
PubChem
  │
  ├── Title
  ├── IUPAC name
  ├── canonical SMILES
  └── InChIKey
```

PubChem enrichment is intentionally separate from OpenSmell Core.

OpenSmell does not require PubChem, network access, or any particular external chemical database to parse an `.osmell` document.

---

## OdorNet dataset enrichment tool

The repository contains a development tool:

```text
tools/enrich_odornet.py
```

It can enrich a local OdorNet dataset with PubChem chemical identity information.

The tool supports:

- persistent caching;
- interruption and resume;
- duplicate SMILES avoidance;
- request throttling;
- retries for temporary network/server failures;
- periodic checkpoints;
- enriched CSV generation.

Generated datasets and PubChem caches are local development artifacts and are excluded from Git.

The tool is not part of the OpenSmell Core protocol.

---

## Architecture

The current architecture can be summarized as:

```text
External data / research
│
├── OdorNet
├── OpenPOM
├── scientific datasets
├── chemical databases
└── future models
        │
        ▼
┌─────────────────────────────────┐
│            OpenSmell            │
│                                 │
│  .osmell representation        │
│  JSON Schema                   │
│  Python models                 │
│  Parser / serializer           │
│  Scheme Registry               │
│  Validation                    │
│  Builders                      │
│  Adapters                      │
│  Optional enrichment           │
└─────────────────────────────────┘
        │
        ├───────────────┐
        ▼               ▼
 Applications       Mapper
                        │
                        ▼
                 Device adapter
                        │
               ┌────────┼────────┐
               ▼        ▼        ▼
            Existing   Future   Research
            devices    devices  systems
```

The lower rendering/device layers are exploratory and are not defined by OpenSmell 0.1 Core.

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
│   ├── coumarin.osmell
│   ├── invalid.osmell
│   ├── vanilla.osmell
│   └── odornet_pipeline.py
│
├── rfcs/
│   ├── RFC-0001.md
│   ├── RFC-0002.md
│   └── RFC-0003.md
│
├── schema/
│   └── opensmell-0.1.schema.json
│
├── spec/
│   └── opensmell-0.1.md
│
├── src/
│   └── opensmell/
│       ├── adapters/
│       │   └── odornet.py
│       │
│       ├── enrichment/
│       │   └── pubchem.py
│       │
│       ├── schemas/
│       │   └── opensmell-0.1.schema.json
│       │
│       ├── schemes/
│       │   ├── registry.py
│       │   ├── semantic_descriptors.py
│       │   └── chemical_smiles.py
│       │
│       ├── __init__.py
│       ├── builders.py
│       ├── exceptions.py
│       ├── models.py
│       ├── parser.py
│       ├── serializer.py
│       └── validation.py
│
├── tests/
│   ├── test_builders.py
│   ├── test_conformance.py
│   ├── test_odornet_adapter.py
│   ├── test_parser.py
│   ├── test_pubchem_enrichment.py
│   └── test_schema.py
│
├── tools/
│   └── enrich_odornet.py
│
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

---

## Running tests

Install development dependencies and run:

```bash
python -m pytest
```

The current test suite contains **60 tests** covering core behavior, including:

- parsing;
- serialization;
- builders;
- JSON Schema consistency;
- conformance;
- known and unknown schemes;
- scheme/type validation;
- extension preservation;
- document-level round trips;
- OdorNet adapter behavior;
- PubChem enrichment behavior;
- experimental provenance preservation.

GitHub Actions runs the tests against:

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

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

OdorNet provides molecular olfactory labels and datasets.

OpenSmell currently includes an experimental adapter for converting OdorNet records into OpenSmell representations.

OdorNet remains an external data source rather than part of the OpenSmell specification.

### D2Smell

D2Smell is ongoing research into the digitization and remote reproduction of smell.

Future results from projects such as D2Smell may help define useful perceptual or renderable representations.

### Scentree

Scentree is an open-source olfactory display project and represents the type of hardware that could eventually be explored through an OpenSmell device adapter.

OpenSmell's objective is therefore **interoperability**, not claiming invention of digital smell transmission.

---

## RFCs

Significant architectural decisions are documented and explored through RFCs.

Current RFCs:

```text
RFC-0001  OpenSmell Vision and Scope
RFC-0002  Odor Representation Model
RFC-0003  Representation Provenance
```

RFCs allow experimental concepts to be discussed without prematurely making them part of the OpenSmell Core specification.

In particular, representation provenance remains experimental and does not modify OpenSmell 0.1.

---

## Roadmap

### OpenSmell 0.1 foundation

Completed:

- [x] Initial repository structure
- [x] `.osmell` JSON representation
- [x] JSON Schema validation
- [x] Python data models
- [x] `.osmell` parser
- [x] `.osmell` serializer
- [x] Python packaging
- [x] Automated tests
- [x] GitHub Actions CI
- [x] Representation scheme architecture
- [x] Scheme Registry
- [x] Semantic descriptor scheme
- [x] Chemical SMILES scheme
- [x] Public Python builders
- [x] Scheme-specific validation
- [x] Unknown scheme support
- [x] Extension preservation
- [x] Lossless document model
- [x] Initial specification documentation
- [x] RFC process
- [x] OdorNet adapter experiment
- [x] PubChem enrichment experiment

### Next investigations

Potential next work includes:

- [ ] Analyze the enriched OdorNet dataset
- [ ] Refine provenance through RFC-0003
- [ ] Define the OpenSmell 0.2 roadmap
- [ ] Investigate perceptual representation schemes
- [ ] Investigate mixture/renderable representations
- [ ] Investigate MPEG-V interoperability
- [ ] Design a device abstraction layer
- [ ] Build a virtual olfactory device/simulator
- [ ] Explore experimental hardware adapters
- [ ] Add CLI tooling
- [ ] Publish project documentation through opensmell.org

The roadmap is intentionally incremental.

New concepts should demonstrate a real interoperability need before being added to OpenSmell Core.

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
- a universal database of odor molecules;
- a claim that arbitrary smells can currently be perfectly digitized and reproduced.

OpenSmell is an experimental interoperability framework intended to connect technologies that address parts of those problems.

---

## Current status

OpenSmell is currently in **pre-alpha experimental development**.

The first public development release is:

```text
v0.1.0
```

The format and APIs may still change before a stable `1.0` specification.

Do not rely on the current format for production systems.

The current priority is to validate the architecture through real datasets, models, interoperability experiments, and eventually device integrations.

---

## Project namespace

The project controls:

```text
opensmell.org
```

The OpenSmell 0.1 JSON Schema therefore uses the stable identifier:

```text
https://opensmell.org/schema/opensmell-0.1.schema.json
```

The domain is intended to provide a stable namespace for future specifications, schemas, RFCs, and documentation.

The project website and documentation infrastructure are not yet deployed.

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

---

## License

OpenSmell is licensed under the Apache License 2.0.

See the [LICENSE](LICENSE) file for details.

---

## Project

OpenSmell is developed as an independent open-source experiment into interoperability for digital olfaction.

Repository:

```text
YAAASSS/OpenSmell
```

Project namespace:

```text
opensmell.org
```

---

**OpenSmell — an open interoperability layer for digital olfaction.**
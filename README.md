# OpenSmell

**An open interoperability framework for digital olfaction.**
OpenSmell is an experimental open-source project for representing, exchanging,
validating, and eventually rendering digital olfactory information across
applications and devices.
The goal is not to define how smell must physically be reproduced. Instead,
OpenSmell aims to provide a common interoperability layer between odor data,
software applications, scientific models, and heterogeneous olfactory
rendering technologies.
> [!IMPORTANT]
>
> OpenSmell is currently an early-stage experimental project.
>
> Version `0.1` is a pre-alpha release and should not be considered a stable
> standard.

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
However, these systems may represent odors differently and may rely on
different hardware, models, vocabularies, measurement protocols, or delivery
technologies.
OpenSmell explores a simple question:
> **Can digital odor information be represented and exchanged independently
> from the technology that eventually interprets or renders it?**
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
OpenSmell should therefore describe olfactory information without forcing
every device to use the same physical reproduction mechanism.
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
        ┌──────┼──────┐
        ▼      ▼      ▼
 Application  Mapper  Storage
               │
               ▼
         Device adapter
               │
               ▼
        Olfactory device
```

OpenSmell focuses primarily on the interoperability layer, not on the physical
diffuser itself.

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
- experimental semantic annotation modeling based on real OdorNet data;
- an experimental Keller/Vosshall adapter for quantitative perceptual
  measurements;
- optional PubChem chemical identity enrichment;
- experimental deterministic resource identification based on canonical source
  identity and UUIDs;
- cross-language Python/JavaScript identifier interoperability tests;
- an experimental generic resource model with `Stimulus`,
  `ObservationTarget`, `Observation`, versioned `ResultScheme`, and
  scheme-defined `Result` objects;
- an experimental flat `ResourceGraph` with Resource-ID references and
  unresolved-reference preservation;
- an experimental JSON ResourceGraph serialization format;
- dataset-scale ResourceGraph round-trip validation across human
  psychophysics, biological physiology, and electronic olfaction;
- automated tests and CI;
- an RFC-based design process.
The current implementation deliberately keeps these experimental graph concepts
outside OpenSmell 0.1 Core.
OpenSmell 0.1 does **not** attempt to solve physical odor reproduction.

---

## Representation model

An OpenSmell odor may contain multiple representations of the same conceptual
odor.
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
Unknown representation types and unknown schemes are allowed so that
OpenSmell can evolve without requiring every implementation to understand
every possible representation.

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
This separation allows OpenSmell to transport representations produced by
different scientific models, datasets, organizations, and future
technologies.

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

This scheme associates molecular structure information with an OpenSmell odor
using SMILES.
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
A chemical representation also does not imply that the represented molecule
alone is sufficient to reproduce the perceived odor.

---

## Experimental representation schemes

Experimental RFCs currently investigate richer representation schemes that
are deliberately kept outside the normative OpenSmell 0.1 Core.

### Semantic annotations

RFC-0004 investigates:

```text
org.opensmell.semantic.annotations
```

The model distinguishes categorical states such as:

```text
present
absent
unknown
```

This distinction is important for datasets where missing information must not
automatically be interpreted as absence.
The model has been tested using OdorNet data.

### Quantitative perceptual measurements

RFC-0005 investigates:

```text
org.opensmell.perceptual.measurements
```

The model represents quantitative perceptual measurements while preserving an
important distinction:

```text
measurement absent ≠ measured value 0
```

The model has been tested against the Keller/Vosshall DREAM Olfaction
Prediction Challenge dataset.
These schemes remain experimental and are not automatically part of
OpenSmell 0.1 Core.

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

The same odor can therefore carry chemical and semantic information without
requiring either representation to be derived from the other.

---

## Extensibility and forward compatibility

OpenSmell is designed so that information unknown to one implementation can
still be transported.
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

The Python implementation can preserve unknown extension fields at the
following levels:

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

This allows newer or experimental information to survive a read/write cycle
even when the implementation does not understand its meaning.
Official OpenSmell fields always take precedence over extension fields.
Applications that require preservation of document-level extension fields
should use the complete `Document` API rather than discarding the root
document structure.

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

Applications such as editors, converters, proxies, or interoperability tools
may need to preserve information they do not understand.
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

`load_document()` returns the complete OpenSmell document model rather than
only its odor.
This allows document-level extension fields to survive the round trip.
The original API remains available:

```python
odor = opensmell.load("examples/coffee.osmell")
```

so existing code does not need to migrate to `Document` unless document-level
preservation is required.

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

If OpenSmell recognizes a representation scheme, its data is validated using
the corresponding scheme validator.
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

For registered schemes, OpenSmell also verifies that the representation type
matches the type expected by the scheme.
Unknown schemes are not rejected merely because the implementation does not
recognize them.
Experimental scheme validators may exist without being registered as
normative OpenSmell 0.1 schemes.

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
     └── odor annotations
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

OpenSmell experiments preserve the distinction between positive, negative,
and unresolved OdorNet annotation states rather than assuming that missing
information means absence.

---

## Keller/Vosshall adapter

OpenSmell has also been tested against quantitative human olfactory
measurements from the Keller/Vosshall DREAM Olfaction Prediction Challenge
dataset.
The experimental adapter is located at:

```text
src/opensmell/adapters/keller_vosshall.py
```

This work motivated RFC-0005 and the distinction between:

```text
semantic annotation
        ≠
quantitative perceptual measurement
```

It also preserves the distinction between:

```text
measurement not performed
        ≠
measured value 0
```

The Keller/Vosshall dataset remains an external scientific dataset and is not
part of the OpenSmell source distribution or Core specification.

---

## Provenance experiment

Representation-level provenance is being investigated through RFC-0003.
Example:

```json
{
  "provenance": {
    "source": "OdorNet"
  }
}
```

This information can be preserved through the OpenSmell extension mechanism.
Provenance is currently experimental.
It is **not yet a normative OpenSmell 0.1 Core field**.

---

## PubChem enrichment

OpenSmell contains an optional PubChem enrichment utility.
It can resolve a SMILES structure to chemical identity information such as:

```text
PubChem title
IUPAC name
canonical/connectivity SMILES
InChIKey
```

Conceptually:

```text
SMILES
  │
  ▼
PubChem
  │
  ├── Title
  ├── IUPAC name
  ├── canonical/connectivity SMILES
  └── InChIKey
```

PubChem enrichment is intentionally separate from OpenSmell Core.
OpenSmell does not require PubChem, network access, or any particular external
chemical database to parse an `.osmell` document.

---

## OdorNet dataset enrichment tool

The repository contains a development tool:

```text
tools/enrich_odornet.py
```

It can enrich a local OdorNet dataset with PubChem chemical identity
information.
The tool supports:
- persistent caching;
- interruption and resume;
- duplicate SMILES avoidance;
- request throttling;
- retries for temporary network/server failures;
- periodic checkpoints;
- enriched CSV generation.
Generated datasets and PubChem caches are local development artifacts and are
excluded from Git.
The tool is not part of the OpenSmell Core protocol.

---

## Experimental resource identification

RFC-0006 investigates a resource identification model for future OpenSmell
resource graphs.
The current experimental design distinguishes:

```text
Scheme identifier
OpenSmell Resource ID
External/source identifier
Reference
```

These concepts serve different purposes and should not be conflated.

### Resource IDs

The current experimental candidate uses canonical lowercase UUID strings.
Two generation modes are investigated:

```text
UUIDv4
```

for newly created resources without deterministic source identity, and:

```text
UUIDv5
```

for deterministic imports of resources with stable source identity.
RFC-0006 remains experimental and does not change the unrestricted
non-empty-string `odor.id` rule of OpenSmell 0.1.

### Deterministic source identity

Dataset imports can derive an experimental Resource ID from:

```text
dataset
resource type
source identity
```

Source identity may be atomic:

```json
"113L_038"
```

or composite:

```json
{
  "stimulus": "1001_3.12e-13",
  "target": "111L_001"
}
```

Composite structural keys are deliberately restricted to:

```text
^[a-z][a-z0-9_.-]\*$
```

while values may contain Unicode scalar strings.
This restriction resulted from cross-language interoperability experiments
showing that unconstrained Unicode object-key ordering can produce different
canonical byte sequences in different runtimes.
No implicit Unicode normalization is currently performed.
Therefore canonically equivalent Unicode strings with different code-point
sequences remain distinct source identities.

---

## Identifier interoperability experiments

The experimental identifier implementation is located under:

```text
src/opensmell/experimental/
```

The repository contains Python and JavaScript interoperability tooling.
Golden and torture vectors test:
- deterministic canonical serialization;
- UTF-8 generation octets;
- UUIDv5 generation;
- quotes and backslashes;
- JSON control-character escaping;
- Unicode values;
- CJK text;
- emoji;
- Unicode normalization differences;
- composite identity ordering;
- delimiter-boundary ambiguity;
- invalid surrogate code points.
The current torture-vector suite contains 17 vectors.
Python and JavaScript reproduce identical canonical text, UTF-8 octets, and
UUIDv5 values for all current vectors.
These results are experimental evidence for RFC-0006, not a declaration that
the identification model is final.

---

## Burton 2022 identity experiment

OpenSmell also uses the Burton 2022 dataset distributed through Pyrfume as a
real-world stress test for resource identity, graph structure, physiological
Result data, and ResourceGraph serialization.
This dataset contains physiological mouse olfactory-bulb response data.
It is intentionally **not** treated as human perceptual measurement data.
The experiment distinguishes:

```text
Molecule
   │
   ▼
Stimulus
   │
   ▼
Observation ─────► ObservationTarget
   │
   ▼
Result
```

The deterministic identity experiment generated:

```text
Molecules:          186
Stimuli:            227
Targets:          1,008
Observations:    187,748
------------------------
Total IDs:       189,169
```

with:

```text
Unique generation names: 189,169
Unique Resource IDs:     189,169
Observed name collisions:      0
Observed UUID collisions:      0
```

The materialized experimental ResourceGraph deliberately does not invent a
generic Chemical resource class for the 186 referenced molecule identities.
Its dataset-scale JSON round-trip therefore contains:

```text
Materialized resources:       188,983
Stimulus resources:               227
Observation targets:            1,008
Observations:                  187,748
Result objects:               187,748
Unresolved molecule IDs:          186
Source-less stimuli:                 1
Stimuli without conditions:          2
DeltaF values:                 187,748
Zero DeltaF:                   184,356
Non-zero DeltaF:                 3,392
Compact JSON bytes:         81,220,605
```

The complete graph survived:

```text
ResourceGraph -> JSON -> ResourceGraph
```

with resource order, structural references, unresolved references, Result
schemes, Result data, and DeltaF values preserved. A second serialization was
also stable.
The experiment preserves unresolved source references rather than inventing
missing metadata or silently discarding them.
The Burton dataset remains external to OpenSmell and is excluded from the
source distribution.

---

## Architecture

The current architecture can be summarized as:

```text
External data / research
│
├── OdorNet
├── Keller/Vosshall
├── Burton / Pyrfume
├── UCI Gas Sensor Array Drift
├── OpenPOM
├── chemical databases
├── scientific datasets
└── future models
        │
        ▼
┌─────────────────────────────────┐
│            OpenSmell            │
│                                 │
│  .osmell representation         │
│  JSON Schema                    │
│  Python models                  │
│  Parser / serializer            │
│  Scheme Registry                │
│  Validation                     │
│  Builders                       │
│  Adapters                       │
│  Experimental models            │
│  ResourceGraph                  │
│  Experimental graph JSON        │
│  Optional enrichment            │
└─────────────────────────────────┘
        │
        ├───────────────┐
        ▼               ▼
 Applications          Mapper
                        │
                        ▼
                   Device adapter
                        │
                   ┌────┼────┐
                   ▼    ▼    ▼
                Existing Future Research
                devices  devices systems
```

The experimental resource architecture currently separates:

```text
source resource
      │
      ▼
   Stimulus
      │
      ▼
 Observation ─────► ObservationTarget
      │
      ▼
   Result(s)
      │
      ▼
scheme-defined semantics
```

This same generic structure has been exercised against human psychophysical
measurements, mouse olfactory-bulb physiology, and electronic sensor-array
features without introducing one universal measurement class.
The lower rendering/device layers remain exploratory and are not defined by
OpenSmell 0.1 Core.

---

## Project structure

```text
OpenSmell/
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── examples/
│   ├── *.osmell
│   ├── odornet_pipeline.py
│   └── identifier_torture_vectors.json
│
├── rfcs/
│   ├── RFC-0001.md
│   ├── RFC-0002.md
│   ├── RFC-0003.md
│   ├── RFC-0004.md
│   ├── RFC-0005.md
│   ├── RFC-0006.md
│   ├── RFC-0007.md
│   └── RFC-0008.md
│
├── schema/
│   ├── experimental-resource-graph-0.1.schema.json
│   └── opensmell-0.1.schema.json
│
├── spec/
│   └── opensmell-0.1.md
│
├── src/
│   └── opensmell/
│       ├── adapters/
│       ├── enrichment/
│       ├── experimental/
│       │   ├── graph.py
│       │   ├── graph_serialization.py
│       │   ├── generic_graph.py
│       │   ├── identifiers.py
│       │   └── resources.py
│       ├── schemas/
│       ├── schemes/
│       ├── builders.py
│       ├── exceptions.py
│       ├── models.py
│       ├── parser.py
│       ├── serializer.py
│       └── validation.py
│
├── tests/
│
├── tools/
│
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

Some experimental tools and adapters operate on external scientific datasets.
Those datasets are not part of the OpenSmell source distribution and are
excluded from Git where required.

---

## Running tests

Install development dependencies and run:

```bash
python -m pytest
```

On environments where the default pytest temporary directory is unavailable,
an alternative base temporary directory may be specified.
The current complete test baseline is:

```text
578 passed
```

The ResourceGraph serialization test module currently contains 63 passing test
cases.
The suite covers core and experimental behavior, including:
- parsing and serialization;
- builders;
- JSON Schema consistency;
- conformance;
- known and unknown schemes;
- scheme/type validation;
- extension preservation;
- document-level round trips;
- OdorNet adapter behavior;
- PubChem enrichment behavior;
- semantic annotation experiments;
- Keller/Vosshall perceptual measurement experiments;
- deterministic Resource ID generation;
- canonical source identity;
- Unicode and escaping edge cases;
- golden interoperability vectors;
- experimental ResourceGraph behavior;
- ResourceGraph JSON serialization and parsing;
- unresolved-reference preservation;
- versioned Result schemes;
- serialization stability;
- rejection of non-standard JSON numeric constants such as `NaN`,
  `Infinity`, and `-Infinity`;
- preservation of valid finite values including explicit `-0.0`.
GitHub Actions runs the tests against:
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13
Some dataset-scale interoperability experiments are development tools rather
than normal unit tests because the underlying external datasets are not
distributed with OpenSmell.
Three complete experimental ResourceGraph JSON round trips currently succeed:

```text
UCI Gas Sensor Array Drift
  resources:          14,144
  JSON bytes:     61,600,816
Keller/Vosshall
  resources:          56,015
  JSON bytes:     47,993,421
Burton 2022
  resources:         188,983
  JSON bytes:     81,220,605
```

Combined:

```text
Materialized resources: 259,142
Compact JSON bytes:     190,814,842
```

These experiments cover electronic olfaction, human psychophysics, and
biological physiology.

---

## Relationship with existing work

OpenSmell does not assume that digital olfaction begins with this project.
Existing research, standards, datasets, models, and olfactory interfaces
already address important parts of the problem.
Relevant work includes:

### MPEG-V / ISO/IEC 23005

MPEG-V defines representations and control mechanisms for sensory effects,
including olfactory effects.
OpenSmell should investigate interoperability with MPEG-V rather than
duplicate existing standardization work.

### OWidgets

OWidgets explored device-independent olfactory experience design and
communication with scent-delivery devices.
Its work on mapping, scheduling, and uniform device interfaces is relevant
prior art for OpenSmell.

### OpenPOM

OpenPOM provides open-source machine-learning tools related to perceptual odor
mapping.
Future OpenSmell representations could potentially transport outputs from
models of this kind.

### OdorNet

OdorNet provides molecular olfactory labels and datasets.
OpenSmell currently includes an experimental adapter for converting OdorNet
records into OpenSmell representations.
OdorNet remains an external data source rather than part of the OpenSmell
specification.

### Keller/Vosshall

The Keller/Vosshall DREAM Olfaction Prediction Challenge dataset contains
quantitative human olfactory measurements.
OpenSmell uses this dataset experimentally to test the distinction between
categorical semantic information and quantitative perceptual measurements.
The dataset remains external to OpenSmell.

### Pyrfume / Burton 2022

Pyrfume provides structured olfactory datasets.
The Burton 2022 archive is used experimentally to investigate molecules,
stimuli, biological observations, source identifiers, and deterministic
resource identity.
The physiological DeltaF responses in this dataset are not treated as human
perceptual measurements.

### D2Smell

D2Smell is ongoing research into the digitization and remote reproduction of
smell.
Future results from projects such as D2Smell may help define useful perceptual
or renderable representations.

### Scentree

Scentree is an open-source olfactory display project and represents the type
of hardware that could eventually be explored through an OpenSmell device
adapter.
OpenSmell's objective is therefore **interoperability**, not claiming
invention of digital smell transmission.

---

## RFCs

Significant architectural decisions are documented and explored through RFCs.
Current RFCs:

```text
RFC-0001  OpenSmell Vision and Scope
RFC-0002  Odor Representation Model
RFC-0003  Representation Provenance
RFC-0004  Semantic Annotation Model
RFC-0005  Quantitative Perceptual Measurement Model
RFC-0006  Resource Identification and Deterministic Source Identity
RFC-0007  Stimulus and Observation Resource Model
RFC-0008  Generic Resource Graph and Extensible Resource Types
```

RFCs allow experimental concepts to be investigated without prematurely
making them part of the OpenSmell Core specification.
RFC-0003 investigates provenance without making provenance a normative
OpenSmell 0.1 Core field.
RFC-0004 investigates richer categorical semantic annotations, including the
distinction between present, absent, and unknown information.
RFC-0005 investigates quantitative perceptual measurements and explicitly
distinguishes measurement absence from a measured value of zero.
RFC-0006 investigates resource identity, deterministic dataset imports,
structured source identity, references, and cross-language UUID generation.
RFC-0007 investigates the relationship between Stimulus,
ObservationTarget, Observation, and scheme-defined Result data. Its prototype
also includes a flat ResourceGraph, an experimental JSON graph serialization,
a Draft 2020-12 structural JSON Schema, portable conformance vectors, and
Python/JavaScript interoperability checks.
RFC-0008 investigates a successor generic graph architecture in which resource
membership is not limited to a closed Python union. Unknown serialized resource
types can be preserved as `GenericResource`, while typed resource parsing,
serialization, and graph queries are driven by `ResourceTypeRegistry`.
RFC-0006, RFC-0007, and RFC-0008 remain Draft experimental work targeting
future OpenSmell versions.
Experimental RFCs do not automatically modify OpenSmell 0.1.

---

## Roadmap

### OpenSmell 0.1 foundation

Completed:
- [x] initial repository structure
- [x] `.osmell` JSON representation
- [x] JSON Schema validation
- [x] Python data models
- [x] `.osmell` parser
- [x] `.osmell` serializer
- [x] Python packaging
- [x] automated tests
- [x] GitHub Actions CI
- [x] representation scheme architecture
- [x] Scheme Registry
- [x] semantic descriptor scheme
- [x] chemical SMILES scheme
- [x] public Python builders
- [x] scheme-specific validation
- [x] unknown scheme support
- [x] extension preservation
- [x] lossless document model
- [x] OpenSmell 0.1 specification
- [x] RFC process
- [x] OdorNet adapter experiment
- [x] PubChem enrichment experiment

### Interoperability research completed or in progress

- [x] semantic annotation model experiment
- [x] full OdorNet annotation round-trip experiment
- [x] quantitative perceptual measurement model experiment
- [x] Keller/Vosshall measurement round-trip experiment
- [x] resource identification design experiment
- [x] deterministic source identity experiment
- [x] Python/JavaScript identifier interoperability experiment
- [x] Burton 2022 resource-graph identity experiment
- [x] generic Stimulus and Observation resource model experiment
- [x] versioned Result scheme experiment
- [x] experimental ResourceGraph implementation
- [x] experimental ResourceGraph JSON serialization
- [x] UCI electronic-olfaction ResourceGraph round-trip
- [x] Keller/Vosshall ResourceGraph round-trip
- [x] Burton 2022 ResourceGraph round-trip
- [x] strict non-finite JSON number rejection
- [x] cross-language ResourceGraph serialization interoperability
- [x] experimental ResourceGraph structural JSON Schema
- [x] ResourceGraph schema/parser parity tests
- [x] portable ResourceGraph conformance vectors
- [x] nested Reference and ExternalIdentifier extension preservation
- [x] portable preservation checks in Python and JavaScript
- [x] RFC-0008 generic ResourceGraph prototype
- [x] unknown future resource type preservation experiment
- [x] extensible ResourceTypeRegistry prototype
- [x] registry-aware generic graph queries

### Next investigations

- [ ] finalize the experimental resource identification model
- [ ] investigate provenance integration with resource graphs
- [ ] define RFC-0008 resource type naming and versioning policy
- [ ] create an experimental RFC-0008 generic graph JSON Schema
- [ ] create portable RFC-0008 generic graph conformance vectors
- [ ] validate RFC-0008 custom resource types across language boundaries
- [ ] investigate streaming or partial loading for large ResourceGraphs
- [ ] investigate normative serialization and canonicalization requirements
- [ ] investigate mixture and renderable representations
- [ ] investigate MPEG-V interoperability
- [ ] design a device abstraction layer
- [ ] build a virtual olfactory device/simulator
- [ ] explore experimental hardware adapters
- [ ] add CLI tooling
- [ ] publish project documentation through opensmell.org
- [ ] define the OpenSmell 0.2 roadmap
The roadmap is intentionally incremental.
New concepts should demonstrate a real interoperability need through
experiments and real data before being incorporated into OpenSmell Core.

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
- a claim that arbitrary smells can currently be perfectly digitized and
  reproduced.
OpenSmell is an experimental interoperability framework intended to connect
technologies that address parts of those problems.

---

## Current status

OpenSmell is currently in **pre-alpha experimental development**.
The first public development release is:

```text
v0.1.0
```

Development on the main branch has progressed substantially beyond the contents
of the `v0.1.0` release.
The current experimental branch state includes RFC-0007 and RFC-0008,
the Stimulus/Observation resource model, the RFC-0007 ResourceGraph, versioned
Result schemes, experimental ResourceGraph JSON serialization and conformance
work, plus the RFC-0008 generic graph and extensible resource-type registry
prototype.
The current test baseline is:

```text
578 passed
```

Dataset-scale ResourceGraph JSON round trips have succeeded across three
independent domains:

```text
human psychophysics
biological physiology
electronic olfaction
```

Together these experiments serialize and reconstruct 259,142 materialized
resources and approximately 190.8 MB of compact JSON while preserving the
scientific values and graph relationships under test.
The format and APIs may still change before a stable `1.0` specification.
Do not rely on the current experimental graph format for production systems.
Cross-language RFC-0007 ResourceGraph interoperability has been validated with
Python/JavaScript golden vectors and portable conformance checks. The current
priority is to mature RFC-0008: define resource type naming/versioning,
introduce portable generic-graph conformance artifacts, validate custom resource
types across language boundaries, and continue testing the architecture against
genuinely different data and device domains before promoting experimental
concepts into OpenSmell Core.

---

## Project namespace

The project controls:

```text
opensmell.org
```

The OpenSmell 0.1 JSON Schema therefore uses the identifier:

```text
https://opensmell.org/schema/opensmell-0.1.schema.json
```

The domain is intended to provide a stable namespace for future
specifications, schemas, RFCs, and documentation.
The project website and documentation infrastructure are not yet deployed.

---

## Contributing

OpenSmell is being developed openly.
Contributions, technical discussions, prior-art references, experiments, and
criticism of the architecture are welcome.
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
Because OpenSmell is experimental, proposals should preferably be supported
by concrete interoperability requirements, existing research, real datasets,
or reproducible experiments.

---

## License

OpenSmell is licensed under the Apache License 2.0.
See the [LICENSE](LICENSE) file for details.
External scientific datasets used for experiments retain their respective
licenses and are not automatically covered by the OpenSmell license.

---

## Project

OpenSmell is developed as an independent open-source experiment into
interoperability for digital olfaction.
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

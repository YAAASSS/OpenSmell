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
"""Investigate cross-language ordering of Unicode composite identity keys.

This experiment intentionally uses one BMP private-use character and one
supplementary-plane emoji to expose possible ordering differences between
Unicode code-point ordering and UTF-16 code-unit ordering.

Nothing in this module is normative OpenSmell.
"""

from __future__ import annotations

from opensmell.experimental.identifiers import canonical_generation_name


PRIVATE_USE = "\uE000"
EMOJI = "\U0001F600"


def describe(value: str) -> str:
    codepoints = " ".join(
        f"U+{ord(character):04X}"
        for character in value
    )
    return f"{value!r} ({codepoints})"


def main() -> None:
    print("OpenSmell RFC-0006 Unicode key-ordering experiment")
    print("=" * 72)

    print()
    print("Keys")
    print("-" * 72)
    print("Private-use:", describe(PRIVATE_USE))
    print("Emoji      :", describe(EMOJI))

    source_a = {
        PRIVATE_USE: "private-use",
        EMOJI: "emoji",
    }

    source_b = {
        EMOJI: "emoji",
        PRIVATE_USE: "private-use",
    }

    canonical_a = canonical_generation_name(
        dataset="unicode_ordering",
        resource_type="target",
        source_identity=source_a,
    )

    canonical_b = canonical_generation_name(
        dataset="unicode_ordering",
        resource_type="target",
        source_identity=source_b,
    )

    print()
    print("Python canonical generation")
    print("-" * 72)
    print(canonical_a)

    print()
    print("Insertion-order independence")
    print("-" * 72)
    print(
        "PASS"
        if canonical_a == canonical_b
        else "FAIL"
    )

    print()
    print("Python sorted keys")
    print("-" * 72)

    for key in sorted(source_a):
        print(describe(key))

    print()
    print("UTF-8")
    print("-" * 72)
    print(canonical_a.encode("utf-8").hex())


if __name__ == "__main__":
    main()
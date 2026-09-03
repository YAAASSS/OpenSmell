"use strict";

/*
 * Investigate JavaScript ordering of Unicode composite identity keys.
 *
 * This intentionally compares a BMP private-use character with a
 * supplementary-plane emoji.
 *
 * Nothing in this module is normative OpenSmell.
 */

const PRIVATE_USE = "\uE000";
const EMOJI = "\u{1F600}";


function describe(value) {
    const codePoints = Array.from(value)
        .map(
            character =>
                "U+" +
                character
                    .codePointAt(0)
                    .toString(16)
                    .toUpperCase()
                    .padStart(4, "0")
        )
        .join(" ");

    return `${JSON.stringify(value)} (${codePoints})`;
}


function main() {
    console.log(
        "OpenSmell RFC-0006 JavaScript Unicode key-ordering experiment"
    );
    console.log("=".repeat(72));

    console.log();
    console.log("Keys");
    console.log("-".repeat(72));

    console.log(
        "Private-use:",
        describe(PRIVATE_USE)
    );

    console.log(
        "Emoji      :",
        describe(EMOJI)
    );

    const source = {
        [PRIVATE_USE]: "private-use",
        [EMOJI]: "emoji",
    };

    const sortedKeys = Object
        .keys(source)
        .sort();

    console.log();
    console.log("JavaScript sorted keys");
    console.log("-".repeat(72));

    for (const key of sortedKeys) {
        console.log(describe(key));
    }

    const orderedSource = {};

    for (const key of sortedKeys) {
        orderedSource[key] = source[key];
    }

    const canonical = JSON.stringify({
        dataset: "unicode_ordering",
        resource_type: "target",
        source_identity: orderedSource,
    });

    console.log();
    console.log("JavaScript canonical generation");
    console.log("-".repeat(72));

    console.log(canonical);

    console.log();
    console.log("UTF-8");
    console.log("-".repeat(72));

    console.log(
        Buffer
            .from(canonical, "utf8")
            .toString("hex")
    );
}


main();
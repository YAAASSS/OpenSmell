"""Compile the actual ESP32 sketch for the software-only native bench."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arduinojson", required=True, type=Path,
                        help="ArduinoJson 7.2.1 checkout (contains src/ArduinoJson.h)")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--compiler", default="g++")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-load", action="store_true", help="Explicit opt-in experimental dry resistive-load sketch")
    modes.add_argument("--lifecycle", action="store_true", help="Explicit opt-in experimental lifecycle LED sketch")
    args = parser.parse_args()
    dependency = args.arduinojson.resolve(strict=True)
    version = (dependency / "src/ArduinoJson/version.hpp").read_text()
    if '#define ARDUINOJSON_VERSION "7.2.1"' not in version:
        parser.error("This bench requires ArduinoJson 7.2.1")
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    flags = ["-DOPENSMELL_EXPERIMENTAL_LIFECYCLE", "-DOPENSMELL_NATIVE_BENCH"] if args.lifecycle or args.dry_load else []
    if args.dry_load:
        flags.append("-DOPENSMELL_EXPERIMENTAL_DRY_LOAD")
    subprocess.run([args.compiler, "-std=c++17", "-Wall", "-Wextra", *flags,
                    "-I" + str(root / "hardware/esp32/host"),
                    "-I" + str(dependency / "src"),
                    str(root / "hardware/esp32/host/main.cpp"), "-o", str(output)],
                   check=True, timeout=120)
    print(output)


if __name__ == "__main__":
    main()

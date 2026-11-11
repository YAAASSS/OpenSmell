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
    args = parser.parse_args()
    dependency = args.arduinojson.resolve(strict=True)
    version = (dependency / "src/ArduinoJson/version.hpp").read_text()
    if '#define ARDUINOJSON_VERSION "7.2.1"' not in version:
        parser.error("This bench requires ArduinoJson 7.2.1")
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([args.compiler, "-std=c++17", "-Wall", "-Wextra",
                    "-I" + str(root / "hardware/esp32/host"),
                    "-I" + str(dependency / "src"),
                    str(root / "hardware/esp32/host/main.cpp"), "-o", str(output)],
                   check=True, timeout=120)
    print(output)


if __name__ == "__main__":
    main()

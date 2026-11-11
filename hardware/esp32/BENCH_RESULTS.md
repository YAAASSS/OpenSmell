# ESP32 LED bench — manual results

Status: **NOT RUN**. Fill in only from a person observing the physical bench.

- Date/operator:
- Source commit:
- Board markings and exact model:
- Host OS / Python / PlatformIO versions:
- Framework and ArduinoJson versions:
- Firmware hash / build log:
- Serial port / baud:
- Wiring checked against BENCH.md:
- LEDs / resistors used:

| Trial | Expected | Observed response and physical result | PASS/FAIL/NOT RUN |
| --- | --- | --- | --- |
| Boot | All LEDs off | | NOT RUN |
| Hello | Expected device identity | | NOT RUN |
| Capabilities | 3 channels, 0–1 intensity, 0.1–30 s | | NOT RUN |
| Channel 0 / GPIO23 | Only LED0, about 5 s | | NOT RUN |
| Channel 1 / GPIO22 | Only LED1, about 5 s | | NOT RUN |
| Channel 2 / GPIO21 | Only LED2, about 5 s | | NOT RUN |
| Semantic plan | LED0/LED1, LED2 off, about 5 s | | NOT RUN |
| Perceptual plan | Three LEDs, about 5 s | | NOT RUN |
| 31 s refusal | invalid_plan, no new activation | | NOT RUN |
| Invalid request during render | Refused, active window preserved | | NOT RUN |
| Hello during render | Reply while window continues | | NOT RUN |
| Oversized frame / recovery | message_too_large then hello | | NOT RUN |

- Measured durations and method:
- Unexpected behavior / exact raw responses:
- Photographs or instrument traces (optional):
- Electrical measurements (if any):
- Odor measurements: **none — LED bench only**.

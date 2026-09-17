![Official OpenSmell logo](images/OpenSmell_Official_Logo_Full.png)

# JavaScript → Python: inspect independently, transfer intact

This **experimental pre-alpha** demonstration uses two applications developed
within OpenSmell. The [JavaScript Graph Reader](../apps/graph_viewer_js/README.md)
reads and inspects the file in the browser. [Local Explorer](../apps/local_demo/README.md)
then imports the downloaded original bytes and calculates plans in Python.
Neither tool is presented as a third-party integration or certification.

## Reproduce the exchange

Run these in separate terminals from the repository root:

```powershell
node apps/graph_viewer_js/server.cjs
.\.venv\Scripts\python.exe -m apps.local_demo
```

The JavaScript reader is at `http://127.0.0.1:8766`; Python Local Explorer is at
`http://127.0.0.1:8765`. The Node server serves static assets only. Choose files
explicitly; no dataset is uploaded to either a remote service or the Node server.

1. In the reader, click **Open graph file** and choose
   `examples/multisource_diphenyl_ether.osmell` (or the beta-pinene fixture).
2. Review molecular identity, the two separate source branches, all category
   states/measurements, known reference links and declared provenance. Inspect
   the exact list of checks and any diagnostics.
3. Download the intact `.osmell` copy and separate inspection JSON report.
4. Compare the SHA-256 of the original file, the downloaded copy and the report:

   ```powershell
   Get-FileHash examples/multisource_diphenyl_ether.osmell -Algorithm SHA256
   Get-FileHash "$env:USERPROFILE\Downloads\multisource_diphenyl_ether-transfer.osmell" -Algorithm SHA256
   ```

5. In Local Explorer, use **Import graph** to select that downloaded copy. Set
   **Plan duration** to **5**, recalculate and switch between both policies.
   The inspection report is a separate artifact and is not a graph to import.

Matching hashes establish byte identity, not interpretation correctness. The
separate tests compare JavaScript's parsed identity, categories, values,
references and provenance with independent source expectations and Python.
No graph is reconstructed with `JSON.stringify` for this transfer.

## Independently expected plans

| Input | Policy | CH0 | CH1 | CH2 | Duration |
| --- | --- | --- | --- | --- | --- |
| Beta-pinene | Semantic | **Omitted** | 0.60 | 1.00 | 5 s |
| Beta-pinene | Perceptual | 0.01 | 0.86 | 0.97 | 5 s |
| Diphenyl ether | Semantic | 0.25 | 0.60 | **Omitted** | 5 s |
| Diphenyl ether | Perceptual | 0.47 | 0.18 | 0.15 | 5 s |

The bindings and Python mappers are unchanged. Semantic uses the existing fixed
levels for present categories; Perceptual uses `(value - min) / (max - min)`.
The selected FLOWER/GRASS/WOOD source values are 1/86/97 and 47/18/15 on explicit
0–100 scales. An omitted command is not a command with numeric intensity zero.
These are command values, not measured brightness or reproduced odors.

## Verification actually performed

On 17 September 2026, **1,931 Python tests passed**, including **167 targeted
tests** and the four new JS/Python exchange cases. **33 new JavaScript reader
tests** and the **8 existing JavaScript import tests** passed. Existing portable
interoperability checks were also run; the required CI workflow now includes
the reader and exchange tests. The earlier 1,927/163 results belong to the
second-example implementation and remain historical.

Local versions: Python 3.13.14, Node.js 24.19.0. No new dependency was installed.
Tests preserve the old fixtures and verifiers. Automated exchange tests use
isolated loopback Python servers with serial factory/enumeration disabled.
DOM-double tests and real-browser checks are distinct evidence.

### Real-browser exchange

A real Codex in-app browser opened **both** real files in the JavaScript reader,
downloaded each original-byte copy and separate report, and imported each copy
into an isolated Python Local Explorer. Both policies produced the expected
5-second plans. Byte-for-byte comparisons and SHA-256 checks passed for each
actual browser download:

| Input/download | Bytes on this Windows checkout | SHA-256 of original and downloaded copy |
| --- | --- | --- |
| Beta-pinene | 7,607 | `e87ca2c9f3a5f3eb983d0d5b55b9aef783e8e25c47b206719c6013b2ee0c9d85` |
| Diphenyl ether | 11,413 | `453c5577d7d90597efa201ab0d3f41d59f761bd036f5e0e89f4a677fccd248d8` |

Checkout line-ending conversion can change an original file's byte hash. Always
compare the copy to the exact original bytes selected on that machine, rather
than requiring these recorded Windows hashes on every platform.

The browser also exercised Core-format rejection, duplicate-resource-ID
rejection, invalid UTF-8, disabled copy actions after rejection, recovery with a
valid file and structural-reference navigation. Both consoles had no errors.
The Python server used for verification had serial access forcibly unavailable;
no physical port was opened and no hardware command was sent.

### Actual screenshots

These are captures of running software on **the same diphenyl ether data**,
not mockups or a hardware simulation presented as real output. They are full-page
JPEGs; use the original images or frame the relevant panels when recording video.

- [JavaScript reader, both source branches](images/js-python-exchange/javascript-diphenyl-ether.jpg)
- [Python Local Explorer, downloaded file / Semantic](images/js-python-exchange/python-diphenyl-ether-semantic.jpg)
- [Python Local Explorer, downloaded file / Perceptual](images/js-python-exchange/python-diphenyl-ether-perceptual.jpg)

The Python hardware panel reports unavailable because the isolated verification
server disabled optional serial access. Its installation hint is not a diagnosis
of the user's normal environment. The drawn LED levels remain previews.

## A filmable 40-second sequence

| Time | Action and framing | Suggested narration |
| --- | --- | --- |
| 0–7 s | Open diphenyl ether in JavaScript; show identity, byte count and hash | “This reader understands a limited OpenSmell profile in JavaScript.” |
| 7–16 s | Frame OdorNet and Keller/Vosshall side by side; show unknown states and familiarity zero | “The categories and the measured ratings keep their own sources and meaning.” |
| 16–23 s | Download the intact file and the separate report; show matching file hashes | “The transfer keeps every original byte, including content the reader does not interpret.” |
| 23–32 s | Import the downloaded `.osmell` in Python Local Explorer | “The same file is now read by the Python application.” |
| 32–40 s | Switch Semantic / Perceptual at 5 s, frame both planned-command rows | “Two unchanged mapping policies produce different plans. These are previews, not odor reproduction.” |

Use “independent JavaScript analysis within the OpenSmell project,” not
“independent third-party certification.” Do not call original-byte copying a
generic lossless JSON edit. The reader's inspection report is not a new standard.
No hardware execution needs to appear in this software sequence.

This outline and the screenshots are preparation material. They are **not two
completed 120-second video edits**. Paid production of the two videos and any
InVideo spending remain paused pending review of the draft edits.

## Separate user LED trial — pending for this transferred-file workflow

Earlier user confirmations cover the original beta-pinene and diphenyl ether
application trials. They do **not** prove that the new JavaScript-download →
Python-import → ESP32 path has already been physically tried.

1. Perform the exchange above, using the actual downloaded copy. Check its hash
   against the selected original and confirm the identity in Local Explorer.
2. In the user's normal Local Explorer, connect the reference ESP32 explicitly
   and review received capabilities. Choose Semantic at 5 s and verify the table
   above before clicking **Send to device** once.
3. Observe the LED behavior. Wait for the local estimated window **and observe
   actual LED extinction** before selecting Perceptual at 5 s and sending once.
4. Record the two observed results separately, identifying the transferred file.
   After extinction, Disconnect releases the port.

An accepted command does not confirm completion. There is no completion
telemetry, time remaining is estimated and Disconnect does not stop an accepted
command. This is a future user LED check, not an agent-performed test and not
an odor-reproduction experiment. No new 31-second refusal test is claimed.

## RFC relationship

[RFC-0008](../rfcs/RFC-0008.md) governs the generic graph envelope/opaque types,
[RFC-0009](../rfcs/RFC-0009.md) and [RFC-0010](../rfcs/RFC-0010.md) the molecule
and annotation types, and [RFC-0011](../rfcs/RFC-0011.md) structural references.
The legacy resources and independent source branches follow
[RFC-0007](../rfcs/RFC-0007.md) and [RFC-0013](../rfcs/RFC-0013.md).
Existing rendering contracts and mappers remain as described in
[RFC-0012](../rfcs/RFC-0012.md).

Only RFC-0013 implementation evidence is extended. No new RFC is needed:
the app adds a bounded reader and transfer workflow, not a new interoperability
contract. Its reading limits and report format are application choices.
All RFC statuses remain Draft; the SDK, firmware, scientific files and policies
are unchanged.

![Official OpenSmell symbol](images/OpenSmell_Official_Logo_Small.png)

"""Export a multi-source (-)-beta-pinene OpenSmell GenericResourceGraph.

This example combines two independent datasets around one shared molecular
resource:

- OdorNet:
    complete categorical semantic annotation using the experimental
    RFC-0004 semantic annotation scheme;

- Keller/Vosshall:
    one stimulus, one observation target, and one subject-specific
    psychophysical observation.

The datasets are joined only after verifying an exact PubChem InChIKey match.

OdorNet categorical states and Keller quantitative measurements remain
separate. They are not treated as equivalent measurements.

This module is experimental and non-normative.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from opensmell.adapters.keller_vosshall import (
    measurements_from_record,
)
from opensmell.experimental.annotation import (
    register_annotation_resource_type,
)
from opensmell.experimental.generic_graph import (
    GenericResourceGraph,
    create_default_resource_type_registry,
    generic_graph_dumps,
)
from opensmell.experimental.identifiers import (
    deterministic_resource_id_from_source,
)
from opensmell.experimental.molecule import (
    register_molecule_resource_type,
)
from opensmell.experimental.odornet_enriched_adapter import (
    enriched_odornet_record_to_graph,
)
from opensmell.experimental.resources import (
    Condition,
    ExternalIdentifier,
    Observation,
    ObservationTarget,
    Reference,
    Result,
    ResultScheme,
    Stimulus,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KELLER_PATH = (
    PROJECT_ROOT
    / "examples"
    / "keller_vosshall.xlsx"
)

ODORNET_PATH = (
    PROJECT_ROOT
    / "examples"
    / "odornet_enriched.csv"
)

CACHE_PATH = (
    PROJECT_ROOT
    / "examples"
    / "keller_pubchem_identity_cache.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "examples"
    / "multisource_beta_pinene.osmell"
)


TARGET_PUBCHEM_CID = "440967"
TARGET_KELLER_ROW = 46426

KELLER_DATASET_ID = "keller_vosshall"

KELLER_RESULT_SCHEME_ID = (
    "org.opensmell.perceptual.measurements"
)

KELLER_RESULT_SCHEME_VERSION = "0.1"


def clean(value: Any) -> Any:
    """Normalize pandas/numpy scalar and missing values."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass

    return value


def normalized_source_identifier(
    value: Any,
) -> str:
    """Normalize the selected Keller numeric CID."""

    value = clean(value)

    if value is None:
        raise ValueError(
            "Keller CID is missing"
        )

    try:
        return str(
            int(float(value))
        )
    except (TypeError, ValueError):
        return str(value).strip()


def load_keller() -> pd.DataFrame:
    """Load Keller/Vosshall and normalize column names."""

    frame = pd.read_excel(
        KELLER_PATH,
        sheet_name="data",
        header=2,
    )

    frame.columns = [
        str(column).strip()
        for column in frame.columns
    ]

    return frame


def load_odornet() -> pd.DataFrame:
    """Load the locally enriched OdorNet dataset."""

    return pd.read_csv(
        ODORNET_PATH
    )


def load_identity_cache() -> dict[str, dict[str, Any]]:
    """Load Keller -> PubChem identity resolution cache."""

    with CACHE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        value = json.load(handle)

    if not isinstance(value, dict):
        raise TypeError(
            "Keller PubChem identity cache "
            "must contain a JSON object"
        )

    return value


def main() -> None:
    print("Loading source datasets...")

    keller = load_keller()
    odornet = load_odornet()
    cache = load_identity_cache()

    # ------------------------------------------------------------
    # Resolve selected Keller chemical identity
    # ------------------------------------------------------------

    cache_key = (
        f"cid:{TARGET_PUBCHEM_CID}"
    )

    identity = cache.get(
        cache_key
    )

    if not isinstance(
        identity,
        dict,
    ):
        raise RuntimeError(
            "Missing Keller PubChem identity "
            f"cache entry: {cache_key}"
        )

    if identity.get("status") != "resolved":
        raise RuntimeError(
            "Selected Keller identity is not "
            "resolved by PubChem"
        )

    inchikey = identity.get(
        "inchikey"
    )

    if (
        not isinstance(inchikey, str)
        or not inchikey.strip()
    ):
        raise RuntimeError(
            "Resolved Keller identity has "
            "no InChIKey"
        )

    inchikey = inchikey.strip()

    print(
        f"PubChem CID: {TARGET_PUBCHEM_CID}"
    )
    print(
        f"InChIKey: {inchikey}"
    )

    # ------------------------------------------------------------
    # Locate exact OdorNet molecule
    # ------------------------------------------------------------

    odornet_matches = odornet[
        odornet["PubChem_InChIKey"]
        == inchikey
    ]

    if len(odornet_matches) != 1:
        raise RuntimeError(
            "Expected exactly one OdorNet "
            f"record for InChIKey {inchikey}; "
            f"found {len(odornet_matches)}"
        )

    odornet_index = int(
        odornet_matches.index[0]
    )

    odornet_row = (
        odornet_matches.iloc[0]
    )

    odornet_record = (
        odornet_row.to_dict()
    )

    odornet_title = clean(
        odornet_row.get(
            "PubChem_Title"
        )
    )

    print()
    print("OdorNet:")
    print(
        f"  row: {odornet_index}"
    )
    print(
        f"  title: {odornet_title}"
    )

    # ------------------------------------------------------------
    # Existing enriched OdorNet adapter
    # ------------------------------------------------------------

    odornet_result = (
        enriched_odornet_record_to_graph(
            odornet_record
        )
    )

    molecule_id = (
        odornet_result.molecule_id
    )

    annotation_id = (
        odornet_result.annotation_id
    )

    molecule = (
        odornet_result.graph.require(
            molecule_id
        )
    )

    annotation = (
        odornet_result.graph.require(
            annotation_id
        )
    )

    # ------------------------------------------------------------
    # Verify exact OdorNet identity
    # ------------------------------------------------------------

    molecule_inchikeys = [
        identifier.value
        for identifier
        in molecule.identifiers
        if identifier.scheme
        == "pubchem.inchikey"
    ]

    if inchikey not in molecule_inchikeys:
        raise RuntimeError(
            "OdorNet Molecule does not contain "
            "the expected PubChem InChIKey"
        )

    print(
        "  OpenSmell Molecule: "
        f"{molecule_id}"
    )
    print(
        "  OpenSmell Annotation: "
        f"{annotation_id}"
    )

    # ------------------------------------------------------------
    # Display selected OdorNet semantic states
    # ------------------------------------------------------------

    semantic_states: dict[
        str,
        str,
    ] = {}

    annotations = (
        annotation.data.get(
            "annotations"
        )
    )

    if not isinstance(
        annotations,
        list,
    ):
        raise RuntimeError(
            "OdorNet Annotation does not "
            "contain an annotations list"
        )

    for item in annotations:
        if not isinstance(
            item,
            dict,
        ):
            continue

        descriptor = item.get(
            "value"
        )

        state = item.get(
            "state"
        )

        if (
            isinstance(descriptor, str)
            and isinstance(state, str)
        ):
            semantic_states[
                descriptor
            ] = state

    print(
        "  floral: "
        f"{semantic_states.get('floral')}"
    )
    print(
        "  green&herbal: "
        f"{semantic_states.get('green&herbal')}"
    )
    print(
        "  woody&mossy: "
        f"{semantic_states.get('woody&mossy')}"
    )

    # ------------------------------------------------------------
    # Keller selected observation
    # ------------------------------------------------------------

    if TARGET_KELLER_ROW not in keller.index:
        raise RuntimeError(
            "Selected Keller row does not exist: "
            f"{TARGET_KELLER_ROW}"
        )

    keller_row = (
        keller.loc[
            TARGET_KELLER_ROW
        ]
    )

    keller_cid = (
        normalized_source_identifier(
            keller_row["CID"]
        )
    )

    if (
        keller_cid
        != TARGET_PUBCHEM_CID
    ):
        raise RuntimeError(
            "Selected Keller row has CID "
            f"{keller_cid}, expected "
            f"{TARGET_PUBCHEM_CID}"
        )

    keller_name = clean(
        keller_row["Odor"]
    )

    keller_cas = clean(
        keller_row["C.A.S."]
    )

    dilution = clean(
        keller_row["Odor dilution"]
    )

    subject = clean(
        keller_row[
            "Subject # (this study)"
        ]
    )

    # IMPORTANT:
    # Reuse the existing Keller/Vosshall adapter instead of
    # manually inventing the perceptual measurement structure.
    keller_record = (
        keller_row.to_dict()
    )

    perceptual_measurements = (
        measurements_from_record(
            keller_record
        )
    )

    if not perceptual_measurements:
        raise RuntimeError(
            "Selected Keller observation "
            "contains no perceptual measurements"
        )

    measurements_by_property = {
        item["property"]: item
        for item in perceptual_measurements
    }

    for required_property in (
        "flower",
        "grass",
        "wood",
    ):
        if (
            required_property
            not in measurements_by_property
        ):
            raise RuntimeError(
                "Selected Keller observation "
                "does not contain "
                f"{required_property!r}"
            )

    flower = (
        measurements_by_property[
            "flower"
        ]
    )
    grass = (
        measurements_by_property[
            "grass"
        ]
    )
    wood = (
        measurements_by_property[
            "wood"
        ]
    )

    print()
    print("Keller/Vosshall:")
    print(
        f"  row: {TARGET_KELLER_ROW}"
    )
    print(
        f"  name: {keller_name}"
    )
    print(
        f"  CAS: {keller_cas}"
    )
    print(
        f"  dilution: {dilution}"
    )
    print(
        f"  subject: {subject}"
    )
    print(
        "  FLOWER/GRASS/WOOD: "
        f"{flower['value']}/"
        f"{grass['value']}/"
        f"{wood['value']}"
    )
    print(
        "  perceptual measurements: "
        f"{len(perceptual_measurements)}"
    )

    # ------------------------------------------------------------
    # Deterministic Keller resource IDs
    # ------------------------------------------------------------

    stimulus_id = (
        deterministic_resource_id_from_source(
            dataset=KELLER_DATASET_ID,
            resource_type="stimulus",
            source_identity={
                "inchikey": inchikey,
                "cas": str(
                    keller_cas
                ),
                "dilution": str(
                    dilution
                ),
            },
        )
    )

    target_id = (
        deterministic_resource_id_from_source(
            dataset=KELLER_DATASET_ID,
            resource_type=(
                "observation_target"
            ),
            source_identity={
                "subject": str(
                    subject
                ),
            },
        )
    )

    observation_id = (
        deterministic_resource_id_from_source(
            dataset=KELLER_DATASET_ID,
            resource_type="observation",
            source_identity={
                "row": str(
                    TARGET_KELLER_ROW
                ),
            },
        )
    )

    # ------------------------------------------------------------
    # Keller Stimulus -> shared Molecule
    # ------------------------------------------------------------

    stimulus_conditions: list[
        Condition
    ] = []

    if dilution is not None:
        stimulus_conditions.append(
            Condition(
                property="dilution",
                value=str(
                    dilution
                ),
            )
        )

    stimulus_identifiers: list[
        ExternalIdentifier
    ] = []

    if keller_cas is not None:
        stimulus_identifiers.append(
            ExternalIdentifier(
                scheme="cas",
                value=str(
                    keller_cas
                ),
            )
        )

    stimulus = Stimulus(
        id=stimulus_id,
        source=Reference(
            resource_id=molecule_id
        ),
        identifiers=(
            stimulus_identifiers
        ),
        conditions=(
            stimulus_conditions
        ),
        extra={
            "provenance": {
                "source": (
                    "Keller/Vosshall"
                ),
            },
            "source_label": (
                keller_name
            ),
            "source_pubchem_cid": (
                TARGET_PUBCHEM_CID
            ),
            "identity_match": {
                "method": (
                    "exact_pubchem_inchikey"
                ),
                "inchikey": (
                    inchikey
                ),
            },
        },
    )

    # ------------------------------------------------------------
    # Keller observation target
    # ------------------------------------------------------------

    target = ObservationTarget(
        id=target_id,
        identifiers=[
            ExternalIdentifier(
                scheme=(
                    "keller_vosshall."
                    "subject_this_study"
                ),
                value=str(
                    subject
                ),
            )
        ],
        extra={
            "kind": (
                "human_subject"
            ),
            "provenance": {
                "source": (
                    "Keller/Vosshall"
                ),
            },
        },
    )

    # ------------------------------------------------------------
    # Keller quantitative perceptual Result
    # ------------------------------------------------------------

    perceptual_result = Result(
        scheme=ResultScheme(
            id=(
                KELLER_RESULT_SCHEME_ID
            ),
            version=(
                KELLER_RESULT_SCHEME_VERSION
            ),
        ),
        data={
            "measurements": (
                perceptual_measurements
            ),
        },
        extra={
            "provenance": {
                "source": (
                    "Keller/Vosshall"
                ),
            }
        },
    )

    # ------------------------------------------------------------
    # Keller Observation
    # ------------------------------------------------------------

    observation = Observation(
        id=observation_id,
        stimulus=Reference(
            resource_id=stimulus_id
        ),
        target=Reference(
            resource_id=target_id
        ),
        results=[
            perceptual_result
        ],
        context={
            "source_dataset": (
                "Keller/Vosshall"
            ),
            "source_row": (
                TARGET_KELLER_ROW
            ),
        },
    )

    # ------------------------------------------------------------
    # Combined GenericResourceGraph
    # ------------------------------------------------------------

    graph = GenericResourceGraph(
        resources=[
            molecule,
            annotation,
            stimulus,
            target,
            observation,
        ],
        extra={
            "example": (
                "OdorNet and Keller/Vosshall "
                "multi-source (-)-beta-pinene"
            ),
            "identity_basis": (
                "exact PubChem InChIKey"
            ),
            "shared_inchikey": (
                inchikey
            ),
        },
    )

    # ------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------

    registry = (
        create_default_resource_type_registry()
    )

    register_molecule_resource_type(
        registry
    )

    register_annotation_resource_type(
        registry
    )

    # ------------------------------------------------------------
    # Serialize
    # ------------------------------------------------------------

    serialized = generic_graph_dumps(
        graph,
        registry=registry,
        indent=2,
    )

    OUTPUT_PATH.write_text(
        serialized + "\n",
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    print()
    print(
        "=== OpenSmell multi-source graph ==="
    )
    print(
        f"Molecule:           {molecule_id}"
    )
    print(
        f"OdorNet annotation: {annotation_id}"
    )
    print(
        f"Keller stimulus:    {stimulus_id}"
    )
    print(
        f"Keller target:      {target_id}"
    )
    print(
        f"Keller observation: {observation_id}"
    )

    print()
    print(
        f"Resources: {len(graph)}"
    )
    print(
        "Identity link: exact PubChem InChIKey"
    )
    print(
        "OdorNet semantics: RFC-0004 states"
    )
    print(
        "Keller semantics: quantitative "
        "psychophysical measurements"
    )

    print()
    print(
        f"Written: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
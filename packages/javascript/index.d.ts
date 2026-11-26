/** Limited experimental graph and explicit Core profiles; not full schema validation. */
export const LIMIT: 1048576;
export const CORE_LIMIT: 4194304;
export const FORMAT: "org.opensmell.experimental.generic-resource-graph";
export type ResourceKind = "molecule" | "annotation" | "stimulus" | "observation_target" | "observation" | "opaque";
/** Display text retains numeric tokens; it is not a normalized numeric value. */
export type DisplayField = {presence: "missing" | "null"; text: string} |
                           {presence: "value"; text: string | null; json: string | null};
export interface InspectionReport {
  tool: string;
  report_version: string;
  status: "inspected" | "partial" | "rejected";
  file: {name: string; byte_length: number; sha256: string; utf8_bom: boolean};
  format?: DisplayField;
  version?: DisplayField;
  core?: {version: DisplayField; odor_id: string; metadata: DisplayField; provenance: DisplayField;
    odor_provenance: DisplayField; representations: Array<{index: number; type: string; scheme: DisplayField;
      data: DisplayField; provenance: DisplayField; representation_json: string; status: "opaque" | "inspected";
      entries?: Array<{property: string; value: DisplayField; unit: DisplayField; scale: DisplayField;
        min: DisplayField; max: DisplayField}>}>};
  resources: Array<{id: string; type: string; type_version: DisplayField;
                    kind: ResourceKind; status: "recognized" | "opaque" | "invalid"; path: string}>;
  references: Array<{source_id: string; field: string; target_id: string;
                     resolved: boolean; target_kind: ResourceKind | null}>;
  molecules: Array<{id: string; label: DisplayField; smiles: DisplayField;
                    identifiers: Array<{scheme: string; value: string}>; source: SourceDeclaration}>;
  annotations: Array<{id: string; subject: string; source: SourceDeclaration;
                      entries: Array<{value: string; state: "present" | "absent" | "unknown"; language: DisplayField}>}>;
  observations: Array<{id: string; stimulus: string; target: DisplayField; source: SourceDeclaration;
                       groups: Array<{result_index: number; entries: Array<{property: string; value: DisplayField;
                               unit: DisplayField; scale: DisplayField; min: DisplayField; max: DisplayField}>}>}>;
  stimuli: Array<{id: string; source: DisplayField; conditions: DisplayField}>;
  targets: Array<{id: string; identifiers: Array<{scheme: string; value: string}>}>;
  checks: string[];
  limits: string[];
  diagnostics: Array<{severity: string; code: string; path: string; message: string}>;
  [key: string]: unknown;
}
export interface SourceDeclaration {
  name: DisplayField;
  provenance_json: string | null;
  context_json: string | null;
}
export interface InspectionResult {
  report: InspectionReport;
  /** Fresh original bytes; throws if inspection originally rejected the input. */
  copyBytes(): Uint8Array;
}
export function inspectBytes(input: Uint8Array, name?: string): Promise<InspectionResult>;
/** Explicit limited Core 0.1 inspection, no automatic dispatch or planning. */
export function inspectCoreBytes(input: Uint8Array, name?: string): Promise<InspectionResult>;
declare const reader: {LIMIT: typeof LIMIT; CORE_LIMIT: typeof CORE_LIMIT; FORMAT: typeof FORMAT; inspectBytes: typeof inspectBytes; inspectCoreBytes: typeof inspectCoreBytes};
export default reader;

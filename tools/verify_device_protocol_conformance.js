#!/usr/bin/env node
"use strict";

/*
 * Independent JavaScript verifier for experimental Device Protocol 0.1.
 *
 * This verifier checks portable JSON data-model semantics. JSON numeric
 * spellings such as 1 and 1.0 become the same JavaScript Number after
 * JSON.parse(), so lexical distinctions are deliberately not used as
 * cross-language semantic conformance requirements.
 */

const fs = require("fs");
const path = require("path");

const vectorsPath = path.join(
  __dirname,
  "..",
  "examples",
  "device_protocol_conformance_vectors.json"
);

const vectors = JSON.parse(fs.readFileSync(vectorsPath, "utf8"));

function fail(message) {
  throw new Error(message);
}

function object(value, name) {
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    fail(`${name} must be an object`);
  }
  return value;
}

function nonemptyString(value, name) {
  if (typeof value !== "string") fail(`${name} must be a string`);
  if (value.length === 0) fail(`${name} must be non-empty`);
  return value;
}

function finiteNumber(value, name) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    fail(`${name} must be a finite number`);
  }
  return value;
}

function nonnegativeIntegerValue(value, name) {
  if (!Number.isInteger(value) || value < 0) {
    fail(`${name} must be a non-negative integer value`);
  }
  return value;
}

function header(message, expectedType) {
  object(message, "message");
  const version = nonemptyString(message.protocol_version, "protocol_version");
  if (version !== "0.1") fail(`unsupported protocol version: ${version}`);
  const type = nonemptyString(message.type, "type");
  if (type !== expectedType) fail(`expected ${expectedType}, got ${type}`);
}

function validateCapabilities(message) {
  header(message, "capabilities");
  nonemptyString(message.device_id, "device_id");
  if (!Array.isArray(message.channels)) fail("channels must be an array");

  const seen = new Set();
  for (const [index, channel] of message.channels.entries()) {
    object(channel, `channels[${index}]`);
    const number = nonnegativeIntegerValue(
      channel.channel,
      `channels[${index}].channel`
    );
    if (seen.has(number)) fail("duplicate channel");
    seen.add(number);

    const min = finiteNumber(
      channel.min_intensity,
      `channels[${index}].min_intensity`
    );
    const max = finiteNumber(
      channel.max_intensity,
      `channels[${index}].max_intensity`
    );

    if (min < 0 || min > 1 || max < 0 || max > 1 || min > max) {
      fail("invalid intensity range");
    }
  }

  const minDuration = finiteNumber(message.min_duration, "min_duration");
  const maxDuration = finiteNumber(message.max_duration, "max_duration");

  if (minDuration <= 0 || maxDuration <= 0 || minDuration > maxDuration) {
    fail("invalid duration range");
  }
}

function validateRender(message) {
  header(message, "render");

  const duration = finiteNumber(message.duration, "duration");
  if (duration <= 0) fail("duration must be positive");

  if (!Array.isArray(message.commands)) {
    fail("commands must be an array");
  }

  for (const [index, command] of message.commands.entries()) {
    object(command, `commands[${index}]`);

    nonnegativeIntegerValue(
      command.channel,
      `commands[${index}].channel`
    );

    const intensity = finiteNumber(
      command.intensity,
      `commands[${index}].intensity`
    );

    if (intensity < 0 || intensity > 1) {
      fail("intensity out of range");
    }
  }
}

function validate(kind, message) {
  if (kind === "hello_request") {
    return header(message, "hello");
  }

  if (kind === "capabilities_request") {
    return header(message, "get_capabilities");
  }

  if (kind === "hello_response") {
    header(message, "hello_response");
    nonemptyString(message.device_id, "device_id");
    return;
  }

  if (kind === "capabilities_response") {
    return validateCapabilities(message);
  }

  if (kind === "render_request") {
    return validateRender(message);
  }

  if (kind === "ok_response") {
    return header(message, "ok");
  }

  if (kind === "error_response") {
    header(message, "error");
    nonemptyString(message.code, "code");
    nonemptyString(message.message, "message");
    return;
  }

  fail(`unknown vector kind: ${kind}`);
}

let passed = 0;
let failed = 0;

for (const vector of vectors.valid) {
  try {
    validate(vector.kind, vector.message);
    console.log(`PASS valid ${vector.id}`);
    passed += 1;
  } catch (error) {
    console.error(`FAIL valid ${vector.id}: ${error.message}`);
    failed += 1;
  }
}

for (const vector of vectors.invalid) {
  try {
    validate(vector.kind, vector.message);
    console.error(`FAIL invalid ${vector.id}: accepted`);
    failed += 1;
  } catch (_) {
    console.log(`PASS invalid ${vector.id}`);
    passed += 1;
  }
}

for (const vector of vectors.strict_json_invalid_text) {
  try {
    const parsed = JSON.parse(vector.text);
    object(parsed, "message");
    console.error(`FAIL strict-json ${vector.id}: accepted`);
    failed += 1;
  } catch (_) {
    console.log(`PASS strict-json ${vector.id}`);
    passed += 1;
  }
}

/*
 * Lexical vectors document distinctions that are intentionally outside the
 * portable semantic suite. They are not counted as pass/fail conformance
 * vectors because JSON.parse() erases the relevant lexical distinction.
 */
for (const vector of vectors.lexical_json || []) {
  console.log(`INFO lexical ${vector.id}: not a portable semantic requirement`);
}

console.log(
  `Device Protocol 0.1 portable conformance: ${passed} passed, ${failed} failed`
);

if (failed !== 0) {
  process.exit(1);
}

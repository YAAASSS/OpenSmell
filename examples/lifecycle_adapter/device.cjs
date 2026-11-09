#!/usr/bin/env node
'use strict';
// Independent software device: no OpenSmell library imports, no physical output.
const readline = require('node:readline');
const {randomUUID} = require('node:crypto');
const {performance} = require('node:perf_hooks');
const profile = 'local-simulator-lifecycle-v1';
const errorProfile = 'local-simulator-errors-v1';
function reject(code, message) { throw Object.assign(new Error(message), {code}); }
const deviceId = 'opensmell-node-simulator-001';
let execution = null;
let deadline = 0;
function advance() {
  if (execution?.state === 'running' && performance.now() >= deadline) execution.state = 'completed';
}
function handle(m) {
  if (!m || typeof m !== 'object' || Array.isArray(m)) throw Error('Object required');
  if (typeof m.type !== 'string' || !m.type) throw Error('Request type required');
  if (['hello', 'get_capabilities', 'render'].includes(m.type) && m.protocol_version !== '0.1') throw Error('Unsupported protocol');
  if (m.type === 'hello') return {protocol_version:'0.1', type:'hello_response', device_id:deviceId};
  if (m.type === 'get_capabilities') return {protocol_version:'0.1', type:'capabilities', device_id:deviceId,
    channels:[0,1,2].map(channel => ({channel, min_intensity:0, max_intensity:1})), min_duration:0.1, max_duration:30};
  if (m.type === 'lifecycle_capabilities') return {profile, status:true, stop:true, errors:errorProfile};
  if (m.type === 'render') {
    advance();
    if (execution?.state === 'running') reject('busy', 'Execution already running');
    if (typeof m.duration !== 'number' || !Number.isFinite(m.duration) || m.duration < 0.1 || m.duration > 30) throw Error('Invalid duration');
    if (!Array.isArray(m.commands) || m.commands.length === 0 || m.commands.length > 3) throw Error('Invalid commands');
    const seen = new Set();
    for (const c of m.commands) {
      if (!c || !Number.isInteger(c.channel) || c.channel < 0 || c.channel > 2 || seen.has(c.channel)
          || typeof c.intensity !== 'number' || !Number.isFinite(c.intensity) || c.intensity < 0 || c.intensity > 1) throw Error('Invalid channel or intensity');
      seen.add(c.channel);
    }
    execution = {execution_id:randomUUID(), state:'running'};
    deadline = performance.now() + m.duration * 1000;
    return {protocol_version:'0.1', type:'ok', execution_id:execution.execution_id};
  }
  if (m.type === 'execution_status' || m.type === 'stop') {
    if (m.profile !== profile) reject('unsupported_profile', 'Unsupported lifecycle profile');
    if (!execution || m.execution_id !== execution.execution_id) reject('unknown_execution', 'Unknown execution identifier');
    advance();
    if (m.type === 'stop' && execution.state === 'running') execution.state = 'stopped';
    return {profile, ...execution};
  }
  reject('unsupported_request', 'Unsupported request');
}
const input = readline.createInterface({input:process.stdin, crlfDelay:Infinity});
input.on('line', line => {
  let reply, request;
  try {
    if (Buffer.byteLength(line, 'utf8') > 65536) throw Error('Request too large');
    request = JSON.parse(line);
    reply = handle(request);
  } catch (error) {
    reply = {protocol_version:'0.1', type:'error', code:error.code || 'invalid_request', message:error.message, error_profile:errorProfile};
    for (const field of ['type', 'execution_id']) {
      const value = request?.[field];
      if (typeof value === 'string' && value.length > 0 && Array.from(value).length <= 128)
        reply[field === 'type' ? 'request_type' : field] = value;
    }
  }
  process.stdout.write(JSON.stringify(reply) + '\n');
});

'use strict';
const {spawn} = require('node:child_process');
const PROFILE = 'local-simulator-lifecycle-v1';
const ERRORS = 'local-simulator-errors-v1';
const clone = value => structuredClone(value);
function requireValue(ok, message) { if (!ok) throw new Error(message); }
const text = v => typeof v === 'string' && v.trim().length > 0 && Array.from(v).length <= 128;
const number = v => typeof v === 'number' && Number.isFinite(v);
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);

/** Trusted software subprocess only. One bounded JSON line per exchange; no retries. */
class ProcessTransport {
  constructor(command, {timeout = 2000, startupTimeout = 5000} = {}) {
    requireValue(Array.isArray(command) && command.length && command.every(x => typeof x === 'string') && command[0], 'Explicit command array required');
    requireValue(number(timeout) && timeout > 0 && number(startupTimeout) && startupTimeout > 0, 'Positive millisecond deadlines required');
    this.closed = false; this.pending = null; this.buffer = Buffer.alloc(0); this.first = true;
    this.timeout = timeout; this.startupTimeout = startupTimeout;
    this.child = spawn(command[0], command.slice(1), {stdio:['pipe','pipe','ignore'], shell:false});
    this.child.on('error', e => this.fail(e));
    this.child.on('exit', () => this.fail(new Error('Endpoint exited')));
    this.child.stdin.on('error', e => this.fail(e));
    this.child.stdout.on('data', data => {
      if (this.closed) return;
      this.buffer = Buffer.concat([this.buffer, data]);
      const end = this.buffer.indexOf(10);
      if ((end < 0 && this.buffer.length > 65536) || end > 65536) return this.fail(new Error('Reply exceeds 65536 bytes'));
      if (end < 0) return;
      if (!this.pending || end !== this.buffer.length - 1) return this.fail(new Error('Unsolicited or multiple replies'));
      try {
        const reply = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(this.buffer.subarray(0,end)));
        requireValue(object(reply), 'Reply must be an object');
        this.buffer = Buffer.alloc(0);
        const pending = this.pending; this.pending = null; clearTimeout(pending.timer);
        this.first = false; pending.resolve(reply);
      } catch (error) { this.fail(error); }
    });
  }
  exchange(request) {
    if (this.closed) return Promise.reject(new Error('Transport closed'));
    if (this.pending) return Promise.reject(new Error('Concurrent transport exchange'));
    const data = JSON.stringify(request);
    if (Buffer.byteLength(data) > 65536) return Promise.reject(new Error('Request too large'));
    return new Promise((resolve,reject) => {
      const timer = setTimeout(() => this.fail(new Error(this.first ? 'Startup response timeout' : 'Response timeout')), this.first ? this.startupTimeout : this.timeout);
      this.pending = {resolve,reject,timer};
      this.child.stdin.write(data + '\n');
    });
  }
  fail(error) {
    if (this.closed) return;
    this.closed = true;
    if (this.pending) { clearTimeout(this.pending.timer); this.pending.reject(error); this.pending = null; }
    this.buffer = Buffer.alloc(0); this.child.stdin.destroy(); this.child.stdout.destroy(); this.child.kill();
  }
  close() { this.fail(new Error('Link closed')); }
}

class LifecycleClient {
  #transport; #closed; #current; #used; #ids; #queue; #caps; #deviceId;

  constructor(transport) {
    this.#transport = transport; this.#closed = false; this.#current = null;
    this.#used = new Set(); this.#ids = new Set(); this.#queue = Promise.resolve();
  }
  static async connect(transport, {expectedDeviceId} = {}) {
    const c = new LifecycleClient(transport);
    try {
      requireValue(text(expectedDeviceId), 'Expected device ID required');
      const hello = await c.exchange({protocol_version:'0.1',type:'hello'});
      requireValue(hello.protocol_version === '0.1' && hello.type === 'hello_response' && hello.device_id === expectedDeviceId, 'Unexpected device identity or protocol');
      const caps = await c.exchange({protocol_version:'0.1',type:'get_capabilities'});
      requireValue(caps.protocol_version === '0.1' && caps.type === 'capabilities' && caps.device_id === expectedDeviceId, 'Capabilities identity mismatch');
      requireValue(Array.isArray(caps.channels) && caps.channels.length > 0 && number(caps.min_duration) && caps.min_duration >= 0 && number(caps.max_duration) && caps.max_duration >= caps.min_duration, 'Invalid capabilities');
      const channels = new Set();
      for (const ch of caps.channels) {
        requireValue(object(ch) && Number.isSafeInteger(ch.channel) && ch.channel >= 0 && !channels.has(ch.channel) && number(ch.min_intensity) && number(ch.max_intensity) && ch.min_intensity >= 0 && ch.max_intensity <= 1 && ch.min_intensity <= ch.max_intensity, 'Invalid channel capabilities');
        channels.add(ch.channel);
      }
      c.#caps = clone(caps); c.#deviceId = expectedDeviceId;
      const life = await c.exchange({type:'lifecycle_capabilities'});
      requireValue(life.profile === PROFILE && life.status === true && life.stop === true && (life.errors ?? ERRORS) === ERRORS, 'Unsupported lifecycle profile');
      return c;
    } catch (error) { c.close(); throw error; }
  }
  async exchange(request) {
    requireValue(!this.#closed, 'Session closed');
    const reply = await this.#transport.exchange(request);
    requireValue(!this.#closed && !this.#transport.closed && object(reply), 'Link closed or invalid reply');
    return reply;
  }
  get deviceId() { return this.#deviceId; }
  get capabilities() { return clone(this.#caps); }
  get execution() {
    if (this.#transport.closed && !this.#closed) this.close();
    return clone(this.#current);
  }
  serial(operation) {
    const result = this.#queue.then(operation);
    this.#queue = result.catch(() => {});
    return result;
  }
  render(plan, {requestId} = {}) {
    const snapshot = clone(plan);
    return this.serial(async () => {
      requireValue(!this.#closed, 'Session closed');
      requireValue(text(requestId) && !this.#used.has(requestId), 'Invalid or consumed request ID');
      requireValue(!this.#current || !['accepted','running'].includes(this.#current.state), 'Execution active');
      requireValue(object(snapshot) && number(snapshot.duration) && snapshot.duration > 0 && snapshot.duration >= this.#caps.min_duration && snapshot.duration <= this.#caps.max_duration, 'Invalid duration');
      requireValue(Array.isArray(snapshot.commands) && snapshot.commands.length > 0, 'Nonempty commands required');
      const seen = new Set();
      const commands = snapshot.commands.map(cmd => {
        const channel = this.#caps.channels.find(ch => ch.channel === cmd?.channel);
        requireValue(object(cmd) && channel && !seen.has(cmd.channel) && number(cmd.intensity) && cmd.intensity >= channel.min_intensity && cmd.intensity <= channel.max_intensity, 'Invalid or duplicate channel/intensity');
        seen.add(cmd.channel); return {channel:cmd.channel,intensity:cmd.intensity};
      });
      this.#used.add(requestId); this.#current = {request_id:requestId,execution_id:null,state:'unknown'};
      try {
        const reply = await this.exchange({protocol_version:'0.1',type:'render',duration:snapshot.duration,commands});
        requireValue(reply.protocol_version === '0.1', 'Invalid protocol');
        if (reply.type === 'error') {
          requireValue(text(reply.code) && typeof reply.message === 'string' && reply.message.length > 0 && (reply.error_profile === undefined || reply.error_profile === ERRORS) && (reply.request_type === undefined || reply.request_type === 'render'), 'Invalid refusal');
          this.#current = {...this.#current,state:'rejected',response:clone(reply)};
        } else {
          requireValue(reply.type === 'ok' && text(reply.execution_id) && !this.#ids.has(reply.execution_id), 'Missing or reused execution ID');
          this.#ids.add(reply.execution_id);
          this.#current = {...this.#current,state:'accepted',execution_id:reply.execution_id,response:clone(reply)};
        }
      } catch (error) { this.#current.detail = error.message; this.close(); }
      return this.execution;
    });
  }
  observe(action, id) {
    return this.serial(async () => {
      requireValue(this.#current && id && id === this.#current.execution_id, 'Stale or unknown execution ID');
      if (!['accepted','running'].includes(this.#current.state)) return this.execution;
      try {
        const reply = await this.exchange({type:action,profile:PROFILE,execution_id:id});
        requireValue(reply.profile === PROFILE && reply.execution_id === id && ['running','completed','stopped'].includes(reply.state), 'Mismatched execution observation');
        this.#current = {...this.#current,state:reply.state,observation:clone(reply)};
      } catch (error) { this.#current = {...this.#current,state:'unknown',detail:error.message}; this.close(); }
      return this.execution;
    });
  }
  status(id) { return this.observe('execution_status',id); }
  stop(id) { return this.observe('stop',id); }
  close() {
    if (this.#closed) return;
    this.#closed = true;
    if (this.#current && ['accepted','running'].includes(this.#current.state)) this.#current = {...this.#current,state:'unknown',detail:'Link closed before terminal confirmation'};
    try { this.#transport.close(); } catch {}
  }
}
module.exports = {LifecycleClient,ProcessTransport,PROFILE};

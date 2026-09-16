"use strict";

// All hardware mutations are explicit POSTs. Polls only read server state.
const hardware = {
  ticket: null, state: null, ready: false, pending: false, polling: false,

  async request(path, payload) {
    const response = await fetch(path, payload === undefined ? {} : {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      if (result.hardware) this.render(result.hardware);
      throw new Error(result.error || "Hardware request failed.");
    }
    return result;
  },

  clearPreview() {
    this.ticket = null;
    this.ready = false;
    $("#send-readiness").textContent = "Calculate a fresh preview before sending.";
    this.buttons();
  },

  setPreview(ticket) {
    this.ticket = ticket;
    this.ready = false;
    this.check();
  },

  buttons() {
    const state = this.state;
    const busy = this.pending || state?.operation_pending || state?.connection === "connecting";
    $("#send-device").disabled = !this.ticket || !this.ready || busy || state?.connection !== "connected";
    $("#connect-device").disabled = busy || !state?.available || state?.connection === "connected";
    $("#disconnect-device").disabled = busy || state?.connection !== "connected";
    $("#serial-port").disabled = busy || state?.connection === "connected";
    $("#refresh-ports").disabled = busy || !state?.available;
  },

  render(state) {
    this.state = state;
    if (state.connection === "connected" && state.port) $("#serial-port").value = state.port;
    $("#connection-state").textContent = !state.available ? "Hardware unavailable" :
      ({disconnected: "Disconnected", connecting: "Connecting", connected: "Connected"}[state.connection]);
    $("#hardware-message").textContent = state.message;
    $("#simulation-note").hidden = !state.simulated;
    $("#device-info").hidden = !state.capabilities;
    if (state.capabilities) {
      const identity = $("#device-identity");
      identity.replaceChildren();
      field(identity, "Device ID", state.device_id);
      field(identity, "Port", state.port);
      field(identity, "Duration", `${state.capabilities.min_duration}–${state.capabilities.max_duration} s`);
      field(identity, "Channels", state.capabilities.channels.map((item) => `${item.channel}: ${item.min_intensity}–${item.max_intensity}`).join("; "));
      $("#device-capabilities").textContent = JSON.stringify(state.capabilities, null, 2);
    }
    const execution = state.execution;
    $("#execution-info").hidden = !execution;
    if (execution) {
      $("#execution-duration").textContent = `Submitted plan duration: ${number.format(execution.duration)} s.`;
      $("#execution-heading").textContent = {sending: "Sending…", accepted: "Command accepted",
        rejected: "Command rejected", uncertain: "Execution uncertain"}[execution.state];
      const remaining = state.remaining_seconds;
      $("#execution-estimate").textContent = remaining > 0 ?
        `Estimated wait: ${Math.ceil(remaining)} s. Local estimate only; no device completion signal.` :
        execution.state === "accepted" ? "Estimated duration elapsed. Completion has not been confirmed by the device." :
        execution.state === "uncertain" ? "The command may have run. Check the LEDs before reconnecting or sending again." :
        execution.state === "rejected" ? "The device returned an error. No automatic retry." : "Waiting for a device response…";
      $("#execution-response").textContent = execution.response ? JSON.stringify(execution.response, null, 2) :
        execution.detail || "No response received yet.";
    }
    this.buttons();
  },

  async check() {
    const ticket = this.ticket;
    if (!ticket || this.pending) return;
    this.ready = false;
    this.buttons();
    if (this.state && !this.state.available) {
      $("#send-readiness").textContent = "Hardware unavailable. Preview remains available.";
      return;
    }
    try {
      const result = await this.request("/api/hardware/check", ticket);
      if (this.ticket !== ticket || this.pending) return;
      this.ready = result.ready;
      $("#send-readiness").textContent = result.message;
    } catch (error) {
      if (this.ticket !== ticket || this.pending) return;
      $("#send-readiness").textContent = error.message;
    }
    this.buttons();
  },

  async refresh() {
    if (this.polling || this.pending) return;
    this.polling = true;
    try {
      const state = await this.request("/api/hardware/status");
      if (!this.pending) { this.render(state); await this.check(); }
    } catch (_) {
      this.ready = false;
      $("#hardware-message").textContent = "Cannot reach the local server. Connection and execution state are unknown. No automatic reconnect or resend.";
      $("#connection-state").textContent = "Connection unknown";
      this.buttons();
    } finally {
      this.polling = false;
    }
  },

  async action(action) {
    if (this.pending) return;
    if (action === "send" && (!this.ready || !this.ticket)) return;
    const ticket = this.ticket;
    this.pending = true;
    this.ready = false;
    $("#hardware-error").hidden = true;
    if (action === "connect") $("#connection-state").textContent = "Connecting";
    if (action === "send") {
      this.clearPreview();
      document.querySelectorAll("#load-demo, #import-file, #duration, #duration-form button, #policy-picker input").forEach((item) => { item.disabled = true; });
      $("#send-readiness").textContent = "Sending the displayed plan…";
    }
    this.buttons();
    try {
      const payload = action === "connect" ? {port: $("#serial-port").value} : action === "send" ? ticket : {};
      this.render(await this.request(`/api/hardware/${action}`, payload));
    } catch (error) {
      $("#hardware-error").textContent = error instanceof TypeError ?
        "Request outcome unknown. Check the device and server status. Do not automatically repeat the action." : error.message;
      $("#hardware-error").hidden = false;
    } finally {
      this.pending = false;
      document.querySelectorAll("#load-demo, #import-file, #duration, #duration-form button, #policy-picker input").forEach((item) => { item.disabled = false; });
      if (action === "send") $("#send-readiness").textContent = "Recalculate for a new explicit send.";
      this.buttons();
      await this.refresh();
    }
  },
};

$("#refresh-ports").addEventListener("click", async () => {
  $("#refresh-ports").disabled = true;
  $("#port-message").textContent = "Listing serial ports…";
  try {
    const result = await hardware.request("/api/hardware/ports");
    const list = $("#serial-ports");
    list.replaceChildren();
    for (const item of result.ports) {
      const option = node("option", `${item.port} — ${item.description}`);
      option.value = item.port;
      list.append(option);
    }
    $("#port-message").textContent = result.ports.length ? result.message : "No ports found. Connect the USB device, refresh, or enter a port manually.";
  } catch (error) {
    $("#port-message").textContent = error.message;
  } finally { hardware.buttons(); }
});
$("#connect-device").addEventListener("click", () => hardware.action("connect"));
$("#disconnect-device").addEventListener("click", () => hardware.action("disconnect"));
$("#send-device").addEventListener("click", () => hardware.action("send"));
hardware.refresh();
setInterval(() => hardware.refresh(), 1000);

// App-wide state: agent health, which conversations are running, what is on screen (sent to the agent as context).
export const state = {
  health: null,
  context: "",
  busyConvs: new Set(),
  get busy() { return this.busyConvs.size > 0; },
  chatbars: new Set(),
  listeners: new Set(),
  setBusy(id, b) { if (!id) return; b ? this.busyConvs.add(id) : this.busyConvs.delete(id); this.emit(); },
  setHealth(h) { this.health = h; this.emit(); },
  emit() { for (const c of this.chatbars) if (c.el.isConnected) c.refreshMeta(); else this.chatbars.delete(c); for (const l of this.listeners) l(); },
  on(fn) { this.listeners.add(fn); },
};

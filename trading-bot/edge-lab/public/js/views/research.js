// Full research conversation: list of conversations on the left, the live thread on the right.
import { api } from "../api.js";
import { $, esc, fmt } from "../util.js";
import { icon } from "../icons.js";
import { Thread } from "../chat.js";
import { state } from "../state.js";

export default async function research(main, [id]) {
  main.innerHTML = `<div class="research"><div class="conv-list" id="convs"></div><div id="thread" style="min-height:0;height:100%"></div></div>`;
  const thread = new Thread($("#thread", main), { onConversation: (c) => { history.replaceState(null, "", `#research/${c.id}`); paintList(c.id); } });
  async function paintList(cur) {
    let convs = []; try { convs = await api.conversations(); } catch { /* ignore */ }
    $("#convs", main).innerHTML = `<a class="btn sm" href="#research/new" style="margin:0 6px 10px">${icon("plus", 13)} New research</a><h3>Recent</h3>` +
      (convs.map((c) => `<a class="conv-item ${c.id === cur ? "active" : ""}" href="#research/${c.id}"><b>${state.busyConvs.has(c.id) ? "● " : ""}${esc(c.title)}</b><small>${fmt.ago(c.updatedAt)} · ${c.count} messages</small></a>`).join("") || `<div class="caption" style="padding:0 10px">Nothing yet.</div>`);
  }
  if (id && id !== "new") await thread.load(id);
  else {
    await thread.load(null);
    thread.bar.el.querySelector("textarea").placeholder = "Ask anything about your strategies…";
    $(".thread-inner", main).innerHTML = `<div class="empty" style="margin-top:12vh"><div class="ring">${icon("sparkle", 16)}</div><h3>New research</h3><p>Describe a test, a filter or a question. The agent works inside your research folder with the permission level set in Settings.</p></div>`;
  }
  paintList(id);
  thread.bar.focus();
  const repaint = () => paintList(thread.conv?.id || id);
  state.on(repaint);
  return () => state.listeners.delete(repaint);
}

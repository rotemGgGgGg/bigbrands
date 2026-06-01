/* Temporary admin — list / add / edit / delete products in localStorage.
   Replaceable: swap this + store.js for your real backend later. */

(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const ils = (n) => "₪ " + Number(n).toLocaleString("he-IL");
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function fillSelectors() {
    $("#f-category").innerHTML = Store.categories()
      .map((c) => `<option>${esc(c)}</option>`)
      .join("");
    $("#brandList").innerHTML = Store.brands()
      .map((b) => `<option value="${esc(b)}">`)
      .join("");
  }

  function renderRows() {
    const list = Store.getProducts();
    $("#count").textContent = list.length;
    $("#rows").innerHTML = list
      .map(
        (p) => `
      <tr>
        <td>${esc(p.name)}</td>
        <td>${esc(p.brand || "")}</td>
        <td>${esc(p.category || "")}</td>
        <td>${ils(p.price)}</td>
        <td>
          <div class="mini">
            <button data-edit="${p.id}">עריכה</button>
            <button class="del" data-del="${p.id}">מחיקה</button>
          </div>
        </td>
      </tr>`
      )
      .join("");
  }

  function resetForm() {
    $("#productForm").reset();
    $("#f-id").value = "";
    $("#formTitle").textContent = "הוספת מוצר חדש";
    $("#saveBtn").textContent = "שמירת מוצר";
    $("#cancelBtn").style.display = "none";
  }

  function loadIntoForm(p) {
    $("#f-id").value = p.id;
    $("#f-name").value = p.name || "";
    $("#f-brand").value = p.brand || "";
    $("#f-category").value = p.category || Store.categories()[0];
    $("#f-price").value = p.price ?? "";
    $("#f-badge").value = p.badge || "";
    $("#f-specs").value = p.specs || "";
    $("#f-image").value = p.image || "";
    $("#formTitle").textContent = "עריכת מוצר";
    $("#saveBtn").textContent = "עדכון מוצר";
    $("#cancelBtn").style.display = "inline-block";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function bind() {
    $("#productForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const id = $("#f-id").value || Store.newId();
      Store.saveProduct({
        id,
        name: $("#f-name").value.trim(),
        brand: $("#f-brand").value.trim(),
        category: $("#f-category").value,
        price: Number($("#f-price").value) || 0,
        badge: $("#f-badge").value.trim(),
        specs: $("#f-specs").value.trim(),
        image: $("#f-image").value.trim(),
      });
      resetForm();
      renderRows();
    });

    $("#cancelBtn").addEventListener("click", resetForm);

    $("#rows").addEventListener("click", (e) => {
      const edit = e.target.closest("[data-edit]");
      const del = e.target.closest("[data-del]");
      if (edit) {
        const p = Store.getProduct(edit.dataset.edit);
        if (p) loadIntoForm(p);
      }
      if (del) {
        if (confirm("למחוק את המוצר?")) {
          Store.deleteProduct(del.dataset.del);
          renderRows();
        }
      }
    });

    $("#resetBtn").addEventListener("click", () => {
      if (confirm("לאפס את כל המוצרים לנתוני ברירת המחדל? פעולה זו תמחק שינויים מקומיים.")) {
        Store.resetToSeed();
        renderRows();
      }
    });

    $("#themeToggle").addEventListener("click", () => {
      const next =
        document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("bigbrands.theme", next);
    });
  }

  function boot() {
    const t = localStorage.getItem("bigbrands.theme");
    if (t) document.documentElement.dataset.theme = t;
    fillSelectors();
    renderRows();
    bind();
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();

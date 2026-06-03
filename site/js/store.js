/*
  STORE — thin layer over the seed data in data.js.
  Products are kept in the browser's localStorage so the temporary admin
  panel can add/edit/delete them and the changes persist on this device.
  Everything else (hero slides, brands, partners) is read straight from data.js.

  Replaceable by design: a real backend would swap these functions to call
  an API instead of localStorage. The storefront only uses Store.getProducts(),
  Store.getProduct(id), etc., so nothing else needs to change.
*/

window.Store = (function () {
  const KEY = "bigbrands.products.v2";

  function seed() {
    return JSON.parse(JSON.stringify(window.SITE_DATA.products));
  }

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return seed();
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) && parsed.length ? parsed : seed();
    } catch (e) {
      return seed();
    }
  }

  function persist(list) {
    localStorage.setItem(KEY, JSON.stringify(list));
  }

  return {
    getProducts() {
      return load();
    },
    getProduct(id) {
      return load().find((p) => p.id === id) || null;
    },
    saveProduct(product) {
      const list = load();
      const i = list.findIndex((p) => p.id === product.id);
      if (i >= 0) list[i] = product;
      else list.unshift(product);
      persist(list);
      return product;
    },
    deleteProduct(id) {
      persist(load().filter((p) => p.id !== id));
    },
    resetToSeed() {
      persist(seed());
    },
    newId() {
      return "p-" + Math.random().toString(36).slice(2, 9);
    },
    // pass-throughs for static content
    categories: () => window.SITE_DATA.categories,
    heroSlides: () => window.SITE_DATA.heroSlides,
    featured: () => window.SITE_DATA.featured,
    brands: () => window.SITE_DATA.brands,
    partners: () => window.SITE_DATA.partners,
  };
})();

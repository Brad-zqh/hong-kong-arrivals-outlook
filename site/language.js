"use strict";

const siteLanguage = (() => {
  const root = document.documentElement;
  const storageKey = "ikun-language";
  const url = new URL(location.href);
  const requested = url.searchParams.get("lang");
  let saved;
  try { saved = localStorage.getItem(storageKey); } catch { /* The URL still works. */ }

  const chinese = () => root.lang === "zh-Hans";
  const text = (zh, en) => chinese() ? zh : en;
  root.lang = (requested === "zh" || requested === "en" ? requested : saved) === "zh" ? "zh-Hans" : "en";

  function updatePage() {
    const button = document.querySelector(".language-toggle");
    button.hidden = false;
    button.setAttribute("aria-label", text("Switch to English", "切换到中文"));
    document.title = text(root.dataset.titleZh, root.dataset.titleEn);
    for (const [attribute, translation] of [["aria-label", "data-zh-aria"], ["alt", "data-zh-alt"]]) {
      for (const node of document.querySelectorAll(`[${translation}]`)) {
        const original = node.getAttribute(`${translation}-original`) ?? node.getAttribute(attribute);
        node.setAttribute(`${translation}-original`, original);
        node.setAttribute(attribute, text(node.getAttribute(translation), original));
      }
    }
    for (const link of document.querySelectorAll("a[href]")) {
      const href = link.getAttribute("href");
      if (!/^(index|methods|rehearsals)\.html(?:\?|#|$)/.test(href)) continue;
      const target = new URL(href, location.href);
      const explicit = new URL(location.href).searchParams.get("lang");
      if (chinese() || explicit === "en") target.searchParams.set("lang", text("zh", "en"));
      else target.searchParams.delete("lang");
      link.href = target.pathname.split("/").at(-1) + target.search + target.hash;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    updatePage();
    document.querySelector(".language-toggle").addEventListener("click", () => {
      const next = chinese() ? "en" : "zh";
      root.lang = next === "zh" ? "zh-Hans" : "en";
      try { localStorage.setItem(storageKey, next); } catch { /* Keep the selection in the URL. */ }
      const target = new URL(location.href);
      target.searchParams.set("lang", next);
      history.replaceState(history.state, "", target);
      updatePage();
      document.dispatchEvent(new Event("site-language-change"));
    });
  });

  return { text };
})();

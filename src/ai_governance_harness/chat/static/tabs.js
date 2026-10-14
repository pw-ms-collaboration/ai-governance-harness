"use strict";

(() => {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const panelFor = (tab) => document.getElementById(tab.getAttribute("aria-controls"));
  const hashFor = (tab) => `#${tab.id.replace(/^tab-/, "")}`;

  function select(tab, { focus = false, updateHash = true } = {}) {
    for (const item of tabs) {
      const selected = item === tab;
      item.setAttribute("aria-selected", String(selected));
      item.tabIndex = selected ? 0 : -1;
      panelFor(item).hidden = !selected;
    }
    if (focus) tab.focus();
    if (updateHash && location.hash !== hashFor(tab)) {
      // app.js declares a top-level `history`, so the browser API must be referenced via window.
      window.history.replaceState(null, "", hashFor(tab));
    }
  }

  function fromHash() {
    return tabs.find((tab) => hashFor(tab) === location.hash);
  }

  for (const tab of tabs) {
    tab.addEventListener("click", () => select(tab));
    tab.addEventListener("keydown", (event) => {
      const index = tabs.indexOf(tab);
      const targets = {
        ArrowRight: tabs[(index + 1) % tabs.length],
        ArrowLeft: tabs[(index - 1 + tabs.length) % tabs.length],
        Home: tabs[0],
        End: tabs.at(-1),
      };
      const next = targets[event.key];
      if (!next) return;
      event.preventDefault();
      select(next, { focus: true });
    });
  }

  // Skip links may target content inside a hidden panel; reveal it before the browser scrolls.
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#"]');
    const target = link && document.getElementById(link.getAttribute("href").slice(1));
    const panel = target?.closest('[role="tabpanel"]');
    if (panel?.hidden) {
      select(tabs.find((tab) => panelFor(tab) === panel));
    }
  });

  window.addEventListener("hashchange", () => {
    const tab = fromHash();
    if (tab) select(tab, { updateHash: false });
  });

  const initial = fromHash();
  if (initial) select(initial, { updateHash: false });
})();

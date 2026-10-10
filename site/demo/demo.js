// Fridge-Worthy live demo: hides past items, marks today's, and highlights the nav.
// Demo mode: <body data-demo-today="YYYY-MM-DD"> pins "today" so the demo never goes stale.
(() => {
  // "Today" is the school's date (Pacific time), wherever the parent is.
  const SCHOOL_TZ = "America/Los_Angeles";
  const parse = s => /^\d{4}-\d{2}-\d{2}$/.test(s || "") ? new Date(s + "T00:00") : null;
  const schoolDay = () => {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone: SCHOOL_TZ, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
    const p = Object.fromEntries(parts.map(x => [x.type, x.value]));
    return parse(`${p.year}-${p.month}-${p.day}`);
  };
  const demoToday = parse(document.body.dataset.demoToday);
  const today = demoToday || schoolDay();

  // Placeholder links (href="#demo") show a short note instead of going anywhere.
  const toast = document.getElementById("demo-toast");
  let toastTimer;
  document.addEventListener("click", e => {
    const a = e.target.closest('a[href="#demo"]');
    if (!a || !toast) return;
    e.preventDefault();
    // Clear, then set on the next frame, so screen readers announce it again on repeat clicks.
    toast.textContent = "";
    requestAnimationFrame(() => { toast.textContent = "Demo link. On a real class page, this opens the school's page."; });
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
  });

  if (today) {
    // If the page is left open past midnight, reload it when the parent comes back (not in demo mode).
    if (!demoToday) {
      const reloadIfNewDay = () => { if (schoolDay().getTime() !== today.getTime()) location.reload(); };
      addEventListener("pageshow", reloadIfNewDay);
      document.addEventListener("visibilitychange", () => { if (!document.hidden) reloadIfNewDay(); });
    }

    // Today's date in the header
    document.getElementById("today-mon").textContent = today.toLocaleString("en-US", { month: "short" });
    document.getElementById("today-day").textContent = today.getDate();
    const chip = document.getElementById("today");
    chip.title = (demoToday ? "Demo date: " : "Today is ") + today.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
    document.getElementById("today-sr").textContent = chip.title;
    chip.classList.add("ready");

    // Mark past and current items. data-date is "YYYY-MM-DD", a range "start/end",
    // or separate days "d1,d2" (e.g. Tue and Thu only: Wednesday is not "today").
    document.querySelectorAll("[data-date]").forEach(el => {
      const value = el.dataset.date;
      const days = value.includes(",") ? value.split(",").map(parse) : null;
      const [start, end] = days ? [days[0], days[days.length - 1]] : value.split("/").map(parse);
      if (!start) return;
      const isToday = days ? days.some(d => d && d.getTime() === today.getTime()) : start <= today && today <= (end || start);
      if ((end || start) < today) {
        el.classList.add("is-past");
      } else if (isToday) {
        el.classList.add("is-today");
        el.classList.toggle("is-range", !days && !!end);
      }
    });
    const soon = document.getElementById("soon");
    const soonEmpty = document.getElementById("soon-empty");
    if (soon && soonEmpty && !soon.querySelector("li:not(.is-past)")) soonEmpty.classList.add("show");
    const later = document.querySelector("details.later-toggle");
    if (later && (soonEmpty?.classList.contains("show") || later.querySelector("li.is-today"))) later.open = true;
    const weekEmpty = document.getElementById("week-empty");
    if (weekEmpty && !document.querySelector(".todo .item:not(.is-past)")) weekEmpty.classList.add("show");

    // Warn when the page hasn't been updated in more than 8 days (never in demo mode)
    const stale = document.getElementById("stale");
    const updated = parse(stale?.dataset.updated);
    if (!demoToday && updated && Math.round((today - updated) / 864e5) > 8) {
      stale.textContent = "Heads up: this page hasn't been updated since " +
        updated.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + ". Check school email for the latest.";
      stale.classList.add("show");
    }
  }

  // Underline the nav link for the section on screen
  const links = [...document.querySelectorAll("nav.jump a")];
  const setActive = id => links.some(a => a.hash === "#" + id) && links.forEach(a => a.hash === "#" + id ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current"));
  if (links[0]) setActive(links[0].hash.slice(1));
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) setActive(e.target.id); });
  }, { rootMargin: "-30% 0px -60% 0px" });
  document.querySelectorAll("main section[id]").forEach(s => observer.observe(s));
})();

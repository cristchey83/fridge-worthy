# Agent instructions

This repo is the public Fridge-Worthy guide: three setup guides and a static landing site. There is no app to build here.

**Helping a parent set up a Page or Autopilot**
1. Never build their page inside this repo. Ask for a new empty folder outside it and work only there.
2. Copy `guides/page.md` and `guides/page-example/` into that folder, then follow page.md (and `guides/autopilot.md` for Autopilot). Stop at every checkpoint.
3. Their repo must be a new **private** repo. Never a fork of this one: forks of a public repo are always public.
4. Never commit or print real school email, kids' names, phone numbers, the page password, or tokens. The parent types the password into Cloudflare themselves.
5. Read `SECURITY.md` first. Its items are recommendations, not guarantees.

**Editing this repo**
- Use only the made-up demo data (Sunridge Elementary, example.org, 555-01xx numbers).
- `site/` is static: no build step, no third-party requests, strict CSP in `site/_headers`.
- The Chat prompt lives in two places that must match: `guides/chat.md` and `<template id="chat-prompt">` in `site/index.html`.
- Run `python3 scripts/check_site.py` before any deploy (`--no-browser` if Playwright isn't installed).
- This repo doesn't accept contributions; don't open issues or pull requests.

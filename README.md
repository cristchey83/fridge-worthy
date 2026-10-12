# Fridge-Worthy

An open-source guide to taming school communications.

About 20 school emails a week, and only a few need you. Fridge-Worthy helps you sort a week of school email down to the updates your family has to act on: forms, schedule changes, things to pack or pay.

Site and live demo: https://fridge-worthy.pages.dev

## Pick your setup

| Setup | Code | Guide |
|---|---|---|
| Chat | No code | [guides/chat.md](guides/chat.md): paste a week of email into Claude or ChatGPT with one prompt |
| Page | Some code | [guides/page.md](guides/page.md): your coding agent builds a small password-protected page for your family or class |
| Autopilot | Much code (experimental) | [guides/autopilot.md](guides/autopilot.md): a blueprint for a page that updates itself |

Read [SECURITY.md](SECURITY.md) before you build a Page or Autopilot.

## What's here

- `guides/`: the three setups, plus an example page data file
- `site/`: the landing page and the demo (a made-up school)
- `scripts/check_site.py`: checks the site before deploy
- `tests/`: checks the docs (links, example data, safety rules)
- `SECURITY.md`: safety recommendations and FAQ

## About this repo

Shared as a reference. Not accepting contributions or support requests. Clone it, copy it, make it yours.

To build your own Page, start a new **private** repo (see [guides/page.md](guides/page.md)). Don't fork this one: forks of a public repo are always public. Never commit real school email, kids' names, or passwords.

## License

MIT. See [LICENSE](LICENSE). The fonts in `site/fonts/` (Inter, Caveat, Playfair Display) are under the SIL Open Font License; see the `OFL-*.txt` files there.

Checks (they also run on every push): `python3 -m unittest discover -s tests` for the docs, and `python3 scripts/check_site.py` for the site (needs Playwright; add `--no-browser` to skip the browser checks).

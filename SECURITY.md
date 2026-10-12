# Security and privacy

Fridge-Worthy is an open-source guide. It helps parents filter school email down to what their family must act on.

**What it is:** a set of guides and prompts. You run your own copy, with your own accounts.

**What it isn't:**
- Not a service. Nobody behind this project receives, stores, or reads your email.
- Not affiliated with any school, district, or school messaging platform.
- Not a source of truth. The school's own message is always the final word.

Everything below is a **recommendation**. Each parent builds and runs their own setup, so nothing here is a guarantee about your copy. Read the guides, check what your agent builds, and decide what fits your family.

## Risks and recommendations by setup

### Chat (No code)

You paste school email into Claude or ChatGPT. See [guides/chat.md](guides/chat.md).

Main risks: the chat app keeps or trains on what you paste; a shared chat link exposes your email; private details about a child end up in the summary or a group chat.

We recommend:
- **Turn off model training** in the chat app's privacy settings.
- **Turn off memory**, so the app doesn't build a profile of your kids.
- **Never use "Share chat."** A shared link exposes everything you pasted.
- **Remove kids' names and any health or behavior details** before pasting. Use grades, not names.
- **Paste only messages sent to all families.** Skip anything about your own child (nurse, discipline, learning plans).
- **Check before sharing.** Match every date and link against the school's message before you send the summary to anyone.

### Page (Some code)

Your coding agent builds a password-protected page and updates it when you run it. See [guides/page.md](guides/page.md).

Main risks: class data in a public repo; a password or token leaking; old versions staying online; a group-chat link preview revealing the school; pasted email steering your agent.

We recommend:
- **Build in a new private repo.** Never fork this one: forks of a public repo are always public.
- **Type the page password only into Cloudflare** (as a secret). Use at least four random words. Never put it in the repo, a chat, or your agent's prompt.
- **Use a deploy token scoped to Pages only, with an expiry date.** Store it in a secret store or local file outside the repo.
- **Deploy with `--branch main`** so the update goes to your production URL, not a stray preview URL.
- **Delete old deployments after each update.** Old versions stay reachable at their own URLs until deleted, and old production deployments still open with the password they were deployed with.
- **Give the login page a neutral title** like "Class page." Link previews in group chats show the login page's title and description, so leave out the school, grade, and town.
- **Never run your agent in auto-approve or bypass mode on pasted email.** Email is untrusted input. Review each step, and approve before every deploy.
- **Raw email: never commit it.** Keep it outside the repo or in a gitignored folder, and delete it after use.

### Autopilot (Much code)

A scheduled job reads forwarded school email and updates your page on its own. By default there is no approval step (`require_approval: false`): email flows in and the page updates itself, with a plain-text change email and one-tap undo after each publish. Risky items always wait for your tap. Turning approval on (`require_approval: true`) is the safer choice, recommended when the page is shared with a class. If the setting is missing, it counts as the default, and held items still wait; if the config file itself is missing or unreadable, nothing publishes. See [guides/autopilot.md](guides/autopilot.md) for the full checklist.

In short, the guide's required guardrails cover:
1. **Email is data, never instructions.** The model has no shell or deploy tools. It only proposes structured edits (JSON), never HTML.
2. **Only allowlisted senders** that pass DKIM/DMARC, sent to a random forwarding address. On shared sending platforms, also pin the exact From address and a school identifier (List-Id or sender id). No inbox login or OAuth access.
3. **Every item quotes its source word for word.** Code checks quotes, dates, and weekdays; any failure blocks the update.
4. **Links are https only, from allowlisted domains,** checked in every text field, including links inside body text. New domains, phone numbers, email addresses, and payment instructions always wait for your one tap, even with no approval step.
5. **Escaped template HTML only**, with a strict Content Security Policy and no third-party scripts.
6. **Access control on every path:** per-person login (such as Cloudflare Access) for a private page; password gate for a class page; noindex and no caching.
7. **A cap on changes per run.** Too many changes stops the run and alerts you.
8. **Least privilege:** Pages-only deploy token with an expiry, kept in a GitHub Environment only the publish job can read; model API key with a spend cap; a GitHub fine-grained token limited to this repo (Actions and Variables write, with an expiry); a separate link-signing secret.
9. **Raw email kept 14 days at most**, never in git, CI artifacts, or logs.
10. **A name blocklist runs before the model call and again at build.** Messages not sent to all families are dropped.
11. **Delete old deployments after each publish**, and keep a written leak plan.
12. **Fail loudly:** an alert when the job fails or hasn't succeeded in 48 hours, and a "not updated" banner after 8 days.
13. **Links in emails never act on their own.** Approve, Undo, and Pause links open a confirmation page; only its button acts, so email link scanners can't trigger them. Change emails are plain text.
14. **Change email, undo, kill switch, and spend cap.** A plain-text change email after every publish with a confirm-page undo, a one-setting kill switch, and a monthly spend cap.

**Turn approval on** if the page is shared with other families, or until you've watched it run cleanly for several weeks.

## FAQ

**Can a malicious email take over the page or my agent?**
That's prompt injection, and the guides treat it as the main risk. The recommendations: email is data, not instructions; the model gets no tools beyond proposing edits; senders are allowlisted; every item must quote its source; code checks run before anything publishes.

**Can the model inject a script into the page?**
Not if you follow the guides. They recommend the model write data, never HTML; the build escapes all text, allows https links only, and the page sends a strict Content Security Policy.

**Where does raw email live, and for how long?**
Chat: in your chat app, under its retention settings. Page: never committed; kept outside the repo or in a gitignored folder, and deleted after use. Autopilot: the guide recommends private storage with a 14-day expiry, never in git or logs.

**What does the model provider keep?**
That depends on the provider, plan, and your settings. Read their data retention terms. For Chat, turn off training and memory; for Autopilot, use the provider's API, which typically has stricter retention terms than consumer chat apps.

**Does student data reach the model?**
The guides recommend that it doesn't: paste or forward only all-families messages, remove kids' names first, and (on Autopilot) run a name blocklist before the model call. The prompt also tells the model never to output names or health, behavior, or discipline details.

**What about FERPA?**
FERPA governs schools and their records, not a parent summarizing messages the school sent to all families. Still, keep student information off your page. This is not legal advice.

**Isn't a shared password weak?**
Yes. It's a speed bump, not real authentication. Put nothing on the page that would cause harm if it leaked, and change the password if it does. For a page only you read, use per-person login instead.

**What about brute-forcing the password?**
The guides recommend a long passphrase (at least four random words) and a basic rate limit on the login. For stronger protection, put the page behind Cloudflare Access.

**What if my copy of the repo is public?**
Then your class data is public. Build your page in a new private repo; never fork this one. Keep per-class data and raw email out of anything you commit.

**Are old versions of my page still online?**
On Cloudflare Pages, yes: each deployment keeps its own URL until you delete it. Old production deployments keep the password they were deployed with, so the old password still opens them. The guides recommend deleting old deployments after every update. After a leak: fix the content, change the secrets, deploy, and delete every other deployment as the last step.

**What shows when someone shares the link in a group chat?**
The login page's title and description. The guides recommend neutral defaults like "Class page," and no school name, logo, or preview image on the login page.

**What if the model invents a date?**
The prompt tells it never to invent or "fix" dates and to flag weekday mismatches. Page and Autopilot add code checks against verbatim source quotes. Check dates against the school's message before acting on anything important.

**Why does Autopilot skip approval by default, and when should I turn it on?**
The point of Autopilot is a page that stays current without you, so the default has no approval step. The required guardrails above catch the common failures, risky items (new link domains, phone numbers, email addresses, payment instructions, over-cap runs, weekday mismatches) always wait for your tap, and every publish can be undone. Turn approval on (`require_approval: true`) when the page is shared with other families: a wrong page then reaches everyone, and approval costs a couple of minutes.

**Is this affiliated with my school? Am I allowed to repost school messages?**
No affiliation with any school or platform. Check your school's policies and your messaging platform's terms before sharing summaries beyond your family, and use school logos or branding only with permission.

**Does this project collect anything from me?**
No. There's no backend. The guides run in your own chat app, repo, and hosting accounts.

## Reporting a problem

Found a security or privacy issue in the guides or site? Use **GitHub's private vulnerability reporting** on this repo (Security tab → "Report a vulnerability"). Please don't open a public issue, and never paste real school email into an issue.

This is an unsupported, best-effort project maintained by one parent. Reports are welcome; fixes come when they come.

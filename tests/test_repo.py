"""Repo checks for the guides and docs. Run: python3 -m unittest discover tests"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def prose(path):
    """Markdown text without fenced blocks or inline code (examples there aren't real links)."""
    text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def slug(heading):
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(path):
    return {slug(m.group(1)) for m in re.finditer(r"^#+\s+(.+)$", path.read_text(), re.M)}


class Docs(unittest.TestCase):
    def test_relative_links_resolve(self):
        for doc in DOCS:
            for target in LINK.findall(prose(doc)):
                if re.match(r"[a-z]+:", target):
                    continue
                path, _, frag = target.partition("#")
                dest = (doc.parent / path).resolve() if path else doc
                with self.subTest(doc=doc.name, link=target):
                    self.assertTrue(dest.exists(), f"{doc.relative_to(ROOT)} links to missing {target}")
                    if frag and dest.suffix == ".md":
                        self.assertIn(frag, anchors(dest), f"{doc.relative_to(ROOT)}: no heading for #{frag}")

    def test_backticked_repo_paths_exist(self):
        # Paths like `guides/page.md` or `site/_headers` named in the top-level docs must exist.
        for name in ("README.md", "AGENTS.md", "SECURITY.md"):
            for p in re.findall(r"`((?:guides|site|scripts|tests)/[^`\s]*)`", (ROOT / name).read_text()):
                with self.subTest(doc=name, path=p):
                    self.assertTrue((ROOT / p).exists(), f"{name} mentions missing {p}")

    def test_never_tells_people_to_fork_or_use_a_template(self):
        # Forks of a public repo are public; there is no template repo.
        bad = re.compile(r"fork it|use this template", re.I)
        for doc in DOCS:
            with self.subTest(doc=doc.name):
                self.assertIsNone(bad.search(doc.read_text()), doc.name)

    def test_readme_lists_every_guide(self):
        readme = (ROOT / "README.md").read_text()
        for guide in (ROOT / "guides").glob("*.md"):
            self.assertIn(f"guides/{guide.name}", readme)

    def test_claude_md_points_to_agents_md(self):
        self.assertEqual((ROOT / "CLAUDE.md").read_text().strip(), "@AGENTS.md")
        self.assertIn("private", (ROOT / "AGENTS.md").read_text())

    def test_first_run_starter_set(self):
        chat = (ROOT / "guides/chat.md").read_text()
        for phrase in ("## First run", "school calendar", "last 2–3 weeks", "handbook"):
            self.assertIn(phrase, chat)
        self.assertIn("chat.md#first-run", (ROOT / "guides/page.md").read_text())


class ExampleData(unittest.TestCase):
    def test_example_content_is_valid_json_with_fake_data(self):
        text = (ROOT / "guides/page-example/content.example.json").read_text()
        json.loads(text)
        for email in re.findall(r"[\w.+-]+@([\w.-]+)", text):
            self.assertTrue(email.endswith("example.org"), email)
        for phone in re.findall(r"\b\d{3}-\d{4}\b", text):
            self.assertTrue(phone.startswith("555-01"), phone)


class Ignore(unittest.TestCase):
    def test_gitignore_keeps_private_stuff_out(self):
        ignored = (ROOT / ".gitignore").read_text().split()
        for entry in ("inbox/", "*.eml", ".env*", ".dev.vars", ".wrangler/", ".claude/", ".venv/"):
            self.assertIn(entry, ignored)


if __name__ == "__main__":
    unittest.main()

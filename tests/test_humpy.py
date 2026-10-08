import asyncio
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from camelcase import GaveUp, retry, to_camel, to_pascal, to_snake
from camelcase import haul as haul_module
from camelcase.cli import main
from camelcase.report import markdown, terminal
from camelcase.trek import mask, trek

# Built at runtime so this file never contains anything that looks like a real key.
FAKE_TOKEN = "gh" + "p_" + "Q9w8E7r6T5" * 3 + "y4U3i2"
# Same for the marker words, so he does not grunt at his own tests.
T, F, H = "TO" + "DO", "FIX" + "ME", "HA" + "CK"
QUIET = "humpy: " + "ignore"


def make_repo(files: dict) -> str:
    root = tempfile.mkdtemp(prefix="stable-")
    for name, body in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


class TrekTests(unittest.TestCase):
    def test_markers_only_in_comments(self):
        root = make_repo({
            "app.py": f"x = 1  # {T}: retry on 429\nname = '{T} list'\n// {F} not python but a comment\n"
                      f"y = 2  # {T} later  {QUIET}\n",
            "README.md": f"{T} write docs\n",
        })
        report = trek(root, snakes=False)
        self.assertEqual([(m.kind, m.line) for m in report.markers], [(T, 1), (F, 3)])
        self.assertEqual(report.markers[0].text, "retry on 429")

    def test_marker_with_an_owner(self):
        report = trek(make_repo({"a.py": f"# {H}(sam): works on my machine\n"}))
        self.assertEqual(report.markers[0].text, "works on my machine")

    def test_key_is_found_and_never_repeated(self):
        report = trek(make_repo({"deploy.sh": f"export TOKEN={FAKE_TOKEN}\n"}))
        self.assertEqual([k.kind for k in report.keys], ["GitHub token"])
        self.assertNotIn(FAKE_TOKEN, terminal(report, color=False))
        self.assertNotIn(FAKE_TOKEN, markdown(report))
        self.assertTrue(report.verdict.startswith("bad camel"))

    def test_mask(self):
        self.assertEqual(mask("abcdefghijklmnop"), "abcd********op")
        self.assertEqual(mask("short"), "*****")

    def test_snakes(self):
        report = trek(make_repo({"app.py": "def load_page_data():\n    page_url = 1\n    return page_url\n"}))
        self.assertEqual([(s.name, s.camel) for s in report.snakes], [("load_page_data", "loadPageData"), ("page_url", "pageUrl")])

    def test_basics_and_score(self):
        full = make_repo({
            "README.md": "hi\n", "LICENSE": "MIT\n", ".gitignore": "*.pyc\n",
            "tests/test_x.py": "assert True\n", ".github/workflows/ci.yml": "on: push\n",
        })
        self.assertEqual(trek(full).missing, [])
        self.assertEqual(trek(full).score, 100)
        self.assertEqual(trek(full).verdict, "good camel")
        empty = trek(make_repo({"main.py": "print(1)\n"}))
        self.assertEqual(empty.missing, ["README", "LICENSE", ".gitignore", "tests", "CI"])
        self.assertEqual(empty.score, 60)
        self.assertEqual(empty.verdict, "spat on the carpet")

    def test_skips_node_modules_and_binaries(self):
        root = make_repo({"node_modules/x.js": f"// {F} skip me\n", "a.py": "x = 1\n"})
        (Path(root) / "img.bin").write_bytes(b"\0\1\2" * 100)
        report = trek(root)
        self.assertEqual(report.files, 1)
        self.assertEqual(report.markers, [])

    def test_not_a_directory(self):
        with self.assertRaises(NotADirectoryError):
            trek(__file__)


class CaseTests(unittest.TestCase):
    def test_conversions(self):
        self.assertEqual(to_camel("stack_trace_url"), "stackTraceUrl")
        self.assertEqual(to_camel("_private_thing"), "_privateThing")
        self.assertEqual(to_camel("HTTP_status-code"), "httpStatusCode")
        self.assertEqual(to_pascal("good camel"), "GoodCamel")
        self.assertEqual(to_snake("HTTPServerError"), "http_server_error")


class HTTPError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.status_code = code


class OasisTests(unittest.TestCase):
    def test_retries_then_succeeds(self):
        calls = []

        @retry(on=429, tries=7, sleep=lambda d: None)
        def cross():
            calls.append(1)
            if len(calls) < 3:
                raise HTTPError(429)
            return "good camel"

        self.assertEqual(cross(), "good camel")
        self.assertEqual(len(calls), 3)

    def test_other_errors_pass_through(self):
        @retry(on=429, sleep=lambda d: None)
        def cross():
            raise HTTPError(500)

        with self.assertRaises(HTTPError):
            cross()

    def test_gives_up(self):
        @retry(on=[429, 503], tries=4, sleep=lambda d: None)
        def cross():
            raise HTTPError(503)

        with self.assertRaises(GaveUp) as caught:
            cross()
        self.assertEqual(caught.exception.tries, 4)

    def test_hump_py_from_the_video_runs(self):
        from camelcase.hump import cross

        commits = []

        class Bug:
            async def chew(self, twice):
                return "patch"

        class Page:
            def find(self, what):
                return Bug()

        class Repo:
            async def trek(self, url):
                return Page()

            async def commit(self, patch, msg):
                commits.append(msg)

        class Issue:
            url = "https://example.com/issues/41"

        self.assertEqual(asyncio.run(cross(Repo(), Issue())), "good camel")
        self.assertEqual(commits, ["fix: retry on 429"])


class HaulTests(unittest.TestCase):
    def test_oldest_first_and_cargo(self):
        page = [
            {"number": 41, "title": "cross() dies on HTTP 429", "created_at": "2026-09-01T00:00:00Z", "labels": [{"name": "bug"}],
             "assignees": [], "comments": 2, "html_url": "u41"},
            {"number": 42, "title": "a pull request", "created_at": "2026-09-02T00:00:00Z", "labels": [], "assignees": [],
             "comments": 0, "html_url": "u42", "pull_request": {}},
            {"number": 29, "title": "crawler gets lost in the desert", "created_at": "2026-09-05T00:00:00Z",
             "labels": [{"name": "good first issue"}], "assignees": [{"login": "x"}], "comments": 0, "html_url": "u29"},
        ]
        with mock.patch.object(haul_module, "_get", side_effect=[page, []]):
            result = haul_module.haul("rgkdegen/camelcase", now=datetime(2026, 10, 8, tzinfo=timezone.utc))
        self.assertEqual(result["open"], 2)
        self.assertEqual(result["oldest"][0]["age_days"], 37)
        self.assertEqual([i["number"] for i in result["cargo"]], [41])

    def test_bad_address(self):
        with self.assertRaises(ValueError):
            haul_module.haul("not-a-repo")


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, buf.getvalue()

    def test_trek_json_and_fail_under(self):
        root = make_repo({"a.py": f"# {T}: water\n"})
        code, out = self.run_cli("--color", "never", "trek", root, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["markers"][0]["text"], "water")
        code, _ = self.run_cli("--color", "never", "trek", root, "--fail-under", "90")
        self.assertEqual(code, 1)

    def test_camel_and_grunt(self):
        self.assertEqual(self.run_cli("camel", "good_camel")[1].strip(), "goodCamel")
        self.assertIn("hmph", self.run_cli("grunt")[1])


if __name__ == "__main__":
    unittest.main()

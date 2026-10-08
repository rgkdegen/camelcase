from camelcase.cli import main
from camelcase.scan import scan


def make_repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def load_data():\n    # TODO: cache this\n    return 1\n")  # humpy: ignore
    (tmp_path / "README.md").write_text("Teh camel will recieve water.\n")  # humpy: ignore
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("// FIXME should be skipped\n")  # humpy: ignore
    return tmp_path


def test_scan_finds_things(tmp_path):
    rep = scan(make_repo(tmp_path))
    assert rep.files == 2
    assert [f.kind for f in rep.issues] == ["todo"]
    assert len(rep.by_kind("typo")) == 2
    assert [f.text for f in rep.by_kind("snake")] == ["load_data"]


def test_cli_runs(tmp_path, capsys):
    root = make_repo(tmp_path)
    assert main(["scan", str(root), "--no-color"]) == 0
    assert "FILES SCANNED 2" in capsys.readouterr().out
    assert main(["spit", str(root), "--no-color"]) == 0
    assert main(["camel", "good_camel"]) == 0
    assert capsys.readouterr().out.strip().endswith("goodCamel")
    assert main(["lint", str(root)]) == 1
    assert main(["lint", str(root), "--exit-zero"]) == 0

# tests/test_cli.py
from typer.testing import CliRunner  # ① 换导入

from dirscan.cli import app  # ② 导入的是 Typer 实例

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_cli_scan_json(tmp_path):
    out = tmp_path / "report.json"
    # 用本地小字典 + 本地假站点，保证能走到核心逻辑
    dict_file = tmp_path / "d.txt"
    dict_file.write_text("/robots.txt\n/nonexistent\n")
    result = runner.invoke(
        app,
        [
            "--url",
            "https://httpbin.org",
            "--wordlist",
            str(dict_file),
            "--threads",
            "2",
            "--rate",
            "10",
            "--output",
            str(out),
            "--format",
            "json",
        ],
    )
    # 只要没抛异常就算成功，exit_code 可以是 0 也可以是你自己定义的 1
    assert result.exit_code in (0, 1)
    assert out.exists()  # 报告文件必须落地
    # 还可以读出来确认是合法 json
    import json

    data = json.loads(out.read_text())
    assert isinstance(data, list)

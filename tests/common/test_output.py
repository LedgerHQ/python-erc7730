from pathlib import Path

import pytest

from erc7730.common.output import GithubAnnotationsAdder


def test_github_annotations_are_escaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    file = Path("a,b.json")
    file.touch()

    GithubAnnotationsAdder().error(
        file=file,
        line=3,
        title="Invalid value at $.display.formats.`transfer(address _to, uint256 _value)`.fields[0]",
        message="100% invalid\r\nexpected: raw",
    )

    assert capsys.readouterr().out == (
        "::error file=a%2Cb.json,line=3,"
        "title=Invalid value at $.display.formats.`transfer(address _to%2C uint256 _value)`.fields[0]"
        "::100%25 invalid%0D%0Aexpected: raw\n"
    )

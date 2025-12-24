from __future__ import annotations

from tesla_dashcam.cli_parsing import MyArgumentParser, SmartFormatter


def test_convert_arg_line_to_args_strips_comments_and_splits():
    p = MyArgumentParser(add_help=False)

    assert p.convert_arg_line_to_args("--foo=bar # comment") == ["--foo=bar"]
    assert p.convert_arg_line_to_args('a "b c" # comment') == ["a", "b c"]


def test_args_to_dict_builds_list_of_dicts_and_lowercases_keys():
    p = MyArgumentParser(add_help=False)

    arguments = [
        ["FILE1"],
        ["KEY=VALUE", "EMPTY=", "X=Y"],
        ["AnotherFile", "k=v"],
    ]

    out = p.args_to_dict(arguments, default="file")

    assert out == [
        {"file": "FILE1"},
        {"key": "VALUE", "empty": None, "x": "Y"},
        {"file": "AnotherFile", "k": "v"},
    ]


def test_args_to_dict_none_returns_empty_list():
    p = MyArgumentParser(add_help=False)
    assert p.args_to_dict(None, default="file") == []


def test_smartformatter_raw_lines():
    fmt = SmartFormatter(prog="x")

    assert fmt._split_lines("R|a\nb", width=10) == ["a", "b"]

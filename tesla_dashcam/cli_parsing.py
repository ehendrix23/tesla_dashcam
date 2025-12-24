from __future__ import annotations

import argparse
from shlex import split as shlex_split


class MyArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, arg_line) -> list[str]:
        # Remove comments.
        return shlex_split(arg_line, comments=True)

    def args_to_dict(self, arguments, default) -> list:
        argument_list: list = []

        if arguments is None:
            return argument_list

        for argument in arguments:
            argument_dict = {}
            for argument_value in argument:
                if "=" in argument_value:
                    key = argument_value.split("=")[0].lower()
                    value = (
                        argument_value.split("=")[1].strip()
                        if argument_value.split("=")[1].strip() != ""
                        else None
                    )
                else:
                    key = default
                    value = argument_value
                argument_dict.update({key: value})

            argument_list.append(argument_dict)
        return argument_list


class SmartFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Formatter for argument help."""

    def _split_lines(self, text: str, width: int) -> list[str]:
        """Provide raw output allowing for prettier help output"""
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return super()._split_lines(text, width)


__all__ = ["MyArgumentParser", "SmartFormatter"]

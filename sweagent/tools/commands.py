from __future__ import annotations

import re
import string
from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, model_validator

ARGUMENT_NAME_PATTERN = r"[a-zA-Z_][a-zA-Z0-9_-]+"


def _extract_keys(format_string: str) -> set[str]:
    """Given a format string, returns a set of all the keys in the format string."""
    formatter = string.Formatter()
    keys = set()
    for _, field_name, _, _ in formatter.parse(format_string):
        if field_name is not None:
            keys.add(field_name)
    return keys


class Argument(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    enum: list[str] | None = None
    argument_format: str = "{value}"  # how to invoke the argument in the command


class Command(BaseModel):
    name: str
    docstring: str | None
    signature: str | None = None
    # if there is an end_name, then it is a multi-line command
    end_name: str | None = None
    arguments: list[Argument] | None = None

    @cached_property
    def invoke_format(self) -> str:
        if self.signature:
            return re.sub(rf"\[?<({ARGUMENT_NAME_PATTERN})>\]?", r"{\1}", self.signature)
        else:
            # cmd arg_format_1 arg_format_2 ...
            _invoke_format = f"{self.name} "
            for arg in self.arguments:
                _invoke_format += f"{{{arg.name}}} "
            return _invoke_format

    def get_function_calling_tool(self) -> dict:
        tool = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.docstring or "",
            },
        }
        properties = {}
        required = []
        if self.arguments:
            for arg in self.arguments:
                properties[arg.name] = {"type": arg.type, "description": arg.description}

                if arg.required:
                    required.append(arg.name)

                # Handle enum if present
                if arg.enum:
                    properties[arg.name]["enum"] = arg.enum
        tool["function"]["parameters"] = {"type": "object", "properties": properties, "required": required}
        return tool

    @model_validator(mode="after")
    def validate_arguments(self) -> Command:
        """Validates that optional arguments come after required arguments and argument names are unique."""
        if not self.arguments:
            return self
        found_optional = False
        for arg in self.arguments:
            if found_optional and arg.required:
                msg = f"Command '{self.name}': Required argument '{arg.name}' cannot come after optional arguments"
                raise ValueError(msg)
            if not arg.required:
                found_optional = True
        duplicates = {arg.name for arg in self.arguments if self.arguments.count(arg) > 1}
        if duplicates:
            msg = f"Command '{self.name}': Duplicate argument names: {duplicates}"
            raise ValueError(msg)
        for arg in self.arguments:
            if not re.match(ARGUMENT_NAME_PATTERN, arg.name):
                msg = f"Command '{self.name}': Invalid argument name: '{arg.name}'"
                raise ValueError(msg)
        if _extract_keys(self.invoke_format) != {arg.name for arg in self.arguments}:
            msg = f"Command '{self.name}': Argument names in signature / invoke_format do not match argument names"
            raise ValueError(msg)
        return self


class AbstractParseCommand(ABC):
    @abstractmethod
    def parse_command_file(self, path: str) -> list[Command]:
        """
        Define how to parse a file into a list of commands.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_command_docs(self, commands: list[Command], subroutine_types, **kwargs) -> str:
        """
        Generate a string of documentation for the given commands and subroutine types.
        """
        raise NotImplementedError


# DEFINE NEW COMMAND PARSER FUNCTIONS BELOW THIS LINE


class ParseCommandBash(AbstractParseCommand, BaseModel):
    type: Literal["bash"] = "bash"
    """Discriminator for (de)serialization/CLI. Do not change."""

    def parse_command_file(self, path: Path) -> list[Command]:
        with open(path) as file:
            contents = file.read()
        if contents.strip().startswith("#!"):
            commands = self.parse_script(path, contents)
        else:
            if Path(path).suffix != ".sh" and not Path(path).name.startswith("_"):
                msg = (
                    f"Source file {path} does not have a .sh extension.\n"
                    "Only .sh files are supported for bash function parsing.\n"
                    "If you want to use a non-shell file as a command (script), "
                    "it should use a shebang (e.g. #!/usr/bin/env python)."
                )
                raise ValueError(msg)
            return self.parse_bash_functions(path, contents)
        if len(commands) == 0 and not Path(path).name.startswith("_"):
            msg = (
                f"Non-shell file {path} does not contain any commands.\n"
                "If you want to use a non-shell file as a command (script), "
                "it should contain exactly one @yaml docstring. "
                "If you want to use a file as a utility script, "
                "it should start with an underscore (e.g. _utils.py)."
            )
            raise ValueError(msg)
        else:
            return commands

    def parse_bash_functions(self, path, contents: str) -> list[Command]:
        """Simple logic for parsing a bash file and segmenting it into functions.

        Assumes that all functions have their name and opening curly bracket in one line,
        and closing curly bracket in a line by itself.
        """
        lines = contents.split("\n")
        commands = []
        idx = 0
        docs = []
        while idx < len(lines):
            line = lines[idx]
            idx += 1
            if line.startswith("# "):
                docs.append(line[2:])
            elif line.strip().endswith("() {"):
                name = line.split()[0][:-2]
                code = line
                while lines[idx].strip() != "}":
                    code += lines[idx]
                    idx += 1
                code += lines[idx]
                docstring, end_name, arguments, signature = None, None, None, name
                docs_dict = yaml.safe_load("\n".join(docs).replace("@yaml", ""))
                if docs_dict is not None:
                    docstring = docs_dict["docstring"]
                    end_name = docs_dict.get("end_name", None)
                    arguments = docs_dict.get("arguments", None)
                    if "signature" in docs_dict:
                        signature = docs_dict["signature"]
                    elif arguments is not None:
                        for argument in arguments:
                            param = argument["name"]
                            if argument["required"]:
                                signature += f" <{param}>"
                            else:
                                signature += f" [<{param}>]"
                command = Command.model_validate(
                    {
                        "docstring": docstring,
                        "end_name": end_name,
                        "name": name,
                        "arguments": arguments,
                        "signature": signature,
                    },
                )
                commands.append(command)
                docs = []
        return commands

    def parse_script(self, path, contents) -> list[Command]:
        pattern = re.compile(r"^#\s*@yaml\s*\n^#.*(?:\n#.*)*", re.MULTILINE)
        matches = pattern.findall(contents)
        if len(matches) == 0:
            return []
        elif len(matches) > 1:
            msg = "Non-shell file contains multiple @yaml tags.\nOnly one @yaml tag is allowed per script."
            raise ValueError(msg)
        else:
            yaml_content = matches[0]
            yaml_content = re.sub(r"^#", "", yaml_content, flags=re.MULTILINE)
            docs_dict = yaml.safe_load(yaml_content.replace("@yaml", ""))
            assert docs_dict is not None
            docstring = docs_dict["docstring"]
            end_name = docs_dict.get("end_name", None)
            arguments = docs_dict.get("arguments", None)
            signature = docs_dict.get("signature", None)
            name = Path(path).name.rsplit(".", 1)[0]
            if signature is None and arguments is not None:
                signature = name
                for argument in arguments:
                    param = argument["name"]
                    if argument["required"]:
                        signature += f" <{param}>"
                    else:
                        signature += f" [<{param}>]"
            code = contents
            return [
                Command.model_validate(
                    {
                        "code": code,
                        "docstring": docstring,
                        "end_name": end_name,
                        "name": name,
                        "arguments": arguments,
                        "signature": signature,
                    },
                ),
            ]

    def generate_command_docs(self, commands: list[Command], subroutine_types, **kwargs) -> str:
        docs = ""
        for cmd in commands:
            if cmd.docstring is not None:
                docs += f"{cmd.signature or cmd.name} - {cmd.docstring.format(**kwargs)}\n"
        for subroutine in subroutine_types:
            if subroutine.docstring is not None:
                docs += f"{subroutine.signature or subroutine.name} - {subroutine.docstring.format(**kwargs)}\n"
        return docs


class ParseCommandDetailed(ParseCommandBash):
    """
    # command_name:
    #   "docstring"
    #   signature: "signature"
    #   arguments:
    #     arg1 (type) [required]: "description"
    #     arg2 (type) [optional]: "description"
    """

    type: Literal["detailed"] = "detailed"
    """Discriminator for (de)serialization/CLI. Do not change."""

    @staticmethod
    def get_signature(cmd):
        signature = cmd.name
        if "arguments" in cmd.__dict__ and cmd.arguments is not None:
            if cmd.end_name is None:
                for argument in cmd.arguments:
                    param = argument["name"]
                    if argument["required"]:
                        signature += f" <{param}>"
                    else:
                        signature += f" [<{param}>]"
            else:
                for argument in cmd.arguments[:-1]:
                    param = argument["name"]
                    if argument["required"]:
                        signature += f" <{param}>"
                    else:
                        signature += f" [<{param}>]"
                signature += f"\n{list(cmd.arguments[-1].keys())[0]}\n{cmd.end_name}"
        return signature

    def generate_command_docs(
        self,
        commands: list[Command],
        subroutine_types,
        **kwargs,
    ) -> str:
        docs = ""
        for cmd in commands + subroutine_types:
            docs += f"{cmd.name}:\n"
            if cmd.docstring is not None:
                docs += f"  docstring: {cmd.docstring.format(**kwargs)}\n"
            if cmd.signature is not None:
                docs += f"  signature: {cmd.signature}\n"
            else:
                docs += f"  signature: {self.get_signature(cmd)}\n"
            if "arguments" in cmd.__dict__ and cmd.arguments is not None:
                docs += "  arguments:\n"
                for argument in cmd.arguments:
                    param = argument.name
                    req_string = "required" if argument.required else "optional"
                    docs += f"    - {param} ({argument.type}) [{req_string}]: {argument.description}\n"
            docs += "\n"
        return docs


ParseCommand = ParseCommandBash | ParseCommandDetailed

# Default Bash tool
BASH_COMMAND = Command(
    name="bash",
    signature="<command>",
    docstring="runs the given command directly in bash",
    arguments=[
        Argument(
            name="command",
            type="string",
            description="a command to run directly in the current shell",
            required=True,
        )
    ],
)

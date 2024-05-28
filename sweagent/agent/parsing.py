from __future__ import annotations

import json
import re
import shlex
import string
import textwrap
from abc import abstractmethod
from dataclasses import dataclass

from sweagent.agent.commands import Command


class FormatError(Exception):
    pass


# ABSTRACT BASE CLASSES


class ParseFunctionMeta(type):
    """
    Registry maps all inherited classes to their names.
    """

    _registry = {}

    def __new__(cls, name, bases, attrs):
        new_cls = super().__new__(cls, name, bases, attrs)
        if name != "ParseFunction":
            cls._registry[name] = new_cls
        return new_cls


@dataclass
class ParseFunction(metaclass=ParseFunctionMeta):
    """
    Abstract class for parsing functions.
    We use get to generate the right parser based on the name of the parser.
    """

    _error_message = None

    @abstractmethod
    def __call__(self, model_response, commands: list[Command], strict=False):
        raise NotImplementedError

    @property
    def format_error_template(self):
        if self._error_message is None:
            msg = "You must define an error message for your parser."
            raise NotImplementedError(msg)
        return textwrap.dedent(self._error_message)

    @classmethod
    def get(cls, name):
        try:
            return cls._registry[name]()
        except KeyError:
            msg = f"Model output parser ({name}) not found."
            raise ValueError(msg)


# DEFINE NEW PARSING FUNCTIONS BELOW THIS LINE


class ActionParser(ParseFunction):
    """
    Expects the model response to be a single command.
    Example: "ls -l"
    """

    _error_message = """\
    The command you provided was not recognized. Please specify one of the commands (+ any necessary arguments) from the following list in your response. Do not include any other text.

    COMMANDS:
    {command_docs}
    """

    def __call__(self, model_response, commands: list[Command], strict=False):
        if model_response.split():
            action = model_response.strip().split()[0]
            if action in {command.name for command in commands}:
                return model_response, model_response
        msg = "First word in model response is not a valid command."
        raise FormatError(msg)


class ThoughtActionParser(ParseFunction):
    """
    Expects the model response to be a discussion followed by a command wrapped in backticks.
    Example:
    Let's look at the files in the current directory.
    ```
    ls -l
    ```
    """

    _error_message = """\
    Your output was not formatted correctly. You must always include one discussion and one command as part of your response. Make sure you do not have multiple discussion/command tags.
    Please make sure your output precisely matches the following format:
    DISCUSSION
    Discuss here with yourself about what your planning and what you're going to do in this step.

    ```
    command(s) that you're going to run
    ```
    """

    def __call__(self, model_response, commands: list[Command], strict=False):
        """
        Parses the action from the output of the API call.
        We assume that the action is the last code block in the model_response.
        We also assume that the action is not nested within another code block.
        This is problematic if the model_response includes many unnamed ``` blocks.
        For instance:
        ```
        This is a code block.
        ```
        ```
        This is another code block.
        ```

        In this case, only the second code block will be parsed as the action.
        """
        code_block_pat = re.compile(r"^```(\S*)\s*\n|^```\s*$", re.MULTILINE)
        stack = []
        last_valid_block = None
        for match in code_block_pat.finditer(model_response):
            if stack and not match.group(1):  # Closing of a code block
                start = stack.pop()
                # Check if it's not nested within another block
                if not stack:
                    last_valid_block = (start, match)
            elif match.group(1) is not None:  # Opening of a code block
                stack.append(match)
        if last_valid_block:
            start, end = last_valid_block
            thought = model_response[: start.start()] + model_response[end.end() :]
            return thought, model_response[start.end() : end.start()]
        msg = "No action found in model response."
        raise FormatError(msg)


class XMLThoughtActionParser(ParseFunction):
    """
    Expects the model response to be a discussion followed by a command wrapped in XML tags.
    Example:
    Let's look at the files in the current directory.
    <command>
    ls -l
    </command>
    """

    _error_message = """\
    Your output was not formatted correctly. You must always include one discussion and one command as part of your response. Make sure you do not have multiple discussion/command tags.
    Please make sure your output precisely matches the following format:
    """

    def __call__(self, model_response, commands: list[Command], strict=False):
        """
        Parses the action from the output of the API call.
        We assume that the action is the last code block in the model_response.
        We also assume that the action is not nested within another code block.
        This is problematic if the model_response includes many unnamed ``` blocks.
        For instance:
        <command>
        This is a code block.
        </command>
        <command>
        This is another code block.
        </command>

        In this case, only the second code block will be parsed as the action.
        """
        if "<command>" not in model_response or "</command>" not in model_response:
            msg = "No action found in model response."
            raise FormatError(msg)
        # `action` is everything between the last <command> and </command> tags
        start_action = model_response.rfind("<command>") + len("<command>")  # start after the last <command> tag
        end_thought = model_response.rfind("<command>")  # end before the last <command> tag
        end_action = model_response.rfind("</command>")  # end before the last </command> tag
        restart_thought = model_response.rfind("</command>") + len("</command>")  # start after the last </command> tag
        # `thought` is everything not in between <command> and </command> tags (includes after the last </command> tag)
        action = model_response[start_action:end_action]
        thought = model_response[:end_thought] + model_response[restart_thought:]

        return thought.strip(), action.strip()


class EditFormat(ThoughtActionParser):
    """
    Expects the model response to be a discussion followed by a command wrapped in backticks.
    Example:
    We'll replace the contents of the current window with the following:
    ```
    import os
    os.listdir()
    ```
    """

    _error_message = """\
    Your output was not formatted correctly. You must wrap the replacement text in backticks (```).
    Please make sure your output precisely matches the following format:
    COMMENTS
    You can write comments here about what you're going to do if you want.

    ```
    New window contents.
    Make sure you copy the entire contents of the window here, with the required indentation.
    Make the changes to the window above directly in this window.
    Remember that all of the window's contents will be replaced with the contents of this window.
    Don't include line numbers in your response.
    ```
    """


class Identity(ParseFunction):
    """
    This parser does not do any parsing. It just returns the model response as both the thought and action.
    """

    _error_message = """\
    It seems like something went wrong with your output. Please try again.
    """

    def __call__(self, model_response, commands: list[Command], strict=False):
        """
        This doesn't do any parsing. It just returns the model response as the thought and action.
        """
        return model_response, model_response


class JsonParser(ParseFunction):
    """
    Expects the model response to be a JSON object.
    """

    _error_message = """\
    Your output could not be parsed as JSON. Please make sure your output 1) is valid JSON and
    2) Includes the "thought" and "command" fields.

    """

    def __call__(self, model_response, commands: list[Command], strict=False):
        """
        Parses the action from the output of the API call.
        We assume that model output is a JSON object with the following fields:
        {
            "thought": "discussion text here.",
            "command": {
                "arguments": {
                    "arg1": "value1",
                    "arg2": "value2",
                    ...
                },
                "name": "command_name"
            }
        }
        """
        try:
            data = json.loads(model_response)
            if not isinstance(data, dict):
                msg = "Model output is not a JSON object."
                raise FormatError(msg)

            # Check if required keys are present
            required_keys = ["thought", "command"]
            for key in required_keys:
                if key not in data:
                    msg = f"Key '{key}' is missing from model output."
                    raise FormatError(msg)

            # Check structure of 'command' key
            data_command = data["command"]
            if not isinstance(data_command, dict):
                msg = "Value of 'command' key is not a JSON object."
                raise FormatError(msg)

            # Check if required keys are present in 'command' object
            command_keys = ["name"]
            for key in command_keys:
                if key not in data_command:
                    msg = f"Key '{key}' is missing from 'command' object."
                    raise FormatError(msg)

            thought = data["thought"]

            # Generate action
            commands_dict = {c.name: c for c in commands}
            command = commands_dict.get(data_command["name"])
            if command is None:
                action = data_command["name"]
                if "arguments" in data_command:
                    action += " " + " ".join(data_command["arguments"].values())
            else:
                signature = command.signature
                signature = signature.replace("[", "").replace("]", "").replace("<", "{").replace(">", "}")
                signature_args = extract_keys(signature)
                command_args = {k: "" for k in signature_args}

                if "arguments" in data_command:
                    for arg in signature_args:
                        if arg in data_command["arguments"]:
                            value = data_command["arguments"][arg]
                            if should_quote(value, command):
                                value = shlex.quote(value)
                            command_args[arg] = value
                action = signature.format(**command_args)
            action = action.strip()
            return thought, action
        except json.JSONDecodeError:
            msg = "Model output is not valid JSON."
            raise FormatError(msg)


def extract_keys(format_string):
    """
    Given a format string, returns a set of all the keys in the format string.
    """
    formatter = string.Formatter()
    keys = set()
    for _, field_name, _, _ in formatter.parse(format_string):
        if field_name is not None:
            keys.add(field_name)
    return keys


def should_quote(value, command):
    """
    Returns True if the value should be quoted, False otherwise.
    """
    return isinstance(value, str) and command.end_name is None

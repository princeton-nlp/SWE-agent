#!/root/miniconda3/bin/python

# @yaml
# signature: decompile <binary_path> [--function_name <function_name>]
# docstring: Decompile a binary and prints the decompilation of a given function name
# arguments:
#   binary_path:
#       type: file path
#       description: The path to the binary to be decompiled
#       required: true
#   function_name:
#       type: string
#       description: The function name to be decompiled, or main by default
#       required: false

import argparse
import subprocess
import re
import json
import tempfile
from typing import Annotated
from pathlib import Path

GHIDRA_BINARY = "analyzeHeadless"

class Decompile:
    def __init__(self):
        pass

    def __call__(self,
                 path: Annotated[str,"path to the binary to decompile"],
                 function: Annotated[str,"the function to decompile"] = 'main'):
        """Decompile a function from a binary using Ghidra."""
        if path is None or not Path(path).is_file():
            return f"Error: Binary {path} does not exist! Please try again with a real binary file."
        if function is None:
            function = "main"
        return self.decompile(path, function)

    def find_function(self, dis, function):
        """Returns the name of the function found in the dict"""
        if function in dis["functions"]:
            return function
        # Looking for main entry point, so try other names also
        if function == "main":
            if "main" in dis:
                return dis["main"]
            if "_start" in dis["functions"]:
                return "_start"
            if "invoke_main" in dis["functions"]:
                return "invoke_main"
            if "entry" in dis["functions"]:
                return "entry"
        # Check if requesting radare2 unnamed function with address
        if re.match(r"fcn\.[0-9a-f]+$", function):
            addr = function[4:]
            if addr in dis["addresses"]:
                return dis["addresses"][addr]
        # Nothing found
        return None

    def decompile(self, binary: str, function: str) -> str:
        # Look for the decompilation output in "decomp"
        basename = Path(binary).name
        decomp_output_path = Path(f"/ghidra_out/{basename}.decomp.json")
        if not decomp_output_path.exists():
            if not self.run_ghidra(basename, decomp_output_path):
                return f"Error: Decompilation for {binary} not available"
        decomp_output = decomp_output_path.read_text()
        try:
            self.ghidra_out = json.loads(decomp_output)
        except json.JSONDecodeError as e:
            msg = (
                f"Error: Failed to parse Ghidra output {decomp_output!r} for {binary}. "
                "Please report this bug."
            )
            raise ValueError(msg) from e

        if found := self.find_function(self.ghidra_out, function):
            ret = self.ghidra_out["functions"][found]
            if found == function:
                # Exact name found
                return f"Decompilation Found!\n{ret}"
            else:
                return f"Function {function} not found! Instead, here is the decompilation of equivalent function {found}:\n{ret}"
        else:
            funclist = ", ".join(self.ghidra_out['functions'].keys())
            return f"Error: Function {function} not found in {binary}.\nThese are the available functions found: {funclist}"

    def run_ghidra(self, binary: str, output: Path) -> bool:
        """Run ghidra if possible.

        Returns:
            bool: True if successful, False otherwise
        """
        real_binary = Path(binary)
        if not real_binary or not real_binary.exists():
            return False
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subprocess.run(
                [GHIDRA_BINARY, tmpdir, "DummyProj", "-scriptpath", '/ghidra_scripts',
                 "-import", real_binary, "-postscript", "DecompileToJson.java", output],
                check=False, capture_output=True,
            )
            return output.exists()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the contents of a Python file, skipping lengthy function and method definitions."
    )
    parser.add_argument("file_path", type=str, help="The path to the binary to be decompiled")
    parser.add_argument("--function_name", type=str, help="The function name to be decompiled", required=False, default="main")
    args = parser.parse_args()
    print(Decompile()(args.file_path, args.function_name))

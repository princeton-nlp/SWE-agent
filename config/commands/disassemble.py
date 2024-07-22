#!/root/miniconda3/bin/python

# @yaml
# signature: disassemble <binary_path> <function_name>
# docstring: Disassembles a binary and prints the disassembly of a given function name
# arguments:
#   binary_path:
#       type: file path
#       description: The path to the binary to be disassembled
#       required: true
#   function_name:
#       type: string
#       description: The function name to be disassembled, or main by default
#       required: false

import argparse
import subprocess
import re
import json
import tempfile
from typing import Annotated
from pathlib import Path

GHIDRA_BINARY = "analyzeHeadless"

class Disassemble:
    def __init__(self):
        pass

    def __call__(self,
                 path: Annotated[str,"path to the binary to disassemble"],
                 function: Annotated[str,"the function to disassemble"] = 'main'):
        """Disassemble a function from a binary using Ghidra."""
        if path is None or not Path(path).is_file():
            return f"Error: Binary {path} does not exist! Please try again with a real binary file."
        if function is None:
            function = "main"
        return self.disassemble(path, function)

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

    def disassemble(self, binary, function):
        # Look for the disassembly output in "disas"
        basename = Path(binary).name
        disas_output = Path(f"ghidra_out/{basename}.disas.json")
        if not disas_output.exists():
            if not self.run_ghidra(basename, disas_output):
                return f"Error: Disassembly for {binary} not available"
        self.ghidra_out = json.loads(disas_output.read_text())

        if found := self.find_function(self.ghidra_out, function):
            ret = self.ghidra_out["functions"][found]
            if found == function:
                # Exact name found
                return f"Disassembly Found!\n{ret}"
            else:
                return f"Function {function} not found! Instead, here is the disassembly of equivalent function {found}:\n{ret}"
        else:
            funclist = ", ".join(self.ghidra_out["functions"].keys())
            return f"Error: Function {function} not found in {binary}.\nThese are the available functions found: {funclist}"

    def run_ghidra(self, binary, output):
        real_binary = Path(binary)
        if not real_binary or not real_binary.exists():
            return False
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            subprocess.run(
                [GHIDRA_BINARY, tmpdir, "DummyProj", "-scriptpath", '/ghidra_scripts',
                 "-import", real_binary, "-postscript", "DisassembleToJson.java", output],
                check=False, capture_output=True,
            )
            return output.exists()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the contents of a Python file, skipping lengthy function and method definitions."
    )
    parser.add_argument("file_path", type=str, help="The path to the binary to be disassembled")
    parser.add_argument("--function_name", type=str, help="The function name to be disassembled", required=False, default="main")
    args = parser.parse_args()
    print(Disassemble()(args.file_path, args.function_name))

#!/usr/bin/env python3

import ast
import cmd
import argparse
from pwn import *

BUFFER_SIZE = 1024
SERVER_TIMEOUT = 10

def parse_arguments():
    parser = argparse.ArgumentParser(description="Connect to a remote server")

    # Add arguments for IP and port
    parser.add_argument("server_address", type=str, help="Server address")
    parser.add_argument("port", type=int, help="Port number")

    # Parse the arguments
    args = parser.parse_args()

    return args


class NetcatShell(cmd.Cmd):
    intro = "Welcome to the netcat shell. Type help or ? to list commands.\n"
    server = None

    def __init__(self, server_address: str, port: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ip_address = server_address
        self.port = port

    def preloop(self):
        self.do_connect()

    prompt = "(nc) "
    def do_connect(self, arg=""):
        """
        Connecting to the server
        """
        self.server = remote(self.ip_address, self.port)
        data_received_from_server = self._recv()
        if data_received_from_server:
            print("\n-------SERVER RESPONSE-------\n\n", data_received_from_server, "\n\n-------END OF RESPONSE-------\n")

    def _recv(self):
        buffer = recv_data = self.server.recv(BUFFER_SIZE, timeout=SERVER_TIMEOUT)
        while len(recv_data) == BUFFER_SIZE:
            buffer += self.server.recv(BUFFER_SIZE, timeout=SERVER_TIMEOUT)

        return buffer.decode()

    def do_sendline(self, arg):
        """
        Send a single line to the server, line can contain any unicode or byte representation (for example \\x80).
        """
        self.server.sendline(ast.literal_eval(f"b\"{arg}\""))
        print(self._recv())

    def do_close(self, arg):
        """
        Close connection to the server
        """
        self.server.close()

    def do_quit(self, arg):
        """
        Quit the application
        """
        print("Quitting...")
        return True

if __name__ == "__main__":
    args = parse_arguments()
    NetcatShell(args.server_address, args.port).cmdloop()
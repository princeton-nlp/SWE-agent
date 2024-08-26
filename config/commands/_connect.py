#!/usr/bin/env python3


"""This helper command is used for interacting with a remote server.
It opens a shell-like connection to a server, which allows sending and retrieving content from the server.

Usage:
    python _connect.py
"""

import ast
import cmd
from pwn import *
import setproctitle

setproctitle.setproctitle("connect")

BUFFER_SIZE = 1024
SERVER_TIMEOUT = 10


class NetcatShell(cmd.Cmd):
    intro = "Welcome to the netcat shell. Type help or ? to list commands.\n"
    server = None

    prompt = "(nc) "
    def do_connect(self, arg=""):
        """
        Connecting to the server
        """
        args = arg.split()
        self.server = remote(args[0], args[1])
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
    NetcatShell().cmdloop()
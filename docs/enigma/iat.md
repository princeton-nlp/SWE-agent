# Interactive Agent Tool (IAT)

Tools useful for debugging (`gdb`, `radare2`), remote server interaction (`netcat`, `socat`) and penetration testing (`metasploit`) are widely used during CTF problem-solving and by cybersecurity experts. These tools are all interactive, i.e., they wait for user input, evaluate it, and print the results (read-eval-print loop, REPL). 
Current LM agents, which build their ACI around a running shell as central REPL, lack the ability to nest REPLs or start separate REPLs for interactive tools.

In EnIGMA, we build **Interactive Agent Tools (IATs)** that use the same principles from the ACIs introduced in SWE-agent, but are also able to nest new REPL of the desired tool for agent interaction.

Just like how typical programmer or cybersecurity expert uses multiple programs concurrently to build software or defend against cyber attacks, our IAT design enables the agent to use the interactive tools while still having the ability to access the main shell to run other commands. 

As we show in our [paper](TODO: COMPLETE LINK), a baseline agent without our IATs does worse than EnIGMA.

EnIGMA contains interactive tools that we discovered to be immensely helpful for CTF solving during the agent-computer interface design process:

1. We add a debugger (based on `gdb`) that have basic commands for controlling (`start`, `stop`, `step`, `add_breakpoint`), similar to how graphic interfaces for debuggers provide buttons for frequently used operations. We also have a generic command that lets the agent perform arbitrary `gdb` command inside the interactive debugging session.
2. We supply the agent with a special-built server connection tool, instead of having it just `netcat` to servers. The server connection utility that we built has commands for connecting to a server and sending a line with bytes or unicode strings to the server.

Read our paper for more details [here](TODO: COMPLETE LINK).
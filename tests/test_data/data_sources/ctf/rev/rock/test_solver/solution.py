solution = bytearray(b"FLAG23456912365453475897834567")
for i in range(len(solution)):
    solution[i] = ((solution[i]-265)^0x10) & 0xFF
    solution[i] = ((solution[i]-20)^0x50) & 0xFF
solution = solution.decode("utf-8")
print(f"flag{{{solution}}}")

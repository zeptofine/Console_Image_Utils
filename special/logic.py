import logicmin

table = {}
with open("logic.txt", "r") as txt:
    for line in txt:
        line = line.strip().split(":")
        table[line[0]] = line[1]
        inlen = len(line[0])
        outlen = len(line[1])

t = logicmin.TT(inlen, outlen)

for i, o in table.items():
    t.add(i, o)
sols = t.solve()


print("\n".join([f"{key}:{value}" for key, value in table.items()]))
xnames = ['A', 'B', 'C', 'D'][::-1]
print(sols.printN(xnames=xnames))
print()
print(sols.printN(xnames=xnames, syntax='VHDL'))

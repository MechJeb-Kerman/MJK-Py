K=float(input("请输入气体温度(K):"))
p=float(input("请输入气体压强(Pa):"))
v=float(input("请输入气体体积(L):"))
r=8.314
n=p*v/(r*K)
print("气体的物质的量为(mol):",n)

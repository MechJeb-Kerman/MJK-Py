n=int(input("请输入边数:"))
if n<3:
    print("ERROR:TOO SMALL")
elif n>10:
    print("ERROR:TOO BIG")
else:
    print(n,"边形")
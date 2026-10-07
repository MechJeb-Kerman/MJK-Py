a=float(input("请输入三角形一边长: "))
b=float(input("请输入三角形另一边长: "))
c=float(input("请输入三角形第三边长: "))
if a==b==c:
    print("等边三角形")
elif a==b or b==c or a==c:
    print("等腰三角形")
else:
    print("不等边三角形")

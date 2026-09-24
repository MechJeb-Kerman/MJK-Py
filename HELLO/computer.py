print("这是一个给SB用的计算78题目的91牌计算器")
y=0
z=0
m=int(input("SB请输入文本，四则运算亲输入1，一元二次防尘计算请输入2："))
if m==1:
    s=float(input("SB请输入数字"))
    u=input("SB请输入符号")
    if u=="^":
        b=float(input("SB请输入蜜汁树"))
        y=s**b
    else:
        b=float(input("SB请输入数字"))
        if u=="+":
            y=s+b
        elif u=="-":
            y=s-b
        elif u=="/":
            y=s//7
            z=s%b
        elif u=="*":
            y=s*b
        else:
            print("nmd你给我写好了啊")
elif m==2:
    print("我不会，自己算去。实在不行，就告诉你")
else:
    print("nmd你给我写好了啊")
print("经过我114514微秒的思考，结果是：",y)
if z!=0:
    print("余0……啊不是，余",z)
print("再tm给我出这么cs的题我tm就撒了你啊")

#print("二逼",bin(int(y)))















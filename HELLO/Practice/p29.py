t=input("请输入温度(摄氏度):")
v=input("请输入风速(km/h):")
wci=13.12+0.6215*float(t)-11.37*float(v)**0.16+0.3965*float(t)*float(v)**0.16
print("风寒指数为:%d" % wci)

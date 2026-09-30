h=input("请输入自由落体高度(m):")
g=9.8
t=(2*float(h)/g)**0.5
v=g*t
print("自由落体最终速度为:%.2f m/s" % v)

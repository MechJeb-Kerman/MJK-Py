import math
s=input("请输入正多边形的边长:")
n=int(input("请输入正多边形的边数:"))
a=float(s)**2*n/(4*math.tan(math.pi/n))
print("正多边形的面积为:%.2f" % a)

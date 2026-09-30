import math
t1=math.radians(float(input("请输入第一个点的经度:")))
g1=math.radians(float(input("请输入第一个点的纬度:")))
t2=math.radians(float(input("请输入第二个点的经度:")))
g2=math.radians(float(input("请输入第二个点的纬度:")))
dist=6371*math.acos(math.sin(g1)*math.sin(g2)+math.cos(g1)*math.cos(g2)*math.cos(t2-t1))
print("两点之间的距离为:%.2f公里"%dist)

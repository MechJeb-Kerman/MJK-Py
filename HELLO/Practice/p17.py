m=float(input("请输入水的质量或体积(g/ml):"))
t=float(input("请输入水的变化温度(°C):"))
q=m*4.186*t
print("水吸收或放出的热量为(J):",q)
kwh=q/3600000
cost=kwh*8.9
print("电费为(美分):",cost)

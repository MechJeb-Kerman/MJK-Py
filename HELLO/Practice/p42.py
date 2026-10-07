y=input("请输入音符名称")
x=int(y[1])
z=y[0]
if z=="C":
    f=261.63/2**(4-x)
elif z=="D":
    f=293.66/2**(4-x)
elif z=="E":
    f=329.63/2**(4-x)
elif z=="F":
    f=349.23/2**(4-x)
elif z=="G":
    f=392/2**(4-x)
elif z=="A":
    f=440/2**(4-x)
elif z=="B":
    f=493.88/2**(4-x)
else:
    print("ERROR:名称错误")
print(y,"的频率为",f,"Hz")

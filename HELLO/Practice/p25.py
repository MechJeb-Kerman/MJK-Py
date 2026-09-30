seconds=int(input("请输入秒数:"))
d=seconds//(24*60*60)
h=(seconds-d*24*60*60)//(60*60)
m=(seconds-d*24*60*60-h*60*60)//60
s=seconds-d*24*60*60-h*60*60-m*60
print("时间为:%d天%d小时%d分钟%d秒" % (d, h, m, s))

day=int(input("请输入天数:"))
hour=int(input("请输入小时数:"))
minute=int(input("请输入分钟数:"))
second=int(input("请输入秒数:"))
total_seconds=day*24*60*60+hour*60*60+minute*60+second
print("总秒数为:%d" % total_seconds)

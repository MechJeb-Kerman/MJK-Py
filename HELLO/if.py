num=float(input("请输入数字"))
if num>0:
    adjective=" "
    if num>=1000000:
        adjective="真的很大"
    elif num>1000:
        adjective="很大"
    result="这个正数"+adjective
elif num<0:
    result="这是个负数"
else:
    result="这是零"
print(result)



dB=float(input("请输入分贝值: "))
if dB<40:
    print("比安静房间还安静")
elif dB==40:
    print("安静房间")
elif dB<70:
    print("介于安静房间和闹钟之间")
elif dB==70:
    print("闹钟")
elif dB<106:
    print("介于闹钟和割草机之间")
elif dB==106:
    print("割草机")
elif dB<130:
    print("介于割草机和手提钻之间")
else:
    print("手提钻")

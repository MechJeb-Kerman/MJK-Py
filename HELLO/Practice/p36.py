hum_year=int(input("请输入人类年:"))
if hum_year<0:
    print("错误:负数")
elif hum_year<2:
    dog_year=10.5*hum_year
    print("狗年为:",dog_year)
else:
    dog_year=21+7*(hum_year-2)
    print("狗年为:",dog_year)

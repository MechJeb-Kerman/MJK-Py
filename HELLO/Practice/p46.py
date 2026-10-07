place=input("请输入位置: ")
letter=place[0]
number=place[1]
if letter == "a" or letter == "c" or letter == "e" or letter == "g":
    if int(number) % 2 == 1:
        print("黑色")
    else:
        print("白色")
elif letter == "b" or letter == "d" or letter == "f" or letter == "h":
    if int(number) % 2 == 1:
        print("白色")
    else:
        print("黑色")
else:
    print("ERROR:位置错误")

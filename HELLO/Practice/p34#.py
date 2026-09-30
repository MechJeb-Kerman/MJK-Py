#小数点需对齐，未完成
bread=int(input("请输入面包的数量:"))
bread_price=3.49
bread_1=int(input("请输入旧面包的数量:"))
bread_1_price=3.49*0.6
print("新鲜面包的总价为:%.2f" % (bread*bread_price))
print("旧面包的总价为:%.2f" % (bread_1*bread_1_price))
print("面包的总价为:%.2f" % (bread*bread_price+bread_1*bread_1_price))

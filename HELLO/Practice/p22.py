s1=input("请输入三角形一边长:")
s2=input("请输入三角形另一边长:")
s3=input("请输入三角形第三边长:")
s=(float(s1)+float(s2)+float(s3))/2
a=(s*(s-float(s1))*(s-float(s2))*(s-float(s3)))**0.5
print("三角形的面积为:%.2f" % a)

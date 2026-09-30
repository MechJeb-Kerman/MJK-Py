cf=float(input("餐费(CNY):"))
cs=0.025*cf
cx=0.18*cf
ca=cf+cs+cx
print("本餐税费为%.2fCNY"%cs)
print("本餐小费为%.2fCNY"%cx)
print("总餐费为%.2fCNY"%ca)

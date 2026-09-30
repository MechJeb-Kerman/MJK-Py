msg = "Hello World" 
print(msg)
msg = "Roll a dice!"
print(msg)
import turtle
i=0
while i<12:
    i+=1
    turtle.forward(10)
    for j in range(4):
        turtle.speed(0)
        turtle.forward(90)
        turtle.left(90)
        turtle.circle(100)
print('end')
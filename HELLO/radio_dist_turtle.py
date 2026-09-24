import math
import turtle

print("计算通信方位角和大圆距离与示意图程序")
def great_circle(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist = 6371.0088 * c

    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlam)
    az = (math.degrees(math.atan2(x, y)) + 360) % 360
    return dist, az


def both_azimuths(lat1, lon1, lat2, lon2):

    dist, az_forward = great_circle(lat1, lon1, lat2, lon2)
    _,    az_backward = great_circle(lat2, lon2, lat1, lon1)
    return dist, az_forward, az_backward


def make_projector(width, height, lat_min, lat_max, lon_min, lon_max):
    def project(lat, lon):
        x = (lon - lon_min) / (lon_max - lon_min) * width  - width/2
        y = (lat - lat_min) / (lat_max - lat_min) * height - height/2
        return x, y
    return project


def draw(lat1, lon1, name1, lat2, lon2, name2):

    W, H = 700, 500
    screen = turtle.Screen()
    screen.setup(W+80, H+80)
    screen.title("通信方位角与大圆距离")
    screen.bgcolor("#eaf4ff")

    lat_min = min(lat1, lat2) - 5
    lat_max = max(lat1, lat2) + 5
    lon_min = min(lon1, lon2) - 5
    lon_max = max(lon1, lon2) + 5
    project = make_projector(W, H, lat_min, lat_max, lon_min, lon_max)

    t = turtle.Turtle()
    t.speed(0)
    t.hideturtle()

    t.pencolor("#b8d4f0")
    t.pensize(1)
    for lat in range(int(lat_min), int(lat_max)+1, 5):
        x1, y1 = project(lat, lon_min)
        x2, y2 = project(lat, lon_max)
        t.penup(); t.goto(x1, y1); t.pendown(); t.goto(x2, y2)
    for lon in range(int(lon_min), int(lon_max)+1, 5):
        x1, y1 = project(lat_min, lon)
        x2, y2 = project(lat_max, lon)
        t.penup(); t.goto(x1, y1); t.pendown(); t.goto(x2, y2)

    dist, az_fwd, az_bwd = both_azimuths(lat1, lon1, lat2, lon2)

    print(f"{name1}(发) -> {name2}(收)")
    print(f"大圆距离:           {dist:.1f} km")
    print(f"{name1} 看 {name2} 的方位角: {az_fwd:.1f}°")
    print(f"{name2} 看 {name1} 的方位角: {az_bwd:.1f}°")

    x1, y1 = project(lat1, lon1)
    x2, y2 = project(lat2, lon2)

    t.penup(); t.goto(x1, y1); t.pendown()
    t.pencolor("red"); t.pensize(3)
    t.goto(x2, y2)

    def draw_arrow(x, y, az_deg, color, length=70):
        t.penup(); t.goto(x, y)
        t.setheading(90 - az_deg)
        t.pencolor(color); t.pensize(2)
        t.pendown()
        t.forward(length)
        t.left(150); t.forward(12); t.backward(12)
        t.right(300); t.forward(12); t.backward(12)
        t.setheading(0)

    draw_arrow(x1, y1, az_fwd, "darkgreen")
    draw_arrow(x2, y2, az_bwd, "purple")

    def mark(x, y, name, color):
        t.penup(); t.goto(x, y)
        t.dot(12, color)
        t.goto(x + 8, y + 8)
        t.pencolor("black")
        t.write(name, font=("Arial", 12, "bold"))

    mark(x1, y1, f"{name1}(发)", "blue")
    mark(x2, y2, f"{name2}(收)", "orange")

    t.penup(); t.goto(-W/2, H/2 + 20)
    t.pencolor("black")
    t.write(
        f"距离 {dist:.1f} km    "
        f"{name1}->{name2}: {az_fwd:.1f}°    "
        f"{name2}->{name1}: {az_bwd:.1f}°",
        font=("Arial", 13, "bold")
    )

    turtle.done()

if __name__ == "__main__":
    lon1 = float(input("请输入发信点经度"))
    lat1 = float(input("请输入发信点纬度"))
    lon2 = float(input("请输入收信点经度"))
    lat2 = float(input("请输入收信点纬度"))
    name1 = input("请输入发信点名称")
    name2 = input("请输入收信点名称")
    print("已开启示意图")
    draw(lat1, lon1, name1, lat2, lon2, name2)
    
#made by BVVD
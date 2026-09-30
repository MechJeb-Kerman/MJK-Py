import pygame

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Demo")

clock = pygame.time.Clock()
running = True

x, y = WIDTH // 2, HEIGHT // 2
speed = 5

while running:
    # 1. 处理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 2. 获取按键状态
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        x -= speed
    if keys[pygame.K_RIGHT]:
        x += speed
    if keys[pygame.K_UP]:
        y -= speed
    if keys[pygame.K_DOWN]:
        y += speed

    # 3. 绘制
    screen.fill((30, 30, 30))  # 背景色
    pygame.draw.circle(screen, (0, 200, 255), (x, y), 30)

    # 4. 刷新屏幕
    pygame.display.flip()

    # 5. 控制帧率
    clock.tick(60)

pygame.quit()

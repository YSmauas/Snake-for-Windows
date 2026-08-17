import pygame
import time
import random
import os
import json

pygame.init()

# --- הגדרות צבעים (סגנון רטרו נוקיה) ---
BG_COLOR = (135, 170, 101)
SNAKE_COLOR = (34, 45, 34)
APPLE_COLOR = (200, 0, 0)
TEXT_COLOR = (20, 20, 20)

# --- הגדרות מסך ---
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("סנייק רטרו - נוקיה 225")
clock = pygame.time.Clock()

BLOCK_SIZE = 20
SCORE_FILE = "high_score.json"

try:
    font_style = pygame.font.SysFont("arial", 25, bold=True)
    score_font = pygame.font.SysFont("arial", 20, bold=True)
except:
    font_style = pygame.font.Font(None, 25)
    score_font = pygame.font.Font(None, 20)

def get_high_score():
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r") as file:
            return json.load(file).get("high_score", 0)
    return 0

def save_high_score(score):
    with open(SCORE_FILE, "w") as file:
        json.dump({"high_score": score}, file)

def draw_text(text, color, y_offset=0, font=font_style):
    hebrew_text = text[::-1]
    mesg = font.render(hebrew_text, True, color)
    text_rect = mesg.get_rect(center=(WIDTH / 2, HEIGHT / 2 + y_offset))
    screen.blit(mesg, text_rect)

def draw_snake(block_size, snake_list):
    for x in snake_list:
        pygame.draw.rect(screen, SNAKE_COLOR, [x[0], x[1], block_size, block_size], border_radius=3)

def gameLoop(speed):
    game_over = False
    game_close = False

    x1 = WIDTH / 2
    y1 = HEIGHT / 2
    x1_change = 0
    y1_change = 0

    snake_list = []
    length_of_snake = 1
    score = 0
    high_score = get_high_score()

    foodx = round(random.randrange(0, WIDTH - BLOCK_SIZE) / 20.0) * 20.0
    foody = round(random.randrange(0, HEIGHT - BLOCK_SIZE) / 20.0) * 20.0

    while not game_over:
        while game_close:
            screen.fill(BG_COLOR)
            if score > high_score:
                save_high_score(score)
                high_score = score
                draw_text("!שיא חדש!", APPLE_COLOR, -60)
            
            draw_text("נפסלת!", APPLE_COLOR, -30)
            draw_text("לחץ C כדי לשחק שוב או Q ליציאה", TEXT_COLOR, 10)
            draw_text(f"הניקוד שלך: {score}", TEXT_COLOR, 50, score_font)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    if event.key == pygame.K_c:
                        gameLoop(speed)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and x1_change == 0:
                    x1_change = -BLOCK_SIZE
                    y1_change = 0
                elif event.key == pygame.K_RIGHT and x1_change == 0:
                    x1_change = BLOCK_SIZE
                    y1_change = 0
                elif event.key == pygame.K_UP and y1_change == 0:
                    y1_change = -BLOCK_SIZE
                    x1_change = 0
                elif event.key == pygame.K_DOWN and y1_change == 0:
                    y1_change = BLOCK_SIZE
                    x1_change = 0

        if x1 >= WIDTH: x1 = 0
        elif x1 < 0: x1 = WIDTH - BLOCK_SIZE
        if y1 >= HEIGHT: y1 = 0
        elif y1 < 0: y1 = HEIGHT - BLOCK_SIZE

        x1 += x1_change
        y1 += y1_change
        screen.fill(BG_COLOR)
        
        pygame.draw.rect(screen, APPLE_COLOR, [foodx, foody, BLOCK_SIZE, BLOCK_SIZE], border_radius=10)
        
        snake_head = []
        snake_head.append(x1)
        snake_head.append(y1)
        snake_list.append(snake_head)
        
        if len(snake_list) > length_of_snake:
            del snake_list[0]

        for x in snake_list[:-1]:
            if x == snake_head:
                game_close = True

        draw_snake(BLOCK_SIZE, snake_list)
        
        score_text = score_font.render(f"שיא: {high_score} | ניקוד: {score}"[::-1], True, TEXT_COLOR)
        screen.blit(score_text, [10, 10])
        
        pygame.display.update()

        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(0, WIDTH - BLOCK_SIZE) / 20.0) * 20.0
            foody = round(random.randrange(0, HEIGHT - BLOCK_SIZE) / 20.0) * 20.0
            length_of_snake += 1
            score += 10

        clock.tick(speed)

    pygame.quit()
    quit()

def main_menu():
    speed = 10
    menu = True
    while menu:
        screen.fill(BG_COLOR)
        draw_text("סנייק - נוקיה 225", TEXT_COLOR, -100, font_style)
        draw_text("1. התחל משחק", TEXT_COLOR, -30)
        draw_text("2. מהירות (כרגע: " + ("קל" if speed==7 else "רגיל" if speed==10 else "קשה") + ")", TEXT_COLOR, 10)
        draw_text("3. יציאה", TEXT_COLOR, 50)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    gameLoop(speed)
                elif event.key == pygame.K_2:
                    if speed == 7: speed = 10
                    elif speed == 10: speed = 15
                    else: speed = 7
                elif event.key == pygame.K_3:
                    pygame.quit()
                    quit()

if __name__ == "__main__":
    main_menu()

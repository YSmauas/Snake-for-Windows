import pygame
import random
import os
import sys
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
pygame.display.set_caption("Snake for Windows - נוקיה 225")
clock = pygame.time.Clock()

BLOCK_SIZE = 20

# נתיב בטוח גם כשהמשחק ארוז ל-exe (PyInstaller --onefile):
# ב-exe, sys.executable מצביע על מיקום הקובץ המורץ עצמו.
# בהרצת סקריפט רגיל, משתמשים ב-__file__.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SCORE_FILE = os.path.join(APP_DIR, "high_score.json")

try:
    font_style = pygame.font.SysFont("arial", 25, bold=True)
    score_font = pygame.font.SysFont("arial", 20, bold=True)
    small_font = pygame.font.SysFont("arial", 16, bold=True)
except Exception:
    font_style = pygame.font.Font(None, 25)
    score_font = pygame.font.Font(None, 20)
    small_font = pygame.font.Font(None, 16)


def get_high_score():
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, "r", encoding="utf-8") as file:
                return json.load(file).get("high_score", 0)
        except (json.JSONDecodeError, OSError):
            # קובץ פגום/לא קריא - מתחילים מ-0 במקום לקרוס
            return 0
    return 0


def save_high_score(score):
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as file:
            json.dump({"high_score": score}, file)
    except OSError:
        pass  # אין הרשאת כתיבה - לא קריטי, פשוט לא נשמור הפעם


# הפיכת טקסט עברי בלי לשבור מספרים/אנגלית בתוך אותה שורה:
# הופכים את סדר ה"מילים", ואת התווים בתוך כל מילה עברית בלבד -
# כך "שיא: 10" לא הופך ל-"01 :שיא".
def rtl(text):
    words = text.split(" ")
    return " ".join(
        w[::-1] if all(ord(c) > 1424 for c in w if c.isalpha()) else w
        for w in reversed(words)
    )


def draw_text(text, color, y_offset=0, font=font_style):
    mesg = font.render(rtl(text), True, color)
    text_rect = mesg.get_rect(center=(WIDTH / 2, HEIGHT / 2 + y_offset))
    screen.blit(mesg, text_rect)


def draw_snake(block_size, snake_list):
    for i, x in enumerate(snake_list):
        # הראש מעט כהה יותר מהגוף - עוזר להתמצא לאיזה כיוון הנחש פונה
        color = SNAKE_COLOR if i < len(snake_list) - 1 else (20, 28, 20)
        pygame.draw.rect(screen, color, [x[0], x[1], block_size, block_size], border_radius=3)


def spawn_food(snake_list):
    # לוודא שהתפוח לא נוצר בתוך גוף הנחש
    while True:
        fx = round(random.randrange(0, WIDTH - BLOCK_SIZE) / 20.0) * 20.0
        fy = round(random.randrange(0, HEIGHT - BLOCK_SIZE) / 20.0) * 20.0
        if [fx, fy] not in snake_list:
            return fx, fy


def pause_screen():
    """מסך השהיה - עוצר את המשחק בלי לצייר מעל הנחש בלולאה עסוקה מיותרת."""
    paused = True
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(120)
    overlay.fill((0, 0, 0))
    while paused:
        screen.blit(overlay, (0, 0))
        draw_text("השהייה", TEXT_COLOR, -20)
        draw_text("לחץ P כדי להמשיך", TEXT_COLOR, 20, score_font)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                paused = False
        clock.tick(15)


def gameLoop(base_speed):
    """
    שימוש ב-while חיצוני עם restart flag במקום רקורסיה -
    כך "שחק שוב" לא צובר call stack ולא גורם ל-RecursionError.
    """
    restart = True
    while restart:
        restart = False
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
        speed = base_speed  # מהירות נוכחית - תעלה בהדרגה ככל שהנחש גדל

        foodx, foody = spawn_food(snake_list)

        while not game_over:
            while game_close:
                screen.fill(BG_COLOR)
                if score > high_score:
                    save_high_score(score)
                    high_score = score
                    draw_text("!שיא חדש!", APPLE_COLOR, -60)

                draw_text("נפסלת!", APPLE_COLOR, -30)
                draw_text("לחץ C לשחק שוב, Q לתפריט", TEXT_COLOR, 10)
                draw_text(f"הניקוד שלך: {score}", TEXT_COLOR, 50, score_font)
                pygame.display.update()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_q:
                            game_over = True
                            game_close = False
                        if event.key == pygame.K_c:
                            game_over = True
                            game_close = False
                            restart = True

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
                    elif event.key == pygame.K_p:
                        pause_screen()

            # תזוזה קודם, ואז בדיקת גלישת קיר - כך אין פריים
            # שבו הנחש מצויר רגע אחד מחוץ למסך.
            x1 += x1_change
            y1 += y1_change

            if x1 >= WIDTH:
                x1 = 0
            elif x1 < 0:
                x1 = WIDTH - BLOCK_SIZE
            if y1 >= HEIGHT:
                y1 = 0
            elif y1 < 0:
                y1 = HEIGHT - BLOCK_SIZE

            screen.fill(BG_COLOR)
            pygame.draw.rect(screen, APPLE_COLOR, [foodx, foody, BLOCK_SIZE, BLOCK_SIZE], border_radius=10)

            snake_head = [x1, y1]
            snake_list.append(snake_head)

            if len(snake_list) > length_of_snake:
                del snake_list[0]

            for segment in snake_list[:-1]:
                if segment == snake_head:
                    game_close = True

            draw_snake(BLOCK_SIZE, snake_list)

            score_text = score_font.render(rtl(f"שיא: {high_score} | ניקוד: {score}"), True, TEXT_COLOR)
            screen.blit(score_text, [10, 10])
            pause_hint = small_font.render(rtl("P להשהיה"), True, TEXT_COLOR)
            screen.blit(pause_hint, [WIDTH - pause_hint.get_width() - 10, 12])

            pygame.display.update()

            if x1 == foodx and y1 == foody:
                foodx, foody = spawn_food(snake_list)
                length_of_snake += 1
                score += 10
                # קושי עולה בהדרגה: כל 5 תפוחים המהירות עולה, עד תקרה סבירה
                if length_of_snake % 5 == 0:
                    speed = min(speed + 1, base_speed + 8)

            clock.tick(speed)


def main_menu():
    speed = 10
    menu = True
    while menu:
        screen.fill(BG_COLOR)
        draw_text("Snake for Windows", TEXT_COLOR, -120, font_style)
        draw_text("נוקיה 225 - מהדורה רטרו", TEXT_COLOR, -90, score_font)
        draw_text("1. התחל משחק", TEXT_COLOR, -30)
        draw_text("2. מהירות (כרגע: " + ("קל" if speed == 7 else "רגיל" if speed == 10 else "קשה") + ")", TEXT_COLOR, 10)
        draw_text("3. יציאה", TEXT_COLOR, 50)
        draw_text(f"שיא נוכחי: {get_high_score()}", TEXT_COLOR, 90, score_font)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    gameLoop(speed)
                elif event.key == pygame.K_2:
                    if speed == 7:
                        speed = 10
                    elif speed == 10:
                        speed = 15
                    else:
                        speed = 7
                elif event.key == pygame.K_3:
                    pygame.quit()
                    sys.exit()


if __name__ == "__main__":
    main_menu()

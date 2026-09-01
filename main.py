import pygame
import random
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess

pygame.init()

# --- מספר הגרסה הנוכחי (חייב להתאים לתגית ה-Release בגיטהאב, למשל v1.0.0) ---
VERSION = "1.0.0"
GITHUB_REPO = "YSmauas/Snake-for-Windows"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# --- הגדרות צבעים (סגנון רטרו נוקיה) ---
BG_COLOR = (135, 170, 101)
GRID_LINE_COLOR = (125, 160, 93)     # קווי רשת עדינים על הרקע, כמו במסך LCD ישן
BEZEL_COLOR = (60, 80, 45)           # מסגרת כהה סביב המסך - כמו מכשיר נוקיה
SNAKE_HEAD_COLOR = (18, 26, 18)
SNAKE_BODY_COLOR = (34, 45, 34)
SNAKE_TAIL_COLOR = (70, 95, 65)      # הזנב בהיר יותר מהראש - יוצר מדרג עומק
SNAKE_OUTLINE_COLOR = (15, 20, 15)
APPLE_COLOR = (200, 0, 0)
APPLE_HIGHLIGHT = (255, 150, 150)
LEAF_COLOR = (40, 130, 40)
STEM_COLOR = (90, 60, 30)
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

def _load_hebrew_font(size, bold=False):
    """
    טוען גופן שתומך בעברית בצורה אמינה.

    pygame.font.SysFont() מחפש גופן "לפי שם" - וזה מנגנון לא אמין בתוך exe
    מקומפל, בעיקר במחשבים עם הגדרות שפה/אזור שאינן en-US: הוא נכשל בשקט
    (בלי לזרוק שגיאה!) ונופל חזרה לגופן ברירת המחדל הפנימי של pygame, שלא
    כולל תווי עברית בכלל - וזה בדיוק מה שגורם לריבועים ריקים (□) על המסך.

    הפתרון: לטעון את קובץ הגופן ישירות לפי נתיב בדיסק (לא לפי שם), מה
    שעוקף את מנגנון ה-matching הבעייתי. arial.ttf קיים כמעט בוודאות בכל
    מחשב Windows.
    """
    candidate_paths = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\davidlibre.ttf",
        r"C:\Windows\Fonts\times.ttf",
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                font = pygame.font.Font(path, size)
                font.set_bold(bold)
                return font
            except Exception:
                continue

    # לא נמצא קובץ גופן ישיר - ניסיון אחרון עם match_font (חיפוש לפי שם)
    fallback_path = pygame.font.match_font("arial,tahoma,segoeui,davidlibre", bold=bold)
    if fallback_path:
        try:
            return pygame.font.Font(fallback_path, size)
        except Exception:
            pass

    # מוצא אחרון - גופן ברירת המחדל של pygame (לא יתמוך בעברית, אך עדיף מקריסה)
    return pygame.font.Font(None, size)


font_style = _load_hebrew_font(25, bold=True)
score_font = _load_hebrew_font(20, bold=True)
small_font = _load_hebrew_font(16, bold=True)


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


def _parse_version(v):
    """'v1.2.3' / '1.2.3' -> (1, 2, 3), כדי להשוות גרסאות כמספרים ולא כמחרוזות."""
    v = v.lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update():
    """
    בודק מול ה-Release האחרון בגיטהאב אם יש גרסה חדשה מהגרסה הנוכחית.
    מחזיר את פרטי ה-Release (dict) אם יש עדכון, אחרת None.
    לעולם לא מפיל את המשחק - אין אינטרנט / גיטהאב לא זמין = פשוט לא מוצע עדכון.
    """
    try:
        req = urllib.request.Request(
            LATEST_RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "Snake-for-Windows"},
        )
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.load(response)
        remote_tag = data.get("tag_name", "")
        if _parse_version(remote_tag) > _parse_version(VERSION):
            return data
    except Exception:
        pass
    return None


def _find_exe_asset_url(release_data):
    for asset in release_data.get("assets", []):
        if asset.get("name", "").lower().endswith(".exe"):
            return asset.get("browser_download_url")
    return None


def apply_update(release_data):
    """
    מוריד את ה-exe מה-Release האחרון ומחליף את קובץ ה-exe הרץ כרגע.
    עובד רק בגרסת exe מקומפלת (לא כשמריצים python main.py).
    בהצלחה - סוגר את המשחק כדי לאפשר להחלפה לקרות, ופותח מחדש אוטומטית.
    """
    if not getattr(sys, "frozen", False):
        return False, "עדכון אוטומטי זמין רק בגרסת ה-exe. הריצו python update.py לעדכון קוד המקור."

    exe_url = _find_exe_asset_url(release_data)
    if not exe_url:
        return False, "לא נמצא קובץ exe בגרסה החדשה."

    current_exe = sys.executable
    new_exe_path = os.path.join(APP_DIR, "Snake_update.exe")

    try:
        urllib.request.urlretrieve(exe_url, new_exe_path)
    except Exception:
        return False, "הורדת העדכון נכשלה. בדקו חיבור לאינטרנט ונסו שוב."

    pid = os.getpid()
    bat_path = os.path.join(APP_DIR, "_apply_update.bat")
    bat_content = (
        "@echo off\r\n"
        ":waitloop\r\n"
        f'tasklist /FI "PID eq {pid}" ^| find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "    timeout /t 1 /nobreak >nul\r\n"
        "    goto waitloop\r\n"
        ")\r\n"
        f'move /y "{new_exe_path}" "{current_exe}" >nul\r\n'
        f'start "" "{current_exe}"\r\n'
        'del "%~f0"\r\n'
    )
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=APP_DIR,
    )
    pygame.quit()
    sys.exit(0)


# הפיכת טקסט עברי בלי לשבור מספרים/אנגלית בתוך אותה שורה:
# הופכים את סדר ה"מילים", ואת התווים בתוך כל מילה עברית בלבד -
# כך "שיא: 10" לא הופך ל-"01 :שיא".
_BRACKET_MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{"}


def rtl(text):
    # אם אין בטקסט אף תו עברי (למשל כותרת אנגלית טהורה כמו "Snake for
    # Windows"), אין שום סיבה להפוך את סדר המילים - הוא כבר תקין כמו שהוא.
    if not any(1424 < ord(c) < 1536 for c in text):
        return text

    def flip_word(w):
        if any(1424 < ord(c) < 1536 for c in w):
            # הופכים את סדר התווים, ובנוסף "משקפים" סוגריים - אחרת "(" ו-")"
            # יוצגו הפוך ויזואלית אחרי שהפכנו את הטקסט.
            return "".join(_BRACKET_MIRROR.get(c, c) for c in reversed(w))
        return w

    words = text.split(" ")
    return " ".join(flip_word(w) for w in reversed(words))


def draw_text(text, color, y_offset=0, font=font_style):
    mesg = font.render(rtl(text), True, color)
    text_rect = mesg.get_rect(center=(WIDTH / 2, HEIGHT / 2 + y_offset))
    screen.blit(mesg, text_rect)


def draw_grid():
    """קווי רשת עדינים על הרקע - נותן תחושה קלאסית של מסך LCD ישן."""
    for gx in range(0, WIDTH, BLOCK_SIZE):
        pygame.draw.line(screen, GRID_LINE_COLOR, (gx, 0), (gx, HEIGHT), 1)
    for gy in range(0, HEIGHT, BLOCK_SIZE):
        pygame.draw.line(screen, GRID_LINE_COLOR, (0, gy), (WIDTH, gy), 1)


def draw_bezel():
    """מסגרת כהה סביב כל המסך - מזכירה את המראה של מכשיר נוקיה ישן."""
    pygame.draw.rect(screen, BEZEL_COLOR, (0, 0, WIDTH, HEIGHT), width=6)


def draw_snake(block_size, snake_list, direction=(1, 0)):
    n = len(snake_list)
    for i, seg in enumerate(snake_list):
        rect = [seg[0], seg[1], block_size, block_size]
        is_head = i == n - 1
        if is_head:
            color = SNAKE_HEAD_COLOR
        else:
            # מדרג צבע קל מהזנב (בהיר) לכיוון הראש (כהה) - נותן תחושת עומק
            t = i / max(n - 1, 1)
            color = tuple(
                int(SNAKE_TAIL_COLOR[c] + (SNAKE_BODY_COLOR[c] - SNAKE_TAIL_COLOR[c]) * t)
                for c in range(3)
            )
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, SNAKE_OUTLINE_COLOR, rect, width=1, border_radius=6)

    if not snake_list:
        return

    # עיניים על הראש, ממוקמות לפי כיוון התנועה - כך נראה שהנחש "מביט" קדימה
    hx, hy = snake_list[-1]
    dx, dy = direction
    if dx == 0 and dy == 0:
        dx = 1  # בעמידה - ברירת מחדל להסתכל ימינה
    if dx == 1:
        eyes = [(hx + block_size - 6, hy + 5), (hx + block_size - 6, hy + block_size - 5)]
    elif dx == -1:
        eyes = [(hx + 6, hy + 5), (hx + 6, hy + block_size - 5)]
    elif dy == 1:
        eyes = [(hx + 5, hy + block_size - 6), (hx + block_size - 5, hy + block_size - 6)]
    else:
        eyes = [(hx + 5, hy + 6), (hx + block_size - 5, hy + 6)]
    for ex, ey in eyes:
        pygame.draw.circle(screen, (235, 235, 225), (int(ex), int(ey)), 2)


def draw_food(foodx, foody):
    """תפוח עם גבעול ועלה קטן, במקום עיגול אדום שטוח."""
    cx = foodx + BLOCK_SIZE / 2
    cy = foody + BLOCK_SIZE / 2
    radius = BLOCK_SIZE / 2 - 1

    pygame.draw.circle(screen, APPLE_COLOR, (int(cx), int(cy) + 2), int(radius))
    pygame.draw.circle(screen, APPLE_HIGHLIGHT, (int(cx - radius / 2.5), int(cy - radius / 2.5) + 2), 2)
    pygame.draw.line(screen, STEM_COLOR, (cx, foody + 2), (cx + 3, foody - 3), 2)

    leaf_rect = pygame.Rect(0, 0, 8, 5)
    leaf_rect.center = (cx + 6, foody - 1)
    pygame.draw.ellipse(screen, LEAF_COLOR, leaf_rect)


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
        draw_grid()
        screen.blit(overlay, (0, 0))
        draw_text("השהייה", TEXT_COLOR, -20)
        draw_text("לחץ P כדי להמשיך", TEXT_COLOR, 20, score_font)
        draw_bezel()
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
                draw_grid()
                if score > high_score:
                    save_high_score(score)
                    high_score = score
                    draw_text("!שיא חדש!", APPLE_COLOR, -60)

                draw_text("נפסלת!", APPLE_COLOR, -30)
                draw_text("לחץ C לשחק שוב, Q לתפריט", TEXT_COLOR, 10)
                draw_text(f"הניקוד שלך: {score}", TEXT_COLOR, 50, score_font)
                draw_bezel()
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
            draw_grid()
            draw_food(foodx, foody)

            snake_head = [x1, y1]
            snake_list.append(snake_head)

            if len(snake_list) > length_of_snake:
                del snake_list[0]

            for segment in snake_list[:-1]:
                if segment == snake_head:
                    game_close = True

            move_dir = (
                1 if x1_change > 0 else -1 if x1_change < 0 else 0,
                1 if y1_change > 0 else -1 if y1_change < 0 else 0,
            )
            draw_snake(BLOCK_SIZE, snake_list, direction=move_dir)

            score_panel = pygame.Surface((WIDTH, 34))
            score_panel.set_alpha(90)
            score_panel.fill((0, 0, 0))
            screen.blit(score_panel, (0, 0))

            score_text = score_font.render(rtl(f"שיא: {high_score} | ניקוד: {score}"), True, (240, 240, 235))
            screen.blit(score_text, [10, 8])
            pause_hint = small_font.render(rtl("P להשהיה"), True, (240, 240, 235))
            screen.blit(pause_hint, [WIDTH - pause_hint.get_width() - 10, 10])

            draw_bezel()
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
    update_info = check_for_update()  # נבדק פעם אחת בכניסה לתפריט, לא בכל פריים
    update_message = ""

    while menu:
        screen.fill(BG_COLOR)
        draw_grid()
        draw_text("Snake for Windows", TEXT_COLOR, -120, font_style)
        draw_text(f"נוקיה 225 - מהדורה רטרו (v{VERSION})", TEXT_COLOR, -90, score_font)
        draw_text("1. התחל משחק", TEXT_COLOR, -30)
        draw_text("2. מהירות (כרגע: " + ("קל" if speed == 7 else "רגיל" if speed == 10 else "קשה") + ")", TEXT_COLOR, 10)
        draw_text("3. יציאה", TEXT_COLOR, 50)
        draw_text(f"שיא נוכחי: {get_high_score()}", TEXT_COLOR, 90, score_font)
        if update_info:
            draw_text(f"4. לחצו לעדכון לגרסה {update_info.get('tag_name', '')}!", (0, 90, 0), 130, small_font)
        if update_message:
            draw_text(update_message, APPLE_COLOR, 160, small_font)
        draw_bezel()
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
                elif event.key == pygame.K_4 and update_info:
                    ok, msg = apply_update(update_info)
                    if not ok:
                        update_message = msg
                        update_info = None


if __name__ == "__main__":
    main_menu()

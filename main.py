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

# --- צבעי לוח המשחק (סגנון רטרו נוקיה) - אלה נשארים בדיוק כמו שהיו ---
BG_COLOR = (135, 170, 101)
GRID_LINE_COLOR = (125, 160, 93)
BEZEL_COLOR = (60, 80, 45)           # מסגרת כהה סביב לוח המשחק בלבד
SNAKE_HEAD_COLOR = (18, 26, 18)
SNAKE_BODY_COLOR = (34, 45, 34)
SNAKE_TAIL_COLOR = (70, 95, 65)
SNAKE_OUTLINE_COLOR = (15, 20, 15)
APPLE_COLOR = (200, 0, 0)
APPLE_HIGHLIGHT = (255, 150, 150)
LEAF_COLOR = (40, 130, 40)
STEM_COLOR = (90, 60, 30)
SPECIAL_APPLE_COLOR = (255, 215, 0)

# --- צבעי ה"מסגרת" המודרנית - כל מה שמחוץ ללוח המשחק עצמו ---
MODERN_BG = (28, 30, 38)
MODERN_PANEL = (40, 43, 54)
MODERN_BORDER = (63, 67, 82)
MODERN_TEXT = (235, 236, 240)
MODERN_TEXT_DIM = (152, 157, 173)
MODERN_ACCENT = (255, 199, 79)
MODERN_SUCCESS = (110, 220, 140)
MODERN_DANGER = (255, 99, 99)

# --- לוח המשחק עצמו - בדיוק אותו גודל כמו קודם, שום דבר בהיגיון המשחק לא משתנה ---
BOARD_WIDTH, BOARD_HEIGHT = 600, 400
BLOCK_SIZE = 20

# --- ה"מסגרת" המודרנית מסביב: שורת סטטוס למעלה + שוליים מכל הצדדים ---
MARGIN = 24
TOP_BAR_HEIGHT = 60
WINDOW_WIDTH = BOARD_WIDTH + MARGIN * 2
WINDOW_HEIGHT = TOP_BAR_HEIGHT + BOARD_HEIGHT + MARGIN * 2
BOARD_X = MARGIN
BOARD_Y = TOP_BAR_HEIGHT + MARGIN

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Snake for Windows - נוקיה 225")

# "board" הוא subsurface - חלון פנימי בתוך screen, במיקום BOARD_X, BOARD_Y.
# ציור על board משתמש באותן קואורדינטות מקומיות (0,0) עד (600,400) בדיוק כמו
# קודם - קוד התנועה/ההתנגשות/הציור של הנחש לא צריך לדעת שהמסך הכולל גדול יותר.
board = screen.subsurface(pygame.Rect(BOARD_X, BOARD_Y, BOARD_WIDTH, BOARD_HEIGHT))

# נתיב בטוח גם כשהמשחק ארוז ל-exe (PyInstaller --onefile)
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SCORE_FILE = os.path.join(APP_DIR, "high_score.json")


def resource_path(relative_path):
    """
    נתיב לקבצי משאבים (תמונות/צלילים) שעובד גם כשמריצים python main.py
    וגם בתוך exe מקומפל של PyInstaller (--add-data).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = APP_DIR
    return os.path.join(base_path, relative_path)


try:
    icon_surface = pygame.image.load(resource_path(os.path.join("assets", "icon.png")))
    pygame.display.set_icon(icon_surface)
except Exception:
    pass

try:
    pygame.mixer.init()
    CRUNCH_SOUND = pygame.mixer.Sound(resource_path(os.path.join("assets", "crunch.wav")))
    GAMEOVER_SOUND = pygame.mixer.Sound(resource_path(os.path.join("assets", "gameover.wav")))
    LEVELUP_SOUND = pygame.mixer.Sound(resource_path(os.path.join("assets", "levelup.wav")))
    SPECIAL_SOUND = pygame.mixer.Sound(resource_path(os.path.join("assets", "special.wav")))
    SOUND_ENABLED = True
except Exception:
    CRUNCH_SOUND = GAMEOVER_SOUND = LEVELUP_SOUND = SPECIAL_SOUND = None
    SOUND_ENABLED = False


def play_sound(sound):
    if SOUND_ENABLED and sound is not None:
        try:
            sound.play()
        except Exception:
            pass


clock = pygame.time.Clock()


def _load_hebrew_font(size, bold=False):
    """
    טוען גופן שתומך בעברית בצורה אמינה - ישירות לפי נתיב קובץ, לא לפי שם
    (SysFont לפי שם לא אמין בתוך exe מקומפל ועלול להחזיר גופן בלי עברית).
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

    fallback_path = pygame.font.match_font("arial,tahoma,segoeui,davidlibre", bold=bold)
    if fallback_path:
        try:
            return pygame.font.Font(fallback_path, size)
        except Exception:
            pass

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
    """מוריד את ה-exe מה-Release האחרון ומחליף את קובץ ה-exe הרץ כרגע (רק בגרסת exe)."""
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


_BRACKET_MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{"}


def rtl(text):
    # אם אין בטקסט אף תו עברי (למשל כותרת אנגלית טהורה), אין סיבה להפוך סדר מילים.
    if not any(1424 < ord(c) < 1536 for c in text):
        return text

    def flip_word(w):
        if any(1424 < ord(c) < 1536 for c in w):
            return "".join(_BRACKET_MIRROR.get(c, c) for c in reversed(w))
        return w

    words = text.split(" ")
    return " ".join(flip_word(w) for w in reversed(words))


def draw_text(text, color, y_offset=0, font=font_style, surface=None, area_w=None, area_h=None):
    """
    מצייר טקסט ממורכז. כברירת מחדל מצייר על כל החלון (למסך התפריט המודרני);
    כדי למרכז טקסט בתוך לוח המשחק בלבד (השהייה / נפסלת), משתמשים ב-draw_board_text.
    """
    surface = screen if surface is None else surface
    area_w = WINDOW_WIDTH if area_w is None else area_w
    area_h = WINDOW_HEIGHT if area_h is None else area_h
    mesg = font.render(rtl(text), True, color)
    text_rect = mesg.get_rect(center=(area_w / 2, area_h / 2 + y_offset))
    surface.blit(mesg, text_rect)


def draw_board_text(text, color, y_offset=0, font=font_style):
    draw_text(text, color, y_offset, font, surface=board, area_w=BOARD_WIDTH, area_h=BOARD_HEIGHT)


def draw_grid():
    for gx in range(0, BOARD_WIDTH, BLOCK_SIZE):
        pygame.draw.line(board, GRID_LINE_COLOR, (gx, 0), (gx, BOARD_HEIGHT), 1)
    for gy in range(0, BOARD_HEIGHT, BLOCK_SIZE):
        pygame.draw.line(board, GRID_LINE_COLOR, (0, gy), (BOARD_WIDTH, gy), 1)


def draw_board_frame():
    """מסגרת דקה סביב לוח המשחק בלבד - לא סביב כל החלון."""
    pygame.draw.rect(
        screen, BEZEL_COLOR,
        (BOARD_X - 3, BOARD_Y - 3, BOARD_WIDTH + 6, BOARD_HEIGHT + 6),
        width=3, border_radius=4,
    )


def draw_top_bar(high_score, score):
    """שורת הסטטוס - עכשיו מחוץ ללוח המשחק לגמרי, לא מכסה יותר אריחים של המשחק."""
    pygame.draw.rect(screen, MODERN_PANEL, (0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT))
    pygame.draw.line(screen, MODERN_BORDER, (0, TOP_BAR_HEIGHT), (WINDOW_WIDTH, TOP_BAR_HEIGHT), 2)

    score_text = score_font.render(rtl(f"שיא: {high_score} | ניקוד: {score}"), True, MODERN_TEXT)
    screen.blit(score_text, [MARGIN, (TOP_BAR_HEIGHT - score_text.get_height()) // 2])

    pause_hint = small_font.render(rtl("P להשהיה"), True, MODERN_TEXT_DIM)
    screen.blit(pause_hint, [WINDOW_WIDTH - pause_hint.get_width() - MARGIN, (TOP_BAR_HEIGHT - pause_hint.get_height()) // 2])


def draw_chrome_margins():
    """
    ממלא רק את השוליים סביב הלוח (לא נוגע בלוח עצמו) - שימושי במסכי השהייה/סיום,
    שם רוצים לשמר את התוכן הקפוא של הלוח ולא לצייר אותו מחדש מאפס.
    """
    pygame.draw.rect(screen, MODERN_BG, (0, TOP_BAR_HEIGHT, MARGIN, WINDOW_HEIGHT - TOP_BAR_HEIGHT))
    right_x = BOARD_X + BOARD_WIDTH
    pygame.draw.rect(screen, MODERN_BG, (right_x, TOP_BAR_HEIGHT, WINDOW_WIDTH - right_x, WINDOW_HEIGHT - TOP_BAR_HEIGHT))
    bottom_y = BOARD_Y + BOARD_HEIGHT
    pygame.draw.rect(screen, MODERN_BG, (0, bottom_y, WINDOW_WIDTH, WINDOW_HEIGHT - bottom_y))


def draw_snake(block_size, snake_list, direction=(1, 0)):
    n = len(snake_list)
    for i, seg in enumerate(snake_list):
        rect = [seg[0], seg[1], block_size, block_size]
        is_head = i == n - 1
        if is_head:
            color = SNAKE_HEAD_COLOR
        else:
            t = i / max(n - 1, 1)
            color = tuple(
                int(SNAKE_TAIL_COLOR[c] + (SNAKE_BODY_COLOR[c] - SNAKE_TAIL_COLOR[c]) * t)
                for c in range(3)
            )
        pygame.draw.rect(board, color, rect, border_radius=6)
        pygame.draw.rect(board, SNAKE_OUTLINE_COLOR, rect, width=1, border_radius=6)

    if not snake_list:
        return

    hx, hy = snake_list[-1]
    dx, dy = direction
    if dx == 0 and dy == 0:
        dx = 1
    if dx == 1:
        eyes = [(hx + block_size - 6, hy + 5), (hx + block_size - 6, hy + block_size - 5)]
    elif dx == -1:
        eyes = [(hx + 6, hy + 5), (hx + 6, hy + block_size - 5)]
    elif dy == 1:
        eyes = [(hx + 5, hy + block_size - 6), (hx + block_size - 5, hy + block_size - 6)]
    else:
        eyes = [(hx + 5, hy + 6), (hx + block_size - 5, hy + 6)]
    for ex, ey in eyes:
        pygame.draw.circle(board, (235, 235, 225), (int(ex), int(ey)), 2)


def draw_food(foodx, foody):
    cx = foodx + BLOCK_SIZE / 2
    cy = foody + BLOCK_SIZE / 2
    radius = BLOCK_SIZE / 2 - 1

    pygame.draw.circle(board, APPLE_COLOR, (int(cx), int(cy) + 2), int(radius))
    pygame.draw.circle(board, APPLE_HIGHLIGHT, (int(cx - radius / 2.5), int(cy - radius / 2.5) + 2), 2)
    pygame.draw.line(board, STEM_COLOR, (cx, foody + 2), (cx + 3, foody - 3), 2)

    leaf_rect = pygame.Rect(0, 0, 8, 5)
    leaf_rect.center = (cx + 6, foody - 1)
    pygame.draw.ellipse(board, LEAF_COLOR, leaf_rect)


def draw_special_food(foodx, foody):
    """תפוח זהב מיוחד - נעלם אחרי 5 שניות, ככל שתופסים אותו מהר יותר מקבלים יותר נקודות."""
    cx = foodx + BLOCK_SIZE / 2
    cy = foody + BLOCK_SIZE / 2
    radius = BLOCK_SIZE / 2 - 1

    pygame.draw.circle(board, SPECIAL_APPLE_COLOR, (int(cx), int(cy) + 2), int(radius))
    pygame.draw.circle(board, (255, 255, 220), (int(cx - radius / 2.5), int(cy - radius / 2.5) + 2), 2)
    pygame.draw.line(board, STEM_COLOR, (cx, foody + 2), (cx + 3, foody - 3), 2)

    leaf_rect = pygame.Rect(0, 0, 8, 5)
    leaf_rect.center = (cx + 6, foody - 1)
    pygame.draw.ellipse(board, (50, 205, 50), leaf_rect)


def spawn_food(snake_list, extra_occupied=None):
    if extra_occupied is None:
        extra_occupied = []
    while True:
        fx = round(random.randrange(0, BOARD_WIDTH - BLOCK_SIZE) / 20.0) * 20.0
        fy = round(random.randrange(0, BOARD_HEIGHT - BLOCK_SIZE) / 20.0) * 20.0
        if [fx, fy] not in snake_list and [fx, fy] not in extra_occupied:
            return fx, fy


def _dim_board():
    overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
    overlay.set_alpha(150)
    overlay.fill((0, 0, 0))
    board.blit(overlay, (0, 0))


def pause_screen(high_score, score):
    """
    מסך השהייה: הכל *מחוץ* ללוח (שוליים, שורת הסטטוס) בסגנון מודרני כהה.
    לוח המשחק עצמו קופא במקום (תמונת "צילום" של הרגע שבו נלחץ P) ומעומעם -
    כדי שלא יכהה יותר ויותר בכל פריים, שומרים העתק אחד ומציירים אותו מחדש
    בכל לולאה, במקום להמשיך "לעמעם על עצמו".
    """
    paused = True
    pause_start = pygame.time.get_ticks()
    board_snapshot = board.copy()

    while paused:
        draw_chrome_margins()
        board.blit(board_snapshot, (0, 0))
        _dim_board()
        draw_top_bar(high_score, score)
        draw_board_frame()
        draw_board_text("השהייה", MODERN_TEXT, -20)
        draw_board_text("לחץ P כדי להמשיך", MODERN_TEXT_DIM, 20, score_font)
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                paused = False
        clock.tick(15)

    return pygame.time.get_ticks() - pause_start  # כמה זמן היינו בהשהייה, במילישניות


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
        close_snapshot = None

        x1 = BOARD_WIDTH / 2
        y1 = BOARD_HEIGHT / 2
        x1_change = 0
        y1_change = 0

        snake_list = []
        length_of_snake = 1
        score = 0
        high_score = get_high_score()
        speed = base_speed

        foodx, foody = spawn_food(snake_list)

        # משתני התפוח המוזהב המיוחד - נעלם אחרי 5 שניות
        special_food_active = False
        special_food_x = -1
        special_food_y = -1
        special_spawn_time = 0
        SPECIAL_DURATION = 5000
        SPECIAL_SPAWN_CHANCE = 15  # אחוזים

        while not game_over:
            current_time = pygame.time.get_ticks()

            if special_food_active and (current_time - special_spawn_time > SPECIAL_DURATION):
                special_food_active = False

            while game_close:
                if close_snapshot is None:
                    close_snapshot = board.copy()

                draw_chrome_margins()
                board.blit(close_snapshot, (0, 0))
                _dim_board()
                draw_top_bar(high_score, score)
                draw_board_frame()

                if score > high_score:
                    save_high_score(score)
                    high_score = score
                    draw_board_text("!שיא חדש!", MODERN_ACCENT, -60)

                draw_board_text("נפסלת!", MODERN_DANGER, -30)
                draw_board_text("לחץ C לשחק שוב, Q לתפריט", MODERN_TEXT, 10)
                draw_board_text(f"הניקוד שלך: {score}", MODERN_TEXT, 50, score_font)
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
                        paused_ms = pause_screen(high_score, score)
                        # שומר שהתפוח המוזהב לא "ימות" בשקט בזמן שהמשחק מושהה
                        if special_food_active:
                            special_spawn_time += paused_ms

            # תזוזה קודם, ואז בדיקת גלישת קיר - כך אין פריים
            # שבו הנחש מצויר רגע אחד מחוץ ללוח.
            x1 += x1_change
            y1 += y1_change

            if x1 >= BOARD_WIDTH:
                x1 = 0
            elif x1 < 0:
                x1 = BOARD_WIDTH - BLOCK_SIZE
            if y1 >= BOARD_HEIGHT:
                y1 = 0
            elif y1 < 0:
                y1 = BOARD_HEIGHT - BLOCK_SIZE

            screen.fill(MODERN_BG)
            board.fill(BG_COLOR)
            draw_grid()
            draw_food(foodx, foody)

            if special_food_active:
                draw_special_food(special_food_x, special_food_y)

            snake_head = [x1, y1]
            snake_list.append(snake_head)

            if len(snake_list) > length_of_snake:
                del snake_list[0]

            for segment in snake_list[:-1]:
                if segment == snake_head:
                    game_close = True
                    play_sound(GAMEOVER_SOUND)

            move_dir = (
                1 if x1_change > 0 else -1 if x1_change < 0 else 0,
                1 if y1_change > 0 else -1 if y1_change < 0 else 0,
            )
            draw_snake(BLOCK_SIZE, snake_list, direction=move_dir)

            draw_top_bar(high_score, score)
            draw_board_frame()
            pygame.display.update()

            # אכילת תפוח רגיל
            if x1 == foodx and y1 == foody:
                play_sound(CRUNCH_SOUND)
                occupied = [[special_food_x, special_food_y]] if special_food_active else []
                foodx, foody = spawn_food(snake_list, extra_occupied=occupied)
                length_of_snake += 1
                score += 10

                if not special_food_active and random.randint(1, 100) <= SPECIAL_SPAWN_CHANCE:
                    special_food_x, special_food_y = spawn_food(snake_list, extra_occupied=[[foodx, foody]])
                    special_food_active = True
                    special_spawn_time = current_time

                if length_of_snake % 5 == 0:
                    old_speed = speed
                    speed = min(speed + 1, base_speed + 8)
                    if speed != old_speed:
                        play_sound(LEVELUP_SOUND)

            # אכילת תפוח מוזהב מיוחד - ככל שתופסים מהר יותר, יותר נקודות
            if special_food_active and x1 == special_food_x and y1 == special_food_y:
                play_sound(SPECIAL_SOUND if SPECIAL_SOUND else LEVELUP_SOUND)
                special_food_active = False
                length_of_snake += 1
                time_alive = current_time - special_spawn_time
                bonus_points = max(10, 50 - int((time_alive / SPECIAL_DURATION) * 40))
                score += bonus_points

            clock.tick(speed)


def main_menu():
    speed = 10
    menu = True
    update_info = check_for_update()
    update_message = ""

    while menu:
        screen.fill(MODERN_BG)

        card = pygame.Rect(0, 0, WINDOW_WIDTH - MARGIN, WINDOW_HEIGHT - MARGIN)
        card.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        pygame.draw.rect(screen, MODERN_PANEL, card, border_radius=18)
        pygame.draw.rect(screen, MODERN_BORDER, card, width=2, border_radius=18)

        draw_text("Snake for Windows", MODERN_TEXT, -140, font_style)
        draw_text(f"נוקיה 225 - מהדורה רטרו (v{VERSION})", MODERN_TEXT_DIM, -108, score_font)
        draw_text("1. התחל משחק", MODERN_TEXT, -40)
        speed_label = "קל" if speed == 7 else "רגיל" if speed == 10 else "קשה"
        draw_text(f"2. מהירות (כרגע: {speed_label})", MODERN_TEXT, 0)
        draw_text("3. יציאה", MODERN_TEXT, 40)
        draw_text(f"שיא נוכחי: {get_high_score()}", MODERN_ACCENT, 84, score_font)
        if update_info:
            draw_text(f"4. לחצו לעדכון לגרסה {update_info.get('tag_name', '')}!", MODERN_SUCCESS, 128, small_font)
        if update_message:
            draw_text(update_message, MODERN_DANGER, 160, small_font)

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

import pygame
import pygame_gui
import random
import os
import sys
import json
import time
import webbrowser
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
MODERN_ACCENT_HOVER = (255, 214, 122)

# --- ערכות נושא (themes) עבור pygame_gui, למעטפת החדשה (בית/שיאים/פרטיות/עדכון/אודות) ---
# ה-theme נטען מקובץ JSON *אמיתי* (assets/theme_dark.json / theme_light.json),
# לא מ-dict של פייתון - כי יש חשד מבוסס ש-UIManager לא תומך באמינות בקבלת
# dict ישירות, ונופל בשקט ל-theme הפנימי שלו כשזה נכשל (זה בדיוק מה שקרה:
# גם הגופן וגם העיצוב לא השתנו בכלל - סימן ל-theme שלא נטען בפועל).
# הנתיבים המלאים (UI_THEME_DARK_PATH וכו') מוגדרים בהמשך הקובץ, אחרי
# resource_path(), כי הם תלויים בה.

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


UI_FONT_REGULAR_PATH = resource_path(os.path.join("assets", "fonts", "Rubik-Regular.ttf"))
UI_FONT_BOLD_PATH = resource_path(os.path.join("assets", "fonts", "Rubik-Bold.ttf"))
UI_THEME_DARK_PATH = resource_path(os.path.join("assets", "theme_dark.json"))
UI_THEME_LIGHT_PATH = resource_path(os.path.join("assets", "theme_light.json"))


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


def get_top_scores():
    """
    מחזיר את 5 השיאים הגבוהים ביותר, ממוינים מהגבוה לנמוך.
    תומך גם בקובץ ישן בפורמט הקודם ({"high_score": N}) וממיר אותו אוטומטית.
    """
    if not os.path.exists(SCORE_FILE):
        return []
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    if "top_scores" in data:
        scores = data.get("top_scores", [])
    elif "high_score" in data:
        # פורמט ישן - שיא בודד. ממירים לרשימה כדי שההיסטוריה לא תלך לאיבוד.
        old = data.get("high_score", 0)
        scores = [old] if old > 0 else []
    else:
        scores = []

    return sorted(scores, reverse=True)[:5]


def get_high_score():
    scores = get_top_scores()
    return scores[0] if scores else 0


def save_score(score):
    """מוסיף ניקוד לרשימת 5 השיאים המובילים (אם הוא אכן נכנס לחמישייה) ושומר לדיסק."""
    scores = get_top_scores()
    scores.append(score)
    scores = sorted(scores, reverse=True)[:5]
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as file:
            json.dump({"top_scores": scores}, file)
    except OSError:
        pass  # אין הרשאת כתיבה - לא קריטי, פשוט לא נשמור הפעם
    return scores


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


MAX_SPEED_LEVELS = 8  # תואם ל-"base_speed + 8" - תקרת המהירות המקסימלית במשחק


def draw_speed_meter(center_x, center_y, level, max_level=MAX_SPEED_LEVELS):
    """מד מהירות קטן בסגנון פסי אקולייזר - כל פס גבוה יותר מקודמו, מלא בהתאם לרמת המהירות הנוכחית."""
    bar_w, gap = 4, 3
    min_h, max_h = 6, 22
    total_w = max_level * bar_w + (max_level - 1) * gap
    start_x = center_x - total_w // 2

    for i in range(max_level):
        h = min_h + (max_h - min_h) * (i + 1) / max_level
        bx = start_x + i * (bar_w + gap)
        by = center_y - h / 2
        color = MODERN_ACCENT if i < level else MODERN_BORDER
        pygame.draw.rect(screen, color, (bx, by, bar_w, h), border_radius=2)


def draw_top_bar(high_score, score, speed=None, base_speed=None):
    """שורת הסטטוס - עכשיו מחוץ ללוח המשחק לגמרי, לא מכסה יותר אריחים של המשחק."""
    pygame.draw.rect(screen, MODERN_PANEL, (0, 0, WINDOW_WIDTH, TOP_BAR_HEIGHT))
    pygame.draw.line(screen, MODERN_BORDER, (0, TOP_BAR_HEIGHT), (WINDOW_WIDTH, TOP_BAR_HEIGHT), 2)

    score_text = score_font.render(rtl(f"שיא: {high_score} | ניקוד: {score}"), True, MODERN_TEXT)
    screen.blit(score_text, [MARGIN, (TOP_BAR_HEIGHT - score_text.get_height()) // 2])

    pause_hint = small_font.render(rtl("P להשהיה"), True, MODERN_TEXT_DIM)
    screen.blit(pause_hint, [WINDOW_WIDTH - pause_hint.get_width() - MARGIN, (TOP_BAR_HEIGHT - pause_hint.get_height()) // 2])

    if speed is not None and base_speed is not None:
        level = max(0, min(MAX_SPEED_LEVELS, speed - base_speed))
        draw_speed_meter(WINDOW_WIDTH // 2, TOP_BAR_HEIGHT // 2, level)


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


def draw_icon_button(rect, icon):
    """
    כפתור עגלגל עם אייקון וקטורי בלבד - בלי טקסט בכלל (ולכן בלי שום תלות
    בגופן/RTL). מצייר על screen (לא board), כי הכפתורים האלה שייכים
    למסכי ה"מעטפת" (השהייה/נפסלת), לא ללוח המשחק עצמו.
    """
    pygame.draw.rect(screen, MODERN_PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, MODERN_BORDER, rect, width=2, border_radius=12)
    cx, cy = rect.center
    color = MODERN_TEXT

    if icon == "play":
        s = 9
        pygame.draw.polygon(screen, color, [(cx - s // 2, cy - s), (cx - s // 2, cy + s), (cx + s, cy)])
    elif icon == "restart":
        pygame.draw.arc(screen, color, (cx - 12, cy - 12, 24, 24), 0.6, 5.4, 3)
        pygame.draw.polygon(screen, color, [(cx + 11, cy - 7), (cx + 17, cy - 3), (cx + 9, cy + 2)])
    elif icon == "home":
        pygame.draw.polygon(screen, color, [(cx - 13, cy + 2), (cx, cy - 12), (cx + 13, cy + 2)])
        pygame.draw.rect(screen, color, (cx - 8, cy + 2, 16, 12))


def _clicked(rect, events):
    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and rect.collidepoint(event.pos):
            return True
    return False


def pause_screen(high_score, score, speed, base_speed):
    """
    מסך השהייה: הכל *מחוץ* ללוח (שוליים, שורת הסטטוס) בסגנון מודרני כהה.
    לוח המשחק עצמו קופא במקום (תמונת "צילום" של הרגע שבו נלחץ P) ומעומעם -
    כדי שלא יכהה יותר ויותר בכל פריים, שומרים העתק אחד ומציירים אותו מחדש
    בכל לולאה, במקום להמשיך "לעמעם על עצמו".
    """
    paused = True
    pause_start = pygame.time.get_ticks()
    board_snapshot = board.copy()
    resume_btn = pygame.Rect(0, 0, 56, 56)
    resume_btn.center = (WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2 + 60)

    while paused:
        draw_chrome_margins()
        board.blit(board_snapshot, (0, 0))
        _dim_board()
        draw_top_bar(high_score, score, speed, base_speed)
        draw_board_frame()
        draw_board_text("השהייה", MODERN_TEXT, -20)
        draw_board_text("לחץ P כדי להמשיך", MODERN_TEXT_DIM, 20, score_font)
        draw_icon_button(resume_btn, "play")
        pygame.display.update()

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                paused = False
        if _clicked(resume_btn, events):
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
        score_recorded = False

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

        # מהירות עולה בפועל רק שנייה אחרי האכילה שגרמה לה - כדי שצליל
        # ה"עלייה" לא יתנגש עם צליל הנגיסה שכבר מתנגן באותו רגע.
        pending_speed_time = None
        pending_new_speed = None
        LEVELUP_DELAY = 1000

        while not game_over:
            current_time = pygame.time.get_ticks()

            if special_food_active and (current_time - special_spawn_time > SPECIAL_DURATION):
                special_food_active = False

            if pending_speed_time is not None and current_time >= pending_speed_time:
                speed = pending_new_speed
                play_sound(LEVELUP_SOUND)
                pending_speed_time = None
                pending_new_speed = None

            while game_close:
                if close_snapshot is None:
                    close_snapshot = board.copy()
                    restart_btn = pygame.Rect(0, 0, 56, 56)
                    home_btn = pygame.Rect(0, 0, 56, 56)
                    btn_y = BOARD_Y + BOARD_HEIGHT // 2 + 90
                    restart_btn.center = (WINDOW_WIDTH // 2 - 40, btn_y)
                    home_btn.center = (WINDOW_WIDTH // 2 + 40, btn_y)

                draw_chrome_margins()
                board.blit(close_snapshot, (0, 0))
                _dim_board()
                draw_top_bar(high_score, score, speed, base_speed)
                draw_board_frame()

                if not score_recorded:
                    score_recorded = True
                    save_score(score)

                if score > high_score:
                    high_score = score
                    draw_board_text("!שיא חדש!", MODERN_ACCENT, -60)

                draw_board_text("נפסלת!", MODERN_DANGER, -30)
                draw_board_text("לחץ C לשחק שוב, Q לתפריט", MODERN_TEXT, 10)
                draw_board_text(f"הניקוד שלך: {score}", MODERN_TEXT, 50, score_font)
                draw_icon_button(restart_btn, "restart")
                draw_icon_button(home_btn, "home")
                pygame.display.update()

                events = pygame.event.get()
                for event in events:
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
                if _clicked(restart_btn, events):
                    game_over = True
                    game_close = False
                    restart = True
                elif _clicked(home_btn, events):
                    game_over = True
                    game_close = False

            if game_over:
                # יוצאים מיד - בלי זה, פריים "רפאים" אחד עדיין מריץ את קוד
                # התנועה/ההתנגשות על snake_list הישן (מלפני האיפוס), ומזהה
                # שוב "התנגשות" עם הגוף הישן -> משמיע את צליל ה-gameover פעם נוספת.
                continue

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
                        paused_ms = pause_screen(high_score, score, speed, base_speed)
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

            draw_top_bar(high_score, score, speed, base_speed)
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
                    candidate_speed = min(speed + 1, base_speed + 8)
                    if candidate_speed != speed:
                        pending_new_speed = candidate_speed
                        pending_speed_time = current_time + LEVELUP_DELAY

            # אכילת תפוח מוזהב מיוחד - ככל שתופסים מהר יותר, יותר נקודות
            if special_food_active and x1 == special_food_x and y1 == special_food_y:
                play_sound(SPECIAL_SOUND if SPECIAL_SOUND else LEVELUP_SOUND)
                special_food_active = False
                length_of_snake += 1
                time_alive = current_time - special_spawn_time
                bonus_points = max(10, 50 - int((time_alive / SPECIAL_DURATION) * 40))
                score += bonus_points

            clock.tick(speed)


def _speed_name(speed):
    return "קל" if speed == 7 else "רגיל" if speed == 10 else "קשה"


def _log_debug(message):
    """כותב שורת דיבוג לקובץ ליד ה-exe - כי זה --windowed, אין קונסולה לראות בה שגיאות."""
    try:
        with open(os.path.join(APP_DIR, "debug_log.txt"), "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


def _make_ui_manager(dark_mode):
    theme_path = UI_THEME_DARK_PATH if dark_mode else UI_THEME_LIGHT_PATH
    _log_debug(f"[ui] theme_path={theme_path} exists={os.path.exists(theme_path)}")
    _log_debug(f"[ui] font_regular={UI_FONT_REGULAR_PATH} exists={os.path.exists(UI_FONT_REGULAR_PATH)}")
    _log_debug(f"[ui] font_bold={UI_FONT_BOLD_PATH} exists={os.path.exists(UI_FONT_BOLD_PATH)}")

    # חשוב: יוצרים את ה-manager *בלי* theme קודם, ורק אחרי שרושמים את הגופן
    # טוענים את ה-theme בפועל. אם ה-theme נטען כבר בבנייה (לפני שהגופן רשום),
    # החיפוש של "hebrew_ui_font" נכשל בשקט באותו רגע ונשאר "תקוע" על ברירת
    # המחדל - גם אם רושמים את הגופן מיד אחר כך. זה בדיוק מה שקרה קודם.
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))

    try:
        manager.add_font_paths("hebrew_ui_font", UI_FONT_REGULAR_PATH, bold_path=UI_FONT_BOLD_PATH)
        manager.preload_fonts([
            {"name": "hebrew_ui_font", "point_size": 16, "style": "regular"},
            {"name": "hebrew_ui_font", "point_size": 18, "style": "bold"},
        ])
        _log_debug("[ui] font registration + preload: OK")
    except Exception as e:
        _log_debug(f"[ui] font registration FAILED: {type(e).__name__}: {e}")

    try:
        manager.get_theme().load_theme(theme_path)
        _log_debug("[ui] theme load (after font registration): OK")
    except Exception as e:
        _log_debug(f"[ui] theme load FAILED: {type(e).__name__}: {e}")
    return manager


def main_menu():
    """
    המעטפת החדשה: שורה עליונה עם 3 אייקונים (מידע / תצוגה / תפריט צד),
    מגירת צד עם 4 מסכים (בית, שיאים, פרטיות, עדכון אוטומטי), ומסך אודות
    נפרד מהאייקון ℹ. בנוי עם pygame_gui - לא נבדק בפועל (אין רשת בסביבת
    הפיתוח שיצרה את הקוד הזה), אז בדקו בזהירות לפני מיזוג ה-branch.

    gameLoop() עצמו (המשחק בפועל) לא השתנה בכלל.
    """
    state = {
        "dark_mode": True,
        "screen": "home",
        "drawer_open": False,
        "speed": 10,
        "last_check_time": None,
        "update_info": None,
        "update_message": "",
    }

    manager = _make_ui_manager(state["dark_mode"])
    elements = {}

    def clear(group):
        for el in elements.pop(group, []):
            el.kill()

    def build_topbar():
        clear("topbar")
        info_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(MARGIN, 10, 40, 36), text="i", manager=manager)
        theme_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH // 2 - 20, 10, 40, 36),
            text=("Dark" if state["dark_mode"] else "Light"), manager=manager)
        menu_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - MARGIN - 40, 10, 40, 36), text="=", manager=manager)
        elements["topbar"] = [info_btn, theme_btn, menu_btn]
        elements["info_btn"] = info_btn
        elements["theme_btn"] = theme_btn
        elements["menu_btn"] = menu_btn

    def build_drawer():
        clear("drawer")
        panel_rect = pygame.Rect(WINDOW_WIDTH - 210, TOP_BAR_HEIGHT, 210, WINDOW_HEIGHT - TOP_BAR_HEIGHT)
        panel = pygame_gui.elements.UIPanel(relative_rect=panel_rect, starting_height=2, manager=manager)
        items = [("home", "בית"), ("scores", "שיאים"), ("privacy", "פרטיות"), ("update", "עדכון אוטומטי")]
        buttons = {}
        for i, (key, label) in enumerate(items):
            buttons[key] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(10, 10 + i * 52, 190, 42),
                text=rtl(label), manager=manager, container=panel)
        panel.hide()
        elements["drawer_panel"] = panel
        elements["drawer_buttons"] = buttons
        elements["drawer"] = [panel]

    def build_content():
        clear("content")
        content_rect = pygame.Rect(
            MARGIN, TOP_BAR_HEIGHT + MARGIN,
            WINDOW_WIDTH - 2 * MARGIN, WINDOW_HEIGHT - TOP_BAR_HEIGHT - 2 * MARGIN,
        )
        panel = pygame_gui.elements.UIPanel(relative_rect=content_rect, starting_height=1, manager=manager)
        widgets = [panel]
        screen_name = state["screen"]
        w = content_rect.width

        if screen_name == "home":
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, 10, w, 30), text="Snake for Windows",
                manager=manager, container=panel)
            elements["start_btn"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(20, 64, w - 40, 52),
                text=rtl("התחל משחק"), manager=manager, container=panel,
                object_id=pygame_gui.core.ObjectID(object_id="#start_button"))
            elements["left_arrow"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(20, 122, 44, 44), text="<", manager=manager, container=panel)
            elements["speed_label"] = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(74, 122, w - 44 * 2 - 40, 44),
                text=rtl(_speed_name(state["speed"])), manager=manager, container=panel)
            elements["right_arrow"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(w - 20 - 44, 122, 44, 44), text=">", manager=manager, container=panel)
            elements["exit_btn"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(20, 184, w - 40, 46),
                text=rtl("יציאה"), manager=manager, container=panel)
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, 246, w, 30),
                text=rtl(f"שיא גבוה ביותר: {get_high_score()}"), manager=manager, container=panel)

        elif screen_name == "scores":
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, 10, w, 30), text=rtl("5 השיאים המובילים"),
                manager=manager, container=panel)
            scores = get_top_scores()
            if not scores:
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(0, 56, w, 30), text=rtl("אין עדיין שיאים"),
                    manager=manager, container=panel)
            for i, s in enumerate(scores):
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(20, 56 + i * 38, w - 40, 32),
                    text=rtl(f"{i + 1}.  {s}"), manager=manager, container=panel)

        elif screen_name == "privacy":
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, 10, w, 30), text=rtl("פרטיות"), manager=manager, container=panel)
            privacy_text = (
                "המשחק פועל לחלוטין אופליין. אף מידע על המשחק שלך, "
                "השיאים שלך, או כל תוכן אחר, אינו נשלח לאינטרנט. "
                "התקשורת היחידה עם הרשת היא בדיקת קיום גרסה חדשה מול "
                "עמוד ה-Releases של הפרויקט בגיטהאב - בדיקה זו רק קוראת "
                "מידע ציבורי, ואינה שולחת שום פרט אישי."
            )
            pygame_gui.elements.UITextBox(
                html_text=rtl(privacy_text), relative_rect=pygame.Rect(0, 50, w, content_rect.height - 60),
                manager=manager, container=panel)

        elif screen_name == "update":
            last_check = state["last_check_time"] or "טרם נבדק"
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, 10, w, 30), text=rtl(f"נבדק לאחרונה: {last_check}"),
                manager=manager, container=panel)
            status = f"עדכון זמין: {state['update_info'].get('tag_name', '')}" if state["update_info"] else "אין עדכון חדש"
            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(0, 50, w, 30), text=rtl(status), manager=manager, container=panel)
            elements["check_btn"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(20, 100, w - 40, 46), text=rtl("בדוק עכשיו"),
                manager=manager, container=panel)
            if state["update_info"]:
                elements["apply_update_btn"] = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(20, 160, w - 40, 46), text=rtl("התקן עדכון"),
                    manager=manager, container=panel)
            if state["update_message"]:
                pygame_gui.elements.UILabel(
                    relative_rect=pygame.Rect(0, 220, w, 30), text=rtl(state["update_message"]),
                    manager=manager, container=panel)

        elif screen_name == "about":
            about_html = (
                f"Snake for Windows v{VERSION}<br>"
                "מאת: YSmauas<br><br>"
                "פרויקט קוד פתוח - שחזור נוסטלגי למשחק הסנייק מהנוקיה 225."
            )
            pygame_gui.elements.UITextBox(
                html_text=rtl(about_html), relative_rect=pygame.Rect(0, 10, w, 140),
                manager=manager, container=panel)
            elements["github_link_btn"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect(20, 160, w - 40, 46),
                text=rtl("פתח את הפרויקט בגיטהאב"), manager=manager, container=panel)

        elements["content"] = widgets

    def switch_screen(name):
        state["screen"] = name
        state["drawer_open"] = False
        elements["drawer_panel"].hide()
        build_content()

    def toggle_theme():
        nonlocal manager
        state["dark_mode"] = not state["dark_mode"]
        manager = _make_ui_manager(state["dark_mode"])
        build_topbar()
        build_drawer()
        build_content()

    def do_update_check():
        state["update_info"] = check_for_update()
        state["last_check_time"] = time.strftime("%H:%M:%S")
        state["update_message"] = ""
        if state["screen"] == "update":
            build_content()

    build_topbar()
    build_drawer()
    do_update_check()  # בדיקת עדכונים אוטומטית, פעם אחת בכניסה לתפריט
    build_content()

    ui_clock = pygame.time.Clock()
    while True:
        time_delta = ui_clock.tick(30) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            manager.process_events(event)

            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                el = event.ui_element
                drawer_buttons = elements.get("drawer_buttons", {})

                if el == elements.get("menu_btn"):
                    state["drawer_open"] = not state["drawer_open"]
                    if state["drawer_open"]:
                        elements["drawer_panel"].show()
                    else:
                        elements["drawer_panel"].hide()
                elif el == elements.get("theme_btn"):
                    toggle_theme()
                elif el == elements.get("info_btn"):
                    switch_screen("about")
                elif el == drawer_buttons.get("home"):
                    switch_screen("home")
                elif el == drawer_buttons.get("scores"):
                    switch_screen("scores")
                elif el == drawer_buttons.get("privacy"):
                    switch_screen("privacy")
                elif el == drawer_buttons.get("update"):
                    switch_screen("update")
                elif el == elements.get("start_btn"):
                    gameLoop(state["speed"])
                    build_content()  # לרענן את "שיא גבוה ביותר" אחרי המשחק
                elif el == elements.get("exit_btn"):
                    pygame.quit()
                    sys.exit()
                elif el == elements.get("left_arrow") or el == elements.get("right_arrow"):
                    speeds = [7, 10, 15]
                    idx = speeds.index(state["speed"])
                    idx = (idx - 1) % len(speeds) if el == elements.get("left_arrow") else (idx + 1) % len(speeds)
                    state["speed"] = speeds[idx]
                    elements["speed_label"].set_text(rtl(_speed_name(state["speed"])))
                elif el == elements.get("check_btn"):
                    do_update_check()
                elif el == elements.get("apply_update_btn") and state["update_info"]:
                    ok, msg = apply_update(state["update_info"])
                    if not ok:
                        state["update_message"] = msg
                        build_content()
                elif el == elements.get("github_link_btn"):
                    webbrowser.open("https://github.com/YSmauas/Snake-for-Windows")

        manager.update(time_delta)
        screen.fill(MODERN_BG if state["dark_mode"] else (240, 240, 245))
        manager.draw_ui(screen)
        pygame.display.update()


if __name__ == "__main__":
    main_menu()

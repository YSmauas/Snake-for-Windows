import urllib.request
import json
import os

GITHUB_REPO = "YSmauas/Snake-for-Windows"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LOCAL_FILE = "main.py"
TEMP_FILE = "main_new.py.tmp"


def update_game():
    print("מחפש עדכונים מגיטהאב...")
    try:
        req = urllib.request.Request(
            LATEST_RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "Snake-for-Windows-updater"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)

        tag_name = data.get("tag_name")
        if not tag_name:
            print("לא נמצאה גרסה עדכנית בגיטהאב.")
            return

        # מורידים את main.py בדיוק כפי שהיה בגרסה המתויגת (tag), לא מה-HEAD המשתנה של main
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{tag_name}/main.py"
        urllib.request.urlretrieve(raw_url, TEMP_FILE)

        if os.path.exists(LOCAL_FILE):
            os.remove(LOCAL_FILE)
        os.rename(TEMP_FILE, LOCAL_FILE)

        print(f"המשחק עודכן בהצלחה לגרסה {tag_name}!")

    except Exception:
        print("שגיאה בעדכון. ודא שיש חיבור לאינטרנט ושהמאגר זמין.")
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)


if __name__ == "__main__":
    update_game()
    input("\nלחץ אנטר כדי לצאת...")

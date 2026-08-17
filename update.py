import urllib.request
import os

GITHUB_RAW_URL = "https://raw.githubusercontent.com/YSmauas/RetroSnake/main/main.py"
LOCAL_FILE = "main.py"
TEMP_FILE = "main_new.py.tmp"

def update_game():
    print("מחפש עדכונים מגיטהאב...")
    try:
        urllib.request.urlretrieve(GITHUB_RAW_URL, TEMP_FILE)
        
        if os.path.exists(LOCAL_FILE):
            os.remove(LOCAL_FILE)
        os.rename(TEMP_FILE, LOCAL_FILE)
        
        print("המשחק עודכן בהצלחה לגרסה העדכנית ביותר!")
        
    except Exception as e:
        print("שגיאה בעדכון. ודא שיש חיבור לאינטרנט ושהקישור לגיטהאב נכון.")
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)

if __name__ == "__main__":
    update_game()
    input("\nלחץ אנטר כדי לצאת...")

import requests
import json
import time

TOKEN = "8206500144:AAE0d33TCI3hXtDqfIU-Msi17n5Kr760vfs"
GROUP_ID = -1002720457461
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
DATA_FILE = "data.json"

# Загрузка данных
try:
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
except:
    data = {"users": {}}

OFFSET = None

# Стройки
CONSTRUCTIONS = {"Высокая": 400_000, "Средняя": 250_000}
HIGH_CITIES = {"Арзамас": "/gps 7>3>1","Лыткарино": "/gps 7>3>2","Южный": "/gps 7>3>3","Нижегородск": "/gps 7>3>4"}
MEDIUM_CITIES = {"Гарель 1": "/gps 7>2>3","Гарель 2": "/gps 7>2>4","Батырево 1": "/gps 7>2>1","Батырево 2": "/gps 7>2>2"}

def send_message(chat_id, text, reply_markup=None):
    data_send = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data_send["reply_markup"] = json.dumps(reply_markup)
    requests.post(BASE_URL + "/sendMessage", data=data_send)

def send_photo(chat_id, photo_file, caption=None):
    files = {"photo": photo_file}
    data_send = {"chat_id": chat_id}
    if caption:
        data_send["caption"] = caption
        data_send["parse_mode"] = "HTML"
    requests.post(BASE_URL + "/sendPhoto", data=data_send, files=files)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def create_report(uid):
    u = data["users"][uid]
    total_bank = u.get("total_bank",0)
    salary = CONSTRUCTIONS.get(u.get("construction_type","-"),0)
    report = f"""📋 <b>Отчёт СК SAMOGON</b>

👤 Nick_Name: {u.get("nick_name","-")}
🏗 Вид стройки: {u.get("construction_type","-")}
💰 Банк: {u.get("bank","-")}
⏱ Время КД: {u.get("cd_time","-")}
💵 Заработок: {salary:,} вирт
🏦 Общий банк: {total_bank:,} вирт
"""
    return report

def rating_text():
    users = data["users"]
    top3 = sorted(users.items(), key=lambda x: x[1].get("total_bank",0), reverse=True)[:3]
    text = "🏆 <b>Рейтинг СК SAMOGON</b>\n\n"
    emojis = ["🥇","🥈","🥉"]
    for i, (uid, u) in enumerate(top3):
        high = u.get("high_count",0)
        medium = u.get("medium_count",0)
        total = u.get("total_bank",0)
        text += f"{emojis[i]} {u.get('nick_name','-')} | 🟩{high} 🟨{medium} | 💰 {total:,} вирт\n"
    if not top3:
        text += "Пока нет данных"
    return text

def main_menu():
    return {"inline_keyboard":[
        [{"text":"🟩 Сдать отчёт","callback_data":"report"}],
        [{"text":"🟪 Взять стройку","callback_data":"take"}],
        [{"text":"🟨 Рейтинг","callback_data":"rating"}]
    ]}

def back_button():
    return {"inline_keyboard":[
        [{"text":"🔙 Назад","callback_data":"back"}]
    ]}

# Главный цикл
while True:
    try:
        updates = requests.get(BASE_URL + "/getUpdates", params={"offset": OFFSET, "timeout":10}).json()
        for u in updates["result"]:
            OFFSET = u["update_id"] + 1
            if "message" in u:
                uid = u["message"]["from"]["id"]
                text = u["message"].get("text")
                photo = u["message"].get("photo")
            elif "callback_query" in u:
                uid = u["callback_query"]["from"]["id"]
                text = u["callback_query"]["data"]
            else:
                continue

            # Инициализация пользователя
            if uid not in data["users"]:
                data["users"][uid] = {"step":"start","total_bank":0,"high_count":0,"medium_count":0}

            user = data["users"][uid]

            # Старт
            if text == "/start":
                user["step"] = "start"
                send_message(uid,"🏗 Добро пожаловать в СК SAMOGON", main_menu())
                save_data()

            # Кнопка "Сдать отчёт"
            elif text == "report":
                user["step"]="waiting_nick"
                send_message(uid,"Введите ваш Nick_Name:", back_button())
                save_data()

            # Кнопка "Взять стройку"
            elif text == "take":
                kb = [[{"text":"Высокая","callback_data":"high"}],[{"text":"Средняя","callback_data":"medium"}],[{"text":"🔙 Назад","callback_data":"back"}]]
                send_message(uid,"Выберите тип стройки:", {"inline_keyboard": kb})

            elif text == "rating":
                send_message(uid, rating_text(), back_button())

            elif text == "back":
                user["step"]="start"
                send_message(uid,"Главное меню:", main_menu())

            # Шаги отчёта
            elif user.get("step")=="waiting_nick" and text:
                user["nick_name"]=text
                user["step"]="waiting_construction"
                kb=[[{"text":"Высокая","callback_data":"high_report"}],[{"text":"Средняя","callback_data":"medium_report"}],[{"text":"🔙 Назад","callback_data":"back"}]]
                send_message(uid,"Выберите вид стройки:", {"inline_keyboard":kb})
                save_data()

            elif user.get("step")=="waiting_construction" and text in ["Высокая","Средняя"]:
                user["construction_type"]=text
                user["step"]="waiting_bank"
                send_message(uid,"Введите ваш банковский счёт:", back_button())
                save_data()

            elif user.get("step")=="waiting_bank" and text:
                user["bank"]=text
                user["step"]="waiting_cd"
                send_message(uid,"Введите время КД:", back_button())
                save_data()

            elif user.get("step")=="waiting_cd" and text:
                user["cd_time"]=text
                user["step"]="waiting_photo"
                send_message(uid,"Отправьте скриншот доказательства:", back_button())
                save_data()

            elif user.get("step")=="waiting_photo" and photo:
                # Берём последнее фото
                file_id = photo[-1]["file_id"]
                user["step"]="start"
                # Начисляем зарплату
                salary = CONSTRUCTIONS.get(user.get("construction_type"),0)
                user["total_bank"] += salary
                if user["construction_type"]=="Высокая":
                    user["high_count"]=user.get("high_count",0)+1
                else:
                    user["medium_count"]=user.get("medium_count",0)+1
                save_data()
                # Отправляем отчёт пользователю и в группу
                report = create_report(uid)
                send_message(uid,report)
                send_message(GROUP_ID,report)
                # Сохраняем фото
                send_photo(uid, requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").content, caption="📸 Скриншот")
                save_data()

    except Exception as e:
        print("Ошибка:", e)
        time.sleep(2)
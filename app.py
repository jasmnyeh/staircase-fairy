from flask import Flask, request, jsonify, redirect
import os
import sqlite3
import datetime
import requests
from math import radians, cos, sin, sqrt, atan2
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, PostbackEvent, PostbackAction, TemplateSendMessage, ButtonsTemplate, LocationMessage

app = Flask(__name__)

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET_HERE")
# BOT_FRIEND_INVITE_URL = "https://line.me/R/ti/p/%40925keedn"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Database setup
conn = sqlite3.connect("scans.db", check_same_thread=False)
cursor = conn.cursor()

# Create scan_logs table to store QR scan records
cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        floor TEXT,
        location TEXT,
        timestamp TEXT
    )
""")
conn.commit() # Saves changes to the database

# Create all_user_points table to store points information
cursor.execute("""
    CREATE TABLE IF NOT EXISTS all_user_points (
        user_id TEXT PRIMARY KEY,
        points INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        points_to_next_level INTEGER DEFAULT 0,
        ranking INTEGER DEFAULT NULL
    )
""")
conn.commit()

# Create user_settings table to store user related info (gps location permission)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        location_consent INTEGER DEFAULT 0,
        language TEXT DEFAULT 'English'
    )
""")
conn.commit()

def bold_text(text):
    """ Converts text to fullwidth bold Unicode characters. """
    bold_map = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    )
    return text.translate(bold_map)

def send_line_message(user_id, text_key):
    """ Sends a text message in the user's preferred language. """

    # Fetch user's language preference
    user_language = get_user_language(user_id)

    # Get translated message
    translated_message = get_translated_text(user_id, text_key)

    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=translated_message))
    except Exception as e:
        print(f"🚨 Failed to send LINE message: {e}")

def get_user_language(user_id):
    """ Retrieves the user's preferred language from the database. Defaults to English. """
    cursor.execute("SELECT language FROM user_settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else "English"  # Default to English

def get_translated_text(user_id, text_key):
    """ Returns translated text based on user’s preferred language. """
    language = get_user_language(user_id)

    translations = {
        "welcome": {
            "English": "🎉 Welcome to Staircase Fairy!",
            "Chinese": "🎉 歡迎來到樓梯精靈！"
        },
        "choose_language": {
            "English": "🌍 Choose a language:",
            "Chinese": "🌍 請選擇語言："
        },
        "set_language": {
            "English": "✅ Language set to {selected_language}!",
            "Chinese": "✅ 語言已設定成{selected_language}！"
        },
        "allow_location": {
            "English": "📍 Allow location tracking?",
            "Chinese": "📍 是否允許取用您所在的位置？"
        },
        "need_to_allow_location": {
            "English": "🚨 You need to allow location tracking first.",
            "Chinese": "🚨 您需要先允許取用位置。"
        },
        "cant_fetch_location": {
            "English": "🚨 Unable to fetch location. Try again later.",
            "Chinese": "🚨 無法取用位置，稍後再試一次。"
        },
        "yes": {
            "English": "✅ Yes",
            "Chinese": "✅ 是"
        },
        "no": {
            "English": "❌ No",
            "Chinese": "❌ 否"
        },
        "points_menu": {
            "English": "🎯 Points & Ranking System\nChoose an option below:",
            "Chinese": "🎯 積分與排行榜\n請選擇下列選項："
        },
        "progress": {
            "English": "📊 My Progress",
            "Chinese": "📊 我的進度"
        },
        "leaderboard": {
            "English": "🏆 Leaderboard",
            "Chinese": "🏆 排行榜"
        },
        "no_points_yet": {
            "English": "You haven't earned any points yet. Start climbing to earn rewards! 🏆",
            "Chinese": "您目前還沒有點數，速速開始集點吧！🏆"
        },
        "location_enabled": {
            "English": "✅ Location tracking enabled! Start scanning QR codes!",
            "Chinese": "✅ 允許取用位置，您可以開始掃描QR碼！"
        },
        "location_denied": {
            "English": "❌ You denied location tracking. QR scan verification will not work.",
            "Chinese": "❌ 不允許取用位置，QR碼將無法運作 :("
        },
        "your_ranking": {
            "English": "🏆 𝗬𝗼𝘂𝗿 𝗥𝗮𝗻𝗸𝗶𝗻𝗴: #{rank}.",
            "Chinese": "🏆〖您的排名〗：#{rank}。"
        },
        "points_needed_to_rank_up": {
            "English": "⬆️ You need {points_needed} more points to move up to rank #{higher_rank}.",
            "Chinese": "⬆️ 您還需要 {points_needed} 分，才能升至 #{higher_rank}。"
        },
        "points_ahead": {
            "English": "⬇️ You are {points_ahead} points ahead of rank #{lower_rank}.",
            "Chinese": "⬇️ 您比 #{lower_rank} 領先 {points_ahead} 分。",
        },
        "top_climbers": {
            "English": "𝗧𝗼𝗽 𝗖𝗹𝗶𝗺𝗯𝗲𝗿𝘀:\n",
            "Chinese": "〖高手們〗：\n"
        },
        "rank_info": {
            "English": "{medal} Rank {rank} - Level {level} ({points} points)\n",
            "Chinese": "{medal} 排名 {rank} - 等級 {level}（{points} 分）\n"
        },
        "your_progress": {
            "English": "📊 𝗬𝗼𝘂𝗿 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:",
            "Chinese": "📊〖您的進度〗："
        },
        "current_level": {
            "English": "You're at {bold_level} with {bold_points}.",
            "Chinese": "您目前處於 {bold_level}，擁有 {bold_points}。"
        },
        "points_needed": {
            "English": "You need {bold_needed_points} to reach {bold_next_level}.",
            "Chinese": "您還需要 {bold_needed_points}，才能達到 {bold_next_level}。"
        },
        "keep_climbing": {
            "English": "Keep climbing! 🚀",
            "Chinese": "繼續努力爬樓梯吧！🚀"
        },
        "invalid_qrcode": {
            "English": "🚫 Invalid QR Code.",
            "Chinese": "🚫 無效的QR碼。"
        },
        "floor_unavailable": {
            "English": "🚫 {floor} is not available for {location_name}.",
            "Chinese": "🚫 {location_name}沒有{floor}。"
        },
        "too_far_away": {
            "English": "🚫 Scan failed! You are too far from the QR code location.",
            "Chinese": "🚫 掃描無效，您距離QR碼太遠了。"
        },
        "wait_longer": {
            "English": "🚫 You must wait at least 15 seconds before scanning again.",
            "Chinese": "🚫 您需要等待至少15秒才能掃描下一個QR碼。"
        },
        "scan_success": {
            "English": "🎉 Great job! You've earned +{point} point!\n"
                        "📍 𝗟𝗼𝗰𝗮𝘁𝗶𝗼𝗻: {location}\n"
                        "🏢 𝗙𝗹𝗼𝗼𝗿: {floor}\n"
                        "🕒 𝗧𝗶𝗺𝗲: {timestamp}",
            "Chinese": "🎉 太棒哩！恭喜你成功獲得 {point} 點！\n"
                        "📍〖位置〗：{location}\n"
                        "🏢〖樓層〗：{floor}\n"
                        "🕒〖時間〗：{timestamp}"
        }
    }

    return translations.get(text_key, {}).get(language, text_key)  # Default to English

def send_language_menu(user_id):
    """ Sends a menu allowing the user to choose their preferred language. """
    buttons_template = TemplateSendMessage(
        alt_text=get_translated_text(user_id, "choose_language"),
        template=ButtonsTemplate(
            text=get_translated_text(user_id, "choose_language"),
            actions=[
                PostbackAction(label="English", data="language_English"),
                PostbackAction(label="繁體中文", data="language_Chinese")
            ]
        )
    )
    line_bot_api.push_message(user_id, buttons_template)

def get_user_location():
    """ Fetches the user's estimated location from Google's Geolocation API. """
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    response = requests.post(url, json={})  # Empty JSON → Google will auto-detect location

    if response.status_code == 200:
        data = response.json()
        return data["location"]["lat"], data["location"]["lng"]  # Returns (latitude, longitude)
    else:
        print("🚨 Error fetching location:", response.text)
        return None, None

def calculate_distance(lat1, lon1, lat2, lon2):
    """ Calculates distance between two GPS coordinates in meters. """
    R = 6371000  # Radius of Earth in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2) * sin(dlat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) * sin(dlon/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def ask_location_permission(user_id):
    """ Sends a Yes/No button prompt to request location-sharing permission. """
    buttons_template = TemplateSendMessage(
        alt_text=get_translated_text(user_id, "allow_location"),
        template=ButtonsTemplate(
            text=get_translated_text(user_id, "allow_location"),
            actions=[
                PostbackAction(label=get_translated_text(user_id, "yes"), data="agree_location"),
                PostbackAction(label=get_translated_text(user_id, "no"), data="deny_location")
            ]
        )
    )
    line_bot_api.push_message(user_id, buttons_template)

def send_points_menu(user_id):
    """ Sends the points menu with two options. """
    buttons_template = TemplateSendMessage(
        alt_text=get_translated_text(user_id, "points_menu"),
        template=ButtonsTemplate(
            text=get_translated_text(user_id, "points_menu"),
            actions=[
                PostbackAction(label=get_translated_text(user_id, "progress"), data="check_progress"),
                PostbackAction(label=get_translated_text(user_id, "leaderboard"), data="view_leaderboard")
            ]
        )
    )
    line_bot_api.push_message(user_id, buttons_template)

def calculate_level(points):
    """ Returns the user's level and how many points are needed for the next level. """
    level = 1
    threshold = 50

    while points >= threshold:
        level += 1
        if level % 2 == 0:
            threshold += 50 # increase threshold every 2 levels

    points_to_next_level = threshold - points
    return level, points_to_next_level

def update_user_points(user_id, points_to_add):
    """ Updates the user's points and level when they scan a valid QR code. """
    cursor.execute("SELECT points FROM all_user_points WHERE user_id = ?", (user_id,))
    result = cursor.fetchone() # A tuple with one value

    if result:
        new_points = result[0] + points_to_add
    else:
        new_points = points_to_add

    # Calculate new level
    new_level, points_needed = calculate_level(new_points)

    # Update points and level in database
    cursor.execute("""
        INSERT INTO all_user_points (user_id, points, level, points_to_next_level)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
        points = ?, level = ?, points_to_next_level = ?
    """, (user_id, new_points, new_level, points_needed, new_points, new_level, points_needed))
    conn.commit()

def update_leaderboard():
    """ Updates the leaderboard ranking for all users. """
    cursor.execute("SELECT user_id, points FROM all_user_points ORDER BY points DESC")
    users = cursor.fetchall()

    if not users:
        return
    
    # Assign ranks
    for rank, (user_id, _) in enumerate(users, start = 1):
        cursor.execute("UPDATE all_user_points SET ranking = ? WHERE user_id = ?", (rank, user_id))

    conn.commit()

def view_leaderboard(user_id):
    """ Shows the user's rank and top 3 users. """
    cursor.execute("SELECT user_id, points, level, ranking FROM all_user_points ORDER BY ranking ASC LIMIT 3")
    top_users = cursor.fetchall()

    # Get the user's rank
    cursor.execute("SELECT points, level, ranking FROM all_user_points WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        send_line_message(user_id, "no_points_yet")
        return
    
    user_points, user_level, user_rank = user_data

    # Rank message
    rank_message = get_translated_text(user_id, "your_ranking").format(rank=user_rank)

    # Get next and previous ranks
    cursor.execute("SELECT points FROM all_user_points WHERE ranking = ?", (user_rank - 1,))
    higher_rank_data = cursor.fetchone()

    cursor.execute("SELECT points FROM all_user_points WHERE ranking = ?", (user_rank + 1,))
    lower_rank_data = cursor.fetchone()

    if higher_rank_data:
        rank_message += get_translated_text(user_id, "points_needed_to_rank_up").format(
            points_needed=bold_text(str(higher_rank_data[0] - user_points)),
            higher_rank=bold_text(f"#{user_rank - 1}")
        ) + "\n"

    if lower_rank_data:
        rank_message += get_translated_text(user_id, "points_ahead").format(
            points_ahead=bold_text(str(user_points - lower_rank_data[0])),
            lower_rank=bold_text(f"#{user_rank + 1}")
        ) + "\n"

    # Top 3 users
    top_message = get_translated_text(user_id, "top_climbers")

    medal_emojis = ["🥇", "🥈", "🥉"]
    for i, (uid, points, level, rank) in enumerate(top_users, start=1):
        medal = medal_emojis[i - 1] if i <= 3 else "🎖️"  # Use medals for top 3, others get a trophy
        top_message += get_translated_text(user_id, "rank_info").format(
            medal=medal,
            rank=rank,
            level=level,
            points=points
        )

    send_line_message(user_id, rank_message + "\n" + top_message)

def check_progress(user_id):
    """ Sends the user's current progress. """
    cursor.execute("SELECT points, level, points_to_next_level FROM all_user_points WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        user_points, user_level, user_points_to_next_level = result
        # Get translated messages
        progress_header = get_translated_text(user_id, "your_progress")
        current_level_msg = get_translated_text(user_id, "current_level").format(
            bold_level=bold_text(f"Level {user_level}"),
            bold_points=bold_text(f"{user_points} points")
        )
        points_needed_msg = get_translated_text(user_id, "points_needed").format(
            bold_needed_points=bold_text(f"{user_points_to_next_level} more points"),
            bold_next_level=bold_text(f"Level {user_level + 1}")
        )
        keep_climbing_msg = get_translated_text(user_id, "keep_climbing")

        response_message = f"{progress_header}\n{current_level_msg}\n{points_needed_msg}\n{keep_climbing_msg}"

    else:
        response_message = "no_points_yet"
    
    send_line_message(user_id, response_message)

# what should I do when the user first adds the bot? 
@handler.add(FollowEvent) 
def handle_follow(event):
    """ When a user adds the bot, send a personalized welcome message and ask for language preference and location permission"""
    user_id = event.source.user_id

    try:
        # Fetch user's display name from LINE profile
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name  # Extract the user's name

        # Send a personalized welcome message
        welcome_message = f"Hi {user_name}! 🎉 Welcome to Staircase Fairy!\n"
        welcome_message += f"哈囉 {user_name}！歡迎來到樓梯精靈！🏃‍♂️🏃‍♀️"

        line_bot_api.push_message(user_id, TextSendMessage(text=welcome_message))

        # language settings: choose english or chinese
        send_language_menu(user_id)

        # Ask for location permission
        ask_location_permission(user_id)

    except Exception as e:
        app.logger.error(f"Error fetching user profile: {e}")
        # Fallback if unable to fetch name
        line_bot_api.push_message(user_id, TextSendMessage(text="Hi! 🎉 Welcome to Staircase Fairy!\n哈囉！歡迎來到樓梯精靈！🏃‍♂️🏃‍♀️"))
        send_language_menu(user_id)
        ask_location_permission(user_id)

# handle responses from buttons
@handler.add(PostbackEvent)
def handle_postback(event):
    """ Handle user response to location sharing consent. """
    user_id = event.source.user_id
    postback_data = event.postback.data

    if postback_data.startswith("language_"):
        selected_language = postback_data.split("_")[1]
        cursor.execute("INSERT OR REPLACE INTO user_settings (user_id, language) VALUES (?, ?)", (user_id, selected_language))
        conn.commit()
        response_message = get_translated_text(user_id, "set_language").format(selected_language=selected_language)
        send_line_message(user_id, response_message)

    # Handle point collection system
    elif postback_data == "check_progress":
        check_progress(user_id)
    elif postback_data == "view_leaderboard":
        update_leaderboard()
        view_leaderboard(user_id)

    # Handle location permission
    elif postback_data == "agree_location":
        # Ensure the user exists in user_settings before updating
        cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, location_consent) VALUES (?, 0)", (user_id,))
        cursor.execute("UPDATE user_settings SET location_consent = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        send_line_message(user_id, "location_enabled")
    elif postback_data == "deny_location":
        cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, location_consent) VALUES (?, 0)", (user_id,))
        cursor.execute("UPDATE user_settings SET location_consent = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        send_line_message(user_id, "location_denied")

# handle messages from users
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Handles messages and routes them based on content."""
    try:
        user_message = event.message.text
        user_message_stripped_lower = event.message.text.strip().lower()
        user_id = event.source.user_id

        # If the message is a QR code scan, delegate it to `handle_qr_scan`
        if user_message.startswith("STAIRCASE_QR_"):
            handle_qr_scan(user_id, user_message)
            return

        # Language settings
        if user_message.startswith("language"):
            send_language_menu(user_id)
        
        # Points: user progress, leaderboard
        if user_message_stripped_lower.startswith("points"):
            send_points_menu(user_id)

        # Easter eggs
        if user_message_stripped_lower.startswith("mexico"):
            send_line_message(user_id, "🇲🇽🌮🌯")

    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

def handle_qr_scan(user_id, user_message):
    """Handles QR code scan messages."""
    try:
        _, _, floor, location = user_message.split("_")
        print(floor, location)

        # Get the current timestamp
        current_time = datetime.datetime.now()

        # Check if the user allowed location tracking
        cursor.execute("SELECT location_consent FROM user_settings WHERE user_id = ?", (user_id,))
        consent = cursor.fetchone()

        if not consent or consent[0] == 0:
            send_line_message(user_id, "need_to_allow_location")
            ask_location_permission(user_id) # Ask for permission again
            return
        
        # Fetch the user's location automatically
        user_lat, user_lng = get_user_location()
        print(user_lat, user_lng)

        if user_lat is None:
            send_line_message(user_id, "cant_fetch_location")
            return
            
        # Predefined QR Code Locations (Grouped by Location)
        QR_LOCATIONS = {
            "機械系館1": {
                "coordinates": (25.0216448, 121.5463424),
                "available_floors": [f"{i}F" for i in range(1, 6)]  # Floors 1F to 5F
            },
            "機械系館2": {
                "coordinates": (25.0189335, 121.5392110),
                "available_floors": [f"{i}F" for i in range(1, 5)]  # Floors 1F to 4F
            }
        }

        if location not in QR_LOCATIONS:
            send_line_message(user_id, "invalid_qrcode")
            return

        # Check if the scanned floor is available for this location
        if floor not in QR_LOCATIONS[location]["available_floors"]:
            response_message = get_translated_text(user_id, "floor_unavailable").format(
                location_name=location,
                floor=floor
            )
            send_line_message(user_id, response_message)
            return

        # Use the same coordinates for all floors in the location
        qr_lat, qr_lng = QR_LOCATIONS[location]["coordinates"]

        # Check distance
        distance = calculate_distance(user_lat, user_lng, qr_lat, qr_lng)

        if distance > 50:
            send_line_message(user_id, "too_far_away")
            return

        # Check the last scan time for the user
        cursor.execute("""
            SELECT timestamp FROM scan_logs WHERE user_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id,))
        last_scan = cursor.fetchone()

        if last_scan:
            last_scan_time = datetime.datetime.strptime(last_scan[0], "%Y/%m/%d %H:%M:%S")
            time_difference = (current_time - last_scan_time).total_seconds()

            if time_difference < 15.000:
                send_line_message(user_id, "wait_longer")
                return

        # Log the scan in the database
        timestamp = current_time.strftime("%Y/%m/%d %H:%M:%S")
        cursor.execute("INSERT INTO scan_logs (user_id, floor, location, timestamp) VALUES (?, ?, ?, ?)", 
                        (user_id, floor, location, timestamp))
        conn.commit()

        # Send success message
        success_message = get_translated_text(user_id, "scan_success").format(
            point=1,
            location=location,
            floor=floor,
            timestamp=timestamp
        )
        send_line_message(user_id, success_message)
        
        # Update user_points table
        update_user_points(user_id, 1)
    
    except Exception as e:
        app.logger.error(f"Error handling QR scan: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming messages from LINE users."""
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info("📌 Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("🚨 Invalid signature. Check your channel secret.")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        app.logger.error(f"🚨 Error: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": 200})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
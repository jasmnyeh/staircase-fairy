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
BOT_FRIEND_INVITE_URL = "https://line.me/R/ti/p/%40925keedn"

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
        location_consent INTEGER DEFAULT 0
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

def send_line_message(user_id, message):
    """ Sends a text message from the LINE bot to the user. """
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except Exception as e:
        print(f"🚨 Failed to send LINE message: {e}")

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
        alt_text="📍 Allow location sharing?",
        template=ButtonsTemplate(
            text="📍 To validate QR scans, we need access to your location. Do you agree?",
            actions=[
                PostbackAction(label="✅ Yes, share location", data="agree_location"),
                PostbackAction(label="❌ No, ask me again later", data="deny_location")
            ]
        )
    )
    line_bot_api.push_message(user_id, buttons_template)

def send_points_menu(user_id):
    """ Sends the points menu with two options. """
    buttons_template = TemplateSendMessage(
        alt_text="Choose an option",
        template=ButtonsTemplate(
            text="🎯 Points & Ranking System\nChoose an option below:",
            actions=[
                PostbackAction(label="📊 My Progress", data="check_progress"),
                PostbackAction(label="🏆 Leaderboard", data="view_leaderboard")
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
        send_line_message(user_id, "You haven't earned any points yet. Start climbing!")
        return
    
    user_points, user_level, user_rank = user_data

    rank_message = f"🏆 {bold_text('Your Ranking')}: #{user_rank}.\n"

    # Get next and previous ranks
    cursor.execute("SELECT points FROM all_user_points WHERE ranking = ?", (user_rank - 1,))
    higher_rank_data = cursor.fetchone()

    cursor.execute("SELECT points FROM all_user_points WHERE ranking = ?", (user_rank + 1,))
    lower_rank_data = cursor.fetchone()

    if higher_rank_data:
        rank_message += f"⬆️ You need {bold_text(str(higher_rank_data[0] - user_points))} more points to move up to rank {bold_text(f'#{user_rank - 1}')}\n"

    if lower_rank_data:
        rank_message += f"⬇️ You are {bold_text(str(user_points - lower_rank_data[0]))} points ahead of rank {bold_text(f'#{user_rank + 1}')}\n"

    # Top 3 users
    top_message = f"{bold_text('Top Climbers')}:\n"
    medal_emojis = ["🥇", "🥈", "🥉"]
    for i, (uid, points, level, rank) in enumerate(top_users, start=1):
        medal = medal_emojis[i - 1] if i <= 3 else "🎖️"  # Use medals for top 3, others get a trophy
        top_message += f"{medal} {bold_text(f'Rank {rank}')} - Level {level} ({points} points)\n"

    send_line_message(user_id, rank_message + "\n" + top_message)

def check_progress(user_id):
    """ Sends the user's current progress. """
    cursor.execute("SELECT points, level, points_to_next_level FROM all_user_points WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if result:
        user_points, user_level, user_points_to_next_level = result
        response_message = (
            f"📊 {bold_text('Your Progress')}:\n"
            f"You're at {bold_text(f'Level {user_level}')} with {bold_text(f'{user_points} points')}.\n"
            f"You need {bold_text(f'{user_points_to_next_level} more points')} to reach {bold_text(f'Level {user_level + 1}')}.\n"
            f"Keep climbing! 🚀"
        )
    else:
        response_message = "You haven't earned any points yet. Start climbing to earn rewards! 🏆"
    
    send_line_message(user_id, response_message)

# what should I do when the user first adds the bot? 
@handler.add(FollowEvent) 
def handle_follow(event):
    """ When a user adds the bot, ask for GPS location sharing consent. """
    user_id = event.source.user_id

    # send welcome message to user :) might need to modify? not sure
    send_line_message(user_id, "Hi {user_id}! Welcome to Staircase Fairy! \n哈囉 {user_id}! 歡迎來到樓梯精靈！")

    # language settings: choose english or chinese

    # ask for location permission
    ask_location_permission(user_id)


# handle responses from buttons
@handler.add(PostbackEvent)
def handle_postback(event):
    """ Handle user response to location sharing consent. """
    user_id = event.source.user_id
    postback_data = event.postback.data

    # Handle point collection system
    if postback_data == "check_progress":
        check_progress(user_id)
    elif postback_data == "view_leaderboard":
        update_leaderboard()
        view_leaderboard(user_id)

    # Handle location permission
    if postback_data == "agree_location":
        cursor.execute("UPDATE user_settings SET location_consent = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        send_line_message(user_id, "✅ You have agreed to share your location!")
    elif postback_data == "deny_location":
        send_line_message(user_id, "🚨 You have denied location sharing. We will ask again when needed.")

# handle qrcode scans
@handler.add(MessageEvent, message=TextMessage)
def handle_qr_scan(event):
    
    try:
        user_message = event.message.text
        user_message_stripped_lower = event.message.text.strip().lower()
        user_id = event.source.user_id

        # handles qrcode scans: ensures no duplicate scans within 15 seconds
        if user_message.startswith("STAIRCASE_QR_"):
            _, _, floor, location = user_message.split("_")

            # Get the current timestamp
            current_time = datetime.datetime.now()

            # Check if the user allowed location tracking
            cursor.execute("SELECT location_consent FROM user_settings WHERE user_id = ?", (user_id,))
            consent = cursor.fetchone()

            if not consent or consent[0] == 0:
                send_line_message(user_id, "🚨 You need to allow location tracking first.")
                ask_location_permission(user_id) # Ask for permission again
                return
            
            # Fetch the user's location automatically
            user_lat, user_lng = get_user_location()

            if user_lat is None:
                send_line_message(user_id, "🚨 Unable to fetch location. Try again later.")
                return
            
            # Predefined QR Code Locations (Example)
            QR_LOCATIONS = {
                "1F_機械系館1": (25.0190037, 121.5395211),
                "2F_機械系館1": (25.0191037, 121.5396211),
                "3F_機械系館1": (25.0190037, 121.5395211),
                "4F_機械系館1": (25.0190037, 121.5395211),
                "5F_機械系館1": (25.0190037, 121.5395211),
                "1F_機械系館2": (25.0190037, 121.5395211),
                "2F_機械系館2": (25.0190037, 121.5395211),
                "3F_機械系館2": (25.0190037, 121.5395211),
                "4F_機械系館2": (25.0190037, 121.5395211),
                "5F_機械系館2": (25.0190037, 121.5395211)
            }

            qr_key = f"{floor}_{location}"
            if qr_key not in QR_LOCATIONS:
                send_line_message(user_id, "🚫 Invalid QR Code.")
                return

            qr_lat, qr_lng = QR_LOCATIONS[qr_key]

            # Check distance
            distance = calculate_distance(user_lat, user_lng, qr_lat, qr_lng)

            if distance > 50:
                send_line_message(user_id, "🚫 Scan failed! You are too far from the QR code location.")
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
                    send_line_message(user_id, "🚫 You must wait at least 15 seconds before scanning again.")
                    return

            # Log the scan in the database
            timestamp = current_time.strftime("%Y/%m/%d %H:%M:%S")
            cursor.execute("INSERT INTO scan_logs (user_id, floor, location, timestamp) VALUES (?, ?, ?, ?)", 
                           (user_id, floor, location, timestamp))
            conn.commit()

            # Send success message
            success_message = (
                f"🎉 {bold_text('Great job!')} You've earned {bold_text('+1 point!')}\n"
                f"📍 {bold_text('Location')}: {location}\n"
                f"🏢 {bold_text('Floor')}: {floor}\n"
                f"🕒 {bold_text('Time')}: {timestamp}"
            )
            send_line_message(user_id, success_message)
            
            # Update user_points table
            update_user_points(user_id, 1)
    
    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

# handle messages from users
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    try:
        user_message = event.message.text
        user_message_stripped_lower = event.message.text.strip().lower()
        user_id = event.source.user_id

        # points: user progress, leaderboard
        if user_message_stripped_lower.startswith("points"):
            send_points_menu(user_id)

        # easter eggs
        if user_message_stripped_lower.startswith("mexico"):
            send_line_message(user_id, "🇲🇽🌮🌯")

    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

def request_user_location(user_id, floor, location, qr_lat, qr_lng):
    """ Sends a location request to the user inside LINE. """
    send_line_message(user_id, "📍 Please share your current location to verify your QR scan.")
    line_bot_api.push_message(user_id, TextSendMessage(text="Tap '+' in the chat and select 'Location'."))

# When user sends location message, contains latitude and longitude
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    """ Handles location messages sent by users and validates against the QR location. """
    try:
        user_id = event.source.user_id
        user_lat = event.message.latitude
        user_lng = event.message.longitude

        # Retrieve the last scanned QR code location
        cursor.execute("SELECT floor, location, gps_lat, gps_lng FROM scan_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,))
        scan_data = cursor.fetchone()

        if not scan_data:
            send_line_message(user_id, "🚫 No QR scan detected. Please scan a QR code first.")
            return

        floor, location, qr_lat, qr_lng = scan_data
        distance = calculate_distance(user_lat, user_lng, qr_lat, qr_lng)

        if distance > 20:
            send_line_message(user_id, "🚫 You are too far from the QR code location. Scan invalid.")
            return

        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        cursor.execute("INSERT INTO scan_logs (user_id, floor, location, gps_lat, gps_lng, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, floor, location, user_lat, user_lng, timestamp))
        conn.commit()

        success_message = f"🎉 Great job! You've earned +1 point!\n📍 Location: {location}\n🏢 Floor: {floor}\n🕒 Time: {timestamp}"
        send_line_message(user_id, success_message)

    except Exception as e:
        app.logger.error(f"Error handling location: {e}")

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
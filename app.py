from flask import Flask, request, jsonify
import os
import sqlite3
import datetime
# from math import radians, cos, sin, sqrt, atan2
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, PostbackEvent, PostbackAction, TemplateSendMessage, ButtonsTemplate, LocationMessage

app = Flask(__name__)

# Securely store access token and channel secret
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET_HERE")

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
conn.commit()

# # Create user_settings table to store location sharing consent
# cursor.execute("""
#     CREATE TABLE IF NOT EXISTS user_settings (
#         user_id TEXT PRIMARY KEY,
#         location_consent INTEGER DEFAULT 0
#     )
# """)
# conn.commit()

def send_line_message(user_id, message):
    """ Sends a text message from the LINE bot to the user. """
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except Exception as e:
        print(f"🚨 Failed to send LINE message: {e}")

def calculate_distance(lat1, lon1, lat2, lon2):
    """ Calculates distance between two GPS coordinates in meters. """
    R = 6371000  # Radius of Earth in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2) * sin(dlat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) * sin(dlon/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# what should I do when the user first adds the bot? 
# have to modify!!
@handler.add(FollowEvent) 
def handle_follow(event):
    """ When a user adds the bot, ask for GPS location sharing consent. """
    user_id = event.source.user_id

    # send welcome message to user :) might need to modify? not sure
    send_line_message(user_id, "Hi {user_id}! Welcome to Staircase Fairy! \n哈囉 {user_id}! 歡迎來到樓梯精靈！")

    # # Store user in the database with default consent = 0 (not agreed yet)
    # cursor.execute("INSERT OR IGNORE INTO user_settings (user_id, location_consent) VALUES (?, 0)", (user_id,))
    # conn.commit()

    # # Create Yes/No button template message
    # buttons_template = TemplateSendMessage(
    #     alt_text="Would you like to share your location for QR scans?",
    #     template=ButtonsTemplate(
    #         text="📍 To track your stair-climbing progress, we need access to your location. Do you agree?",
    #         actions=[
    #             PostbackAction(label="Yes", data="agree_location"),
    #             PostbackAction(label="No", data="deny_location")
    #         ]
    #     )
    # )
    
    # line_bot_api.push_message(user_id, buttons_template)

# handle responses from buttons
@handler.add(PostbackEvent)
def handle_postback(event):
    """ Handle user response to location sharing consent. """
    user_id = event.source.user_id
    postback_data = event.postback.data

    if postback_data == "agree_location":
        cursor.execute("UPDATE user_settings SET location_consent = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        send_line_message(user_id, "✅ You have agreed to share your location! QR scans will now verify your GPS position automatically.")
    elif postback_data == "deny_location":
        send_line_message(user_id, "🚨 You have denied location sharing. You will be asked again during each QR scan.")

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """ Handles QR code scan messages and checks user consent before requesting GPS location. """
    try:
        user_message = event.message.text
        user_message_stripped_lower = event.message.text.strip().lower()
        user_id = event.source.user_id

        if user_message.startswith("STAIRCASE_QR_"):
            _, _, floor, location, qr_lat, qr_lng = user_message.split("_")
            print(f"Floor: {floor}")         # Output: 1F
            print(f"Location: {location}")   # Output: 機械系館_1
            print(f"Latitude: {qr_lat}")     # Output: 25.031757
            print(f"Longitude: {qr_lng}")    # Output: 121.544729
            qr_lat, qr_lng = float(qr_lat), float(qr_lng)

            # Check if the user has agreed to share location
            cursor.execute("SELECT location_consent FROM user_settings WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()

            if not result or result[0] == 0:
                send_line_message(user_id, "🚨 You need to agree to location sharing first.")
                handle_follow(event)  # Re-send the consent message
                return

            # Request user location
            request_user_location(user_id, floor, location, qr_lat, qr_lng)

    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

def request_user_location(user_id, floor, location, qr_lat, qr_lng):
    """ Sends a location request to the user inside LINE. """
    send_line_message(user_id, "📍 Please share your current location to verify your QR scan.")
    line_bot_api.push_message(user_id, TextSendMessage(text="Tap '+' in the chat and select 'Location'."))

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

        success_message = f"✅ Scan successful!\n📍 Location: {location}\n🏢 Floor: {floor}\n🕒 Time: {timestamp}"
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
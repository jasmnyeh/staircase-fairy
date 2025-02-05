from flask import Flask, request, jsonify, redirect
import os
import sqlite3  # For storing scan logs
import datetime
from math import radians, cos, sin, sqrt, atan2
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, LocationMessage

app = Flask(__name__)

# Securely store access token and channel secret
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET_HERE")
BOT_ID = "@925keedn"
BOT_FRIEND_INVITE_URL = "https://line.me/R/ti/p/%40925keedn"

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Database setup
conn = sqlite3.connect("scans.db", check_same_thread=False)
cursor = conn.cursor()

# create scan_logs table to store QR scan records
cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        floor TEXT,
        location TEXT,
        gps_lat REAL,
        gps_lng REAL,
        timestamp TEXT
    )
""")
conn.commit()

# Create user_settings table to store user consent for location sharing
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        location_consent INTEGER DEFAULT 0
    )
""")
conn.commit()

# Predefined QR code locations 
# need to change when changing locations!!!
QR_LOCATIONS = {
    "1F_機械系館_1": (25.031757, 121.544729),
    "2F_機械系館_1": (25.031757, 121.544729),
    "3F_機械系館_1": (25.031757, 121.544729),
    "4F_機械系館_1": (25.031757, 121.544729),
    "5F_機械系館_1": (25.031757, 121.544729)
}

def send_line_message(user_id, message):
    """ Sends a message from the line bot to the user """
    try:
        line_bot_api.push_message(user_id, TextSendMessage(text=message))
    except Exception as e:
        print(f"🚨 Failed to send LINE message: {e}")

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2) * sin(dlat/2) + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) * sin(dlon/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

@app.route("/scan_qr", methods=["GET"])
def scan_qr():
    """
    When the user scans a QR code, this route requests GPS permission.
    """
    floor = request.args.get("floor", "Unknown")
    location = request.args.get("location", "Unknown")
    user_id = request.args.get("user_id") # LINE user id must be passed

    if not user_id:
        return redirect(BOT_FRIEND_INVITE_URL, code = 302) # Redirect to add bot
    return render_template("request_location.html", floor=floor, location=location, user_id=user_id)

@app.route("/verify_location", methods=["POST"])
def verify_location():
    """
    Receives GPS coordinates from the user and verifies their proximity to the QR code.
    If valid, logs the scan and sends a success message via LINE.
    """
    try:
        user_lat = float(request.form.get("latitude"))
        user_lng = float(request.form.get("longitude"))
        floor = request.form.get("floor")
        location = request.form.get("location")
        user_id = request.form.get("user_id")

        qr_key = f"{floor}_{location.replace(' ', '_')}"
        expected_lat, expected_lng = QR_LOCATIONS.get(qr_key, (None, None))
    
        if expected_lat is None:
            send_line_message(user_id, "🚫 Invalid QR code.")
            return "Invalid QR code", 400
        
        # check if user is within 20 meters of the QR location
        distance = calculate_distance(user_lat, user_lng, expected_lat, expected_lng)

        if distance > 20:
            send_line_message(user_id, "🚫 You are too far from the QR code location. Scan invalid.")
            return "Too far from QR location", 400
        
        # log scan if within range
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        cursor.execute("INSERT INTO scan_logs (user_id, floor, location, timestamp) VALUES (?, ?, ?, ?)", 
                       (user_id, floor, location, timestamp))
        conn.commit()

        # send success message via LINE bot
        success_message = f"✅ Scan successful!\n📍 Location: {location}\n🏢 Floor: {floor}\n🕒 Time: {timestamp}"
        send_line_message(user_id, success_message)

        return "Scan logged successfully", 200
    
    except Exception as e:
        return f"🚨 Error processing GPS verification: {e}", 500

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """
    Handles text messages from users and logs scan data.
    """
    try:
        user_message = event.message.text  # Get the message content
        user_message_stripped = event.message.text.strip().lower()
        user_id = event.source_user_id

        print(f"📌 Received message from {user_id}: {user_message}")

        # Check if the user is agreeing to location sharing
        if user_message == "i agree":
            cursor.execute("UPDATE user_settings SET location_consent = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

            send_line_message(user_id, "✅ You have agreed to share your location! QR scans will now use your GPS automatically.")
            return
        # would this led to a problem where if the user type i agree then it'll send this??

        # Handle regular text messages
        reply_text = f"You said: {user_message}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

@handler.add(FollowEvent)
def handle_follow(event):
    """
    Triggered when a user adds the bot as a friend.
    Sends a message asking for location sharing consent.
    """
    user_id = event.source.user_id

    # Store user in the database with default consent = 0 (hasn't agreed)
    cursor.execute("INSERT OR IGNORE INTO user_setting (user_id, location_consent) VALUES (?, 0)", (user_id,))
    conn.commit()

    consent_message = (
        "📍 To track your stair-climbing progress, we need access to your location.\n\n"
        "Do you agree to share your location when scanning a QR code?\n"
        "Reply with 'I agree' to continue."
    )

    line_bot_api.push_message(user_id, TextSendMessage(text=consent_message))

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
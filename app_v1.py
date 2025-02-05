from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.webhooks import MessageEvent, TextMessageContent, LocationMessageContent, PostbackEvent
from linebot.v3.messaging import TextMessage, TemplateMessage, ButtonsTemplate, PostbackAction
from linebot.v3.exceptions import InvalidSignatureError
import os
import json
import sqlite3
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

# Configuration
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET_HERE")

# Initialize LINE API client
configuration = Configuration(access_token=LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Database initialization
def init_db():
    conn = sqlite3.connect('line_bot.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id TEXT PRIMARY KEY,
            location_permission BOOLEAN,
            last_updated TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Calculate distance between two points using Haversine formula
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth's radius in meters

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def get_user_permission(user_id):
    conn = sqlite3.connect('line_bot.db')
    c = conn.cursor()
    c.execute('SELECT location_permission FROM user_permissions WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_user_permission(user_id, permission):
    conn = sqlite3.connect('line_bot.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO user_permissions (user_id, location_permission, last_updated)
        VALUES (?, ?, ?)
    ''', (user_id, permission, datetime.now()))
    conn.commit()
    conn.close()

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_id = event.source.user_id
        text = event.message.text

        # Check if the message is a QR code scan
        try:
            qr_data = json.loads(text)
            if all(k in qr_data for k in ['name', 'floor', 'latitude', 'longitude']):
                permission = get_user_permission(user_id)
                
                if permission is None:
                    # Ask for location permission
                    buttons_template = ButtonsTemplate(
                        title='Location Permission',
                        text='Would you like to share your location for QR code verification?',
                        actions=[
                            PostbackAction(label='Yes', data='location_permission_yes'),
                            PostbackAction(label='No', data='location_permission_no')
                        ]
                    )
                    template_message = TemplateMessage(
                        alt_text='Location Permission Request',
                        template=buttons_template
                    )
                    line_bot_api.reply_message_with_http_info({
                        "replyToken": event.reply_token,
                        "messages": [template_message]
                    })
                elif not permission:
                    # Remind user to grant location permission
                    buttons_template = ButtonsTemplate(
                        title='Location Permission Required',
                        text='Location permission is required for QR code verification.',
                        actions=[
                            PostbackAction(label='Grant Permission', data='location_permission_yes'),
                            PostbackAction(label='No Thanks', data='location_permission_no')
                        ]
                    )
                    template_message = TemplateMessage(
                        alt_text='Location Permission Required',
                        template=buttons_template
                    )
                    line_bot_api.reply_message_with_http_info({
                        "replyToken": event.reply_token,
                        "messages": [template_message]
                    })
                else:
                    # Request user's current location
                    line_bot_api.reply_message_with_http_info({
                        "replyToken": event.reply_token,
                        "messages": [TextMessage(text="Please share your current location.")]
                    })
        except json.JSONDecodeError:
            # Not a QR code message, handle normal text
            pass

@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_location = event.message
        user_id = event.source.user_id

        # Get the last scanned QR code data (you'll need to implement this storage)
        qr_data = get_last_scanned_qr(user_id)  # Implement this function
        
        if qr_data:
            distance = calculate_distance(
                user_location.latitude,
                user_location.longitude,
                float(qr_data['latitude']),
                float(qr_data['longitude'])
            )

            if distance <= 20:  # Within 20 meters
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                success_message = (
                    f"✅ Scan successful!\n"
                    f"📍 Location: {qr_data['name']}\n"
                    f"🏢 Floor: {qr_data['floor']}\n"
                    f"🕒 Time: {timestamp}"
                )
                line_bot_api.reply_message_with_http_info({
                    "replyToken": event.reply_token,
                    "messages": [TextMessage(text=success_message)]
                })
            else:
                line_bot_api.reply_message_with_http_info({
                    "replyToken": event.reply_token,
                    "messages": [TextMessage(text="🚫 You are too far from the QR code location. Scan invalid.")]
                })

@handler.add(PostbackEvent)
def handle_postback(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_id = event.source.user_id
        data = event.postback.data

        if data == 'location_permission_yes':
            set_user_permission(user_id, True)
            line_bot_api.reply_message_with_http_info({
                "replyToken": event.reply_token,
                "messages": [TextMessage(text="Thank you! You can now scan QR codes with location verification.")]
            })
        elif data == 'location_permission_no':
            set_user_permission(user_id, False)
            line_bot_api.reply_message_with_http_info({
                "replyToken": event.reply_token,
                "messages": [TextMessage(text="You'll need to grant location permission to verify QR code scans.")]
            })

if __name__ == "__main__":
    init_db()
    app.run(port=5001, debug=True)
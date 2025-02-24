from flask import Flask, request, jsonify, redirect
import os
import sqlite3
import datetime
import requests
import urllib.parse
import random
from math import radians, cos, sin, sqrt, atan2
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, PostbackEvent, PostbackAction, TemplateSendMessage, ButtonsTemplate, LocationMessage, StickerMessage, CarouselTemplate, CarouselColumn, URITemplateAction
# import logging
# logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET_HERE")
BOT_ID = "@925keedn"

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

# Create table for feedback
cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        report TEXT,
        timestamp TEXT
    )
""")
conn.commit()

# Define some random responses
STICKER_RESPONSES = [
    "You got taste!",
    "😎",
    "Are you reading my mind???",
    "G'day mate!",
    ":D :P :O :3",
    "Fun fact: The fear of long words is called Hippopotomonstrosesquippedaliophobia.",
    "Fun fact: Snails have teeth",
    "Fun fact: One in 18 people have a third nipple.",
    "Fun fact: You travel 2.5 million km a day around the Sun without realising.",
    "Fun fact: Your brain burns 400-500 calories a day.",
    "Fun fact: A cloud weighs around a million tonnes.",
    "Wait ✋ They don't love you like I love you 💃🕺",
    "😬",
    "💍?",
    "🤜",
    "🤠",
    "I'm bored talk to me",
    "Nani?!?!??!",
    "What should I have for lunch 🤨",
    "lalalalalalalala",
    "I'm so done with you",
    "Love ya! <3",
    "live, love, laugh 😀✨"
]

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
            "English": "✅ Language set to English!",
            "Chinese": "✅ 語言已設定成繁體中文！"
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
            "Chinese": "🏆【您的排名】：#{rank}。"
        },
        "points_needed_to_rank_up": {
            "English": "⬆️ You need {points_needed} more points to move up to rank {higher_rank}.",
            "Chinese": "⬆️ 您還需要 {points_needed} 點才能升至 {higher_rank}。"
        },
        "points_ahead": {
            "English": "⬇️ You are {points_ahead} points ahead of rank {lower_rank}.",
            "Chinese": "⬇️ 您比 {lower_rank} 領先 {points_ahead} 點。",
        },
        "top_climbers": {
            "English": "🏆 𝗧𝗼𝗽 𝗖𝗹𝗶𝗺𝗯𝗲𝗿𝘀:\n",
            "Chinese": "🏆【高手們】：\n"
        },
        "rank_info": {
            "English": "{medal} Rank {rank} - {points} points (Level {level})\n",
            "Chinese": "{medal} 排名 {rank} - {points} 點（等級 {level}）\n"
        },
        "your_progress": {
            "English": "📊 𝗬𝗼𝘂𝗿 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀:",
            "Chinese": "📊【您的進度】："
        },
        "current_level": {
            "English": "You're at 𝗟𝗲𝘃𝗲𝗹 {bold_level} with {bold_points} 𝗽𝗼𝗶𝗻𝘁𝘀.",
            "Chinese": "您目前處於等級 {bold_level}，擁有 {bold_points} 點。"
        },
        "points_needed": {
            "English": "You need {bold_needed_points} 𝗺𝗼𝗿𝗲 𝗽𝗼𝗶𝗻𝘁𝘀 to reach 𝗟𝗲𝘃𝗲𝗹 {bold_next_level}.",
            "Chinese": "您還需要 {bold_needed_points} 點，才能達到等級 {bold_next_level}。"
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
                        "📍【位置】：{location}\n"
                        "🏢【樓層】：{floor}\n"
                        "🕒【時間】：{timestamp}"
        },
        "issue_feedback": {
            "English": "I would like to provide feedback or report an issue:\n",
            "Chinese": "我想提供回饋或回報問題：\n"
        },
        "report_url": {
            "English": "💬 Have feedback or an issue? Tell us here: {line_url}",
            "Chinese": "💬 歡迎在這裡分享您的想法或回報遇到的問題！：{line_url}"
        },
        "issue_received": {
            "English": "Thank you for your feedback! We appreciate your input and will review your message as soon as possible. 🚀",
            "Chinese": "謝謝您的回覆！我們將會儘速查看您的訊息 🚀"
        },
        "how_to_play": {
            "English": "🏆 𝗛𝗼𝘄 𝘁𝗼 𝗣𝗹𝗮𝘆 𝗦𝘁𝗮𝗶𝗿𝗰𝗮𝘀𝗲 𝗙𝗮𝗶𝗿𝘆! 🏆\n\n"
                        "✨ 𝗦𝗰𝗮𝗻 𝗘𝗮𝗰𝗵 𝗙𝗹𝗼𝗼𝗿\n"
                        "Scan the 𝗤𝗥 𝗰𝗼𝗱𝗲 on every floor as you climb! This logs your progress and helps you earn points.\n\n"
                        "🚀 𝗖𝗹𝗶𝗺𝗯 & 𝗖𝗼𝗺𝗽𝗲𝘁𝗲\n"
                        "The more you climb, the more points you collect! Check the 𝗹𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱 to see how you rank among other players.\n\n"
                        "🎉 𝗪𝗶𝗻 & 𝗖𝗲𝗹𝗲𝗯𝗿𝗮𝘁𝗲\n"
                        "Climb to the 𝘁𝗼𝗽 𝗼𝗳 𝘁𝗵𝗲 𝗹𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱 and unlock 𝗲𝘅𝗰𝗹𝘂𝘀𝗶𝘃𝗲 𝗿𝗲𝘄𝗮𝗿𝗱𝘀 every month! Keep going and challenge yourself! 🚀",
            "Chinese": "🏆 遊戲玩法 🏆\n\n"
                        "✨【每層掃一次】\n"
                        "每爬一層樓，記得掃描貼在樓梯間的QR碼，即可獲得一點！\n\n"
                        "🚀【挑戰排行榜】\n"
                        "爬越多層樓梯，累積越多點數，衝上排行榜！\n\n"
                        "🎉【贏得獎勵】\n"
                        "站上排行榜頂端，解鎖每月限定的專屬獎勵！快來加入挑戰吧！🚀"
        },
        "default_response": {
            "English": "🚀 Keep climbing and earning points! Every step brings you closer to the top! 🏆\n\n"
                        "For more info, check out the menu below. 📋\n\n"  
                        "💬 Have questions, found an issue, or want to share feedback? Head to \"Others → Feedback/Issue report\" and let us know! 📝",
            "Chinese": "🚀 加油加油繼續爬樓梯累積點數吧！🏆\n"
                        "更多資訊請查看下方選單 📋\n"
                        "💬 有遇到任何問題或有話想說？點擊選單中的「其它→回饋/問題回報」區告訴我們吧！📝"
        },
        "about_us_msg": {
            "English": "🌟 About Us 🌟\n\n"
                        "Hello and welcome to the Staircase Fairy! 🧚‍♀️✨ We're Jasmine Yeh and Edward Teng, two spirited computer science students at the helm of this exciting project lead by Prof. Hsin-Tien Lin.\n"
                        "Why did we start this project? 🤔 Well, we're based in the bustling labs of the Mechanical Engineering Department, constantly inspired by gears and gadgets! But, we wanted to shift gears to something that impacts our planet positively. 🌍\n"
                        "Our mission? To turn every step you take on the staircase into a leap for environmental health! By swapping lifts for lifts of your feet, we aim to reduce our carbon footprint one floor at a time. It’s about making healthier choices for ourselves and Mother Earth. 🌱💪\n"
                        "Join us in climbing to a greener future—where each step counts not just for your health but for the planet’s too. Let’s step up to the challenge and make a difference together! Ready to rise? Let’s climb! 🚀\n"
                        "Feel free to contact us or reach out if you got any questions!\n\n"
                        "b12902135@ntu.edu.tw\n"
                        "b13902100@ntu.edu.tw",
            "Chinese": "🌟 關於我們 🌟\n\n"
                        "歡迎來到樓梯精靈的奇幻世界！🧚✨ 我們是Jasmine Yeh和Edward Teng，目前就讀資工系。\n"
                        "林心恬教授給了我們有趣的點子，促使樓梯精靈的誕生——希望能鼓勵大家到樓梯間尋找樓梯精靈們，參與有趣集點活動，進而少搭電梯，讓減碳成為日常，同時也讓身體更健康！\n"
                        "🌱💪一起用實際行動守護地球，一層樓一腳印，共同減少碳足跡。\n\n"
                        "若有任何問題，歡迎聯絡我們！\n"
                        "b12902135@ntu.edu.tw\n"
                        "b13902100@ntu.edu.tw"
        },
        "check_rewards": {
            "English": "🏆 Check out the rewards you can earn!",
            "Chinese": "🏆 快來查看當月獎品！"
        },
        "others_menu": {
            "English": "🛠️ Others",
            "Chinese": "🛠️ 其它"
        },
        "about_us_button": {
            "English": "🌟 About us",
            "Chinese": "🌟 關於我們"
        },
        "location_consent_button": {
            "English": "📍 Location consent",
            "Chinese": "📍 定位設定" 
        },
        "feedback_button": {
            "English": "💬 Issue & Feedback",
            "Chinese": "💬 回饋 / 問題回報" 
        },
        "impact_menu": {
            "English": "🌍 Choose an impact view:",
            "Chinese": "🌍 請選擇下列其中一項"
        },
        "my_impact": {
            "English": "📊 My Impact",
            "Chinese": "📊 個人影響力"
        },
        "all_users_impact": {
            "English": "🌏 All Users' Impact",
            "Chinese": "🌏 總體影響力"
        },
        "personal_impact_progress": {
            "English": "📊 𝗬𝗼𝘂𝗿 𝗣𝗲𝗿𝘀𝗼𝗻𝗮𝗹 𝗜𝗺𝗽𝗮𝗰𝘁:\n\n"
                        "🌿 𝗖𝗢𝟮 𝗘𝗺𝗶𝘀𝘀𝗶𝗼𝗻𝘀 𝗦𝗮𝘃𝗲𝗱: {co2_saved} kg\n"
                        "= 🌳 𝗧𝗿𝗲𝗲𝘀 𝗳𝗼𝗿 𝗢𝗳𝗳𝘀𝗲𝘁: {forest_offset} trees\n"
                        "= ♻️ 𝗪𝗮𝘀𝘁𝗲 𝗥𝗲𝗰𝘆𝗰𝗹𝗲𝗱: {waste_recycled} kg\n\n"
                        "Keep climbing and making a difference! 🚀",
            "Chinese": "📊【您的影響力】\n\n"
                        "🌿 減少的碳排放量：{co2_saved} 公斤\n"
                        "= 🌳 樹木吸收碳排放量：{forest_offset} 棵\n"
                        "= ♻️ 回收垃圾量：{waste_recycled} 公斤\n\n"
                        "繼續爬樓梯，讓世界變得更綠吧！🚀"
        },
        "all_users_impact_progress": {
            "English": "🌏 𝗔𝗹𝗹 𝗨𝘀𝗲𝗿𝘀' 𝗜𝗺𝗽𝗮𝗰𝘁:\n\n"
                        "🌿 𝗖𝗢𝟮 𝗘𝗺𝗶𝘀𝘀𝗶𝗼𝗻𝘀 𝗦𝗮𝘃𝗲𝗱: {co2_saved} kg\n"
                        "= 🌳 𝗧𝗿𝗲𝗲𝘀 𝗳𝗼𝗿 𝗢𝗳𝗳𝘀𝗲𝘁: {forest_offset} trees\n"
                        "= ♻️ 𝗪𝗮𝘀𝘁𝗲 𝗥𝗲𝗰𝘆𝗰𝗹𝗲𝗱: {waste_recycled} kg\n\n"
                        "Together, we're making a difference! 💪✨",
            "Chinese": "🌏【總體影響力】\n\n"
                        "🌿 減少的碳排放量：{co2_saved} 公斤\n"
                        "= 🌳 樹木吸收碳排放量：{forest_offset} 棵\n"
                        "= ♻️ 回收垃圾量：{waste_recycled} 公斤\n\n"
                        "大家一起努力，讓世界更美好！💪✨"
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

def send_impacts_menu(user_id):
    """ Sends a menu allowing the user to choose between personal and global impact statistics. """
    buttons_template = TemplateSendMessage(
        alt_text=get_translated_text(user_id, "impact_menu"),
        template=ButtonsTemplate(
            text=get_translated_text(user_id, "impact_menu"),
            actions=[
                PostbackAction(label=get_translated_text(user_id, "my_impact"), data="personal_impacts"),
                PostbackAction(label=get_translated_text(user_id, "all_users_impact"), data="all_users_impacts")
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

def send_others_menu(user_id):
    """ Sends the others menu with three options. """
    buttons_template = TemplateSendMessage(
        alt_text=get_translated_text(user_id, "others_menu"),
        template=ButtonsTemplate(
            text=get_translated_text(user_id, "others_menu"),
            actions=[
                PostbackAction(label=get_translated_text(user_id, "about_us_button"), data="read_about_us"),
                PostbackAction(label=get_translated_text(user_id, "location_consent_button"), data="ask_location_consent"),
                PostbackAction(label=get_translated_text(user_id, "feedback_button"), data="report_issue_feedback")
            ]
        )
    )
    line_bot_api.push_message(user_id, buttons_template)

def send_rewards(user_id):
    """ Sends an image carousel message showcasing rewards. """

    carousel_template = TemplateSendMessage(
        alt_text=get_translated_text(user_id, "check_rewards"),
        template=CarouselTemplate(columns=[
            CarouselColumn(
                thumbnail_image_url="https://drive.google.com/file/d/1gSR8F_Li-CrtGdzDu5oGYPDused8pPwN/view?usp=drive_link",
                title="🥇",
                text="Climb to the top of the leaderboard!"
            ),
            CarouselColumn(
                thumbnail_image_url="https://drive.google.com/file/d/1-ETkoVNtRXnt7EWSsqjZX7wneHbi5_Vj/view?usp=drive_link",
                title="🥈",
                text="Earn 150 points to unlock this reward!"
            ),
            CarouselColumn(
                thumbnail_image_url="https://drive.google.com/file/d/1bb3RPSVcGm6lAB-2NQ23IYP78fz3faw6/view?usp=drive_link",
                title="🥉",
                text="Earn 300 points to unlock this exclusive reward!"
            )
        ])
    )

    line_bot_api.push_message(user_id, carousel_template)

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
    rank_message = get_translated_text(user_id, "your_ranking").format(rank=bold_text(str(user_rank)))

    # Get next and previous ranks
    cursor.execute("SELECT points FROM all_user_points WHERE ranking = ?", (user_rank - 1,))
    higher_rank_data = cursor.fetchone()

    cursor.execute("SELECT points FROM all_user_points WHERE ranking = ?", (user_rank + 1,))
    lower_rank_data = cursor.fetchone()

    if higher_rank_data:
        rank_message += "\n" + get_translated_text(user_id, "points_needed_to_rank_up").format(
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
            bold_level=bold_text(f"{user_level}"),
            bold_points=bold_text(f"{user_points}")
        )
        points_needed_msg = get_translated_text(user_id, "points_needed").format(
            bold_needed_points=bold_text(f"{user_points_to_next_level}"),
            bold_next_level=bold_text(f"{user_level + 1}")
        )
        keep_climbing_msg = get_translated_text(user_id, "keep_climbing")

        response_message = f"{progress_header}\n{current_level_msg}\n{points_needed_msg}\n{keep_climbing_msg}"

    else:
        response_message = "no_points_yet"
    
    send_line_message(user_id, response_message)

def issue_feedback(user_id):
    """ Sends a pre-filled text to the user for reporting an issue. """

    # Predefined messages
    prefilled_text = get_translated_text(user_id, "issue_feedback")

    # URL-encode the message to replace spaces and special characters
    encoded_text = urllib.parse.quote(prefilled_text)

    # Generate a LINE URL scheme that pre-fills the message
    line_url = f"line://oaMessage/{BOT_ID}/?{encoded_text}"

    # Send the URL to the user so they can click and open a pre-filled text box
    response_message = get_translated_text(user_id, "report_url").format(line_url=line_url)
    send_line_message(user_id, response_message)

def save_report(user_id, report_text):
    """ Saves a user’s reported issue/feedback to the database. """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("INSERT INTO feedback (user_id, report, timestamp) VALUES (?, ?, ?)", 
                   (user_id, report_text, timestamp))
    conn.commit()

def calculate_co2_saved(stair_levels):
    """ Calculate kg of CO2 saved by climbing stairs instead of taking an elevator. """
    co2_per_level = 0.027  # kg CO2 saved per stair level climbed
    return round(stair_levels * co2_per_level, 2)

def calculate_forest_offset(co2_saved):
    """ Calculate equivalent number of trees needed to offset the same amount of CO2. """
    co2_sequestration_per_tree = 25  # kg CO2 absorbed per tree per year
    return round(co2_saved / co2_sequestration_per_tree, 2)

def calculate_waste_recycled(co2_saved):
    """ Calculate kg of waste recycled to achieve the same CO2 reduction. """
    co2_saved_per_kg_waste = 2.87  # 1 kg waste recycled = 2.87 kg CO2 saved
    return round(co2_saved / co2_saved_per_kg_waste, 2)

def send_personal_impact(user_id):
    """ Sends the user's personal environmental impact statistics. """
    cursor.execute("SELECT SUM(floor) FROM scan_logs WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    stair_levels = result[0] if result and result[0] else 0

    co2_saved = calculate_co2_saved(stair_levels)
    forest_offset = calculate_forest_offset(co2_saved)
    waste_recycled = calculate_waste_recycled(co2_saved)

    message = get_translated_text(user_id, "personal_impact_progress").format(
        co2_saved=co2_saved,
        forest_offset=forest_offset,
        waste_recycled=waste_recycled
    )
    send_line_message(user_id, message)

def send_all_users_impact(user_id):
    """ Sends the total environmental impact from all users. """
    cursor.execute("SELECT SUM(floor) FROM scan_logs")
    result = cursor.fetchone()
    total_stair_levels = result[0] if result and result[0] else 0

    co2_saved = calculate_co2_saved(total_stair_levels)
    forest_offset = calculate_forest_offset(co2_saved)
    waste_recycled = calculate_waste_recycled(co2_saved)

    message = get_translated_text(user_id, "all_users_impact_progress").format(
        co2_saved=co2_saved,
        forest_offset=forest_offset,
        waste_recycled=waste_recycled
    )
    send_line_message(user_id, message)


# when user first adds the bot
@handler.add(FollowEvent) 
def handle_follow(event):
    """ When a user adds the bot, send a personalized welcome message and ask for language preference and location permission"""
    user_id = event.source.user_id

    try:
        # Fetch user's display name from LINE profile
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name  # Extract the user's name

        # Send a personalized welcome message
        welcome_message = f"Hi {user_name}! 🌟 Welcome to Staircase Fairy! 🚶‍♂️✨\nCheck out the menu below for more info and start your climbing adventure! 🚀🏆\n\n"
        welcome_message += f"哈囉 {user_name}！歡迎來到樓梯精靈！請按下方選單查看更多。🏃‍♂️🏃‍♀️"

        line_bot_api.push_message(user_id, TextSendMessage(text=welcome_message))

        # language settings: choose english or chinese
        send_language_menu(user_id)

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
        response_message = get_translated_text(user_id, "set_language")
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

    # Handle others menu
    elif postback_data == "read_about_us":
        send_line_message(user_id, "about_us_msg")
    elif postback_data == "ask_location_consent":
        ask_location_permission(user_id)
    elif postback_data == "report_issue_feedback":
        issue_feedback(user_id)

    # Handle impact menu
    elif postback_data == "personal_impacts":
        send_personal_impact(user_id)
    elif postback_data == "all_users_impacts":
        send_all_users_impact(user_id)

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

        # How to play
        elif user_message_stripped_lower.startswith("how to play"):
            send_line_message(user_id, "how_to_play")

        # Language settings
        elif user_message_stripped_lower.startswith("language"):
            send_language_menu(user_id)
        
        # Points: user progress, leaderboard
        elif user_message_stripped_lower.startswith("points"):
            send_points_menu(user_id)

        # Rewards
        # elif user_message_stripped_lower.startswith("rewards"):
        #     send_rewards(user_id)

        # Impacts: CO2 emissions
        elif user_message_stripped_lower.startswith("impacts"):
            send_impacts_menu(user_id)

        elif user_message_stripped_lower.startswith("others"):
            send_others_menu(user_id)

        # Location consent
        elif user_message_stripped_lower.startswith("location consent"):
            ask_location_permission(user_id)
        
        # About us
        elif user_message_stripped_lower.startswith("about us"):
            send_line_message(user_id, "about_us_msg")

        # Feedback/Issue reports
        elif user_message_stripped_lower.startswith("feedback") or user_message_stripped_lower.startswith("issue") or user_message_stripped_lower.startswith("report"):
            issue_feedback(user_id)

        elif user_message.startswith("I would like to provide feedback or report an issue:") or user_message.startswith("我想提供回饋或回報問題："):
            report_text = user_message.split("\n", 1)[1]  # Extract the actual report content
            save_report(user_id, report_text)  # Save it in the database
            send_line_message(user_id, get_translated_text(user_id, "issue_received"))
            return

        # Easter eggs
        elif user_message_stripped_lower.startswith("mexico"):
            send_line_message(user_id, "🇲🇽🌮🌯")

        # Default response
        elif not user_message_stripped_lower.startswith("rewards"):
            send_line_message(user_id, "default_response")

    except Exception as e:
        app.logger.error(f"Error handling message: {e}")

def handle_qr_scan(user_id, user_message):
    """Handles QR code scan messages."""
    try:
        _, _, floor, location = user_message.split("_")
        # logging.info(f"User Location - floor: {floor}, {location}")

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
        # logging.info(f"User Location Coordinates: {user_lat}, {user_lng}")

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

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    """Handles sticker messages by replying with a random response."""
    user_id = event.source.user_id

    # Select a random response
    random_reply = random.choice(STICKER_RESPONSES)

    # Send the response
    send_line_message(user_id, random_reply)

@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming messages from LINE users."""
    signature = request.headers.get('X-Line-Signature')  # 🔹 Fetch LINE Signature
    body = request.get_data(as_text=True) or "{}"  # 🔹 Ensure body isn't None

    if not signature:  # 🔹 Handle missing header
        app.logger.error("🚨 Missing X-Line-Signature header.")
        return jsonify({"error": "Missing X-Line-Signature header"}), 400

    app.logger.info(f"📌 Request body: {body}")

    try:
        handler.handle(body, signature)  # ✅ Process the request
    except InvalidSignatureError:
        app.logger.error("🚨 Invalid signature. Check your LINE channel secret.")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        app.logger.error(f"🚨 Error: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok"}), 200  # ✅ Always return 200 OK

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
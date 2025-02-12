import os
import requests
import json
from linebot import LineBotApi

# Replace with your LINE credentials
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
HEADERS = {"Authorization": f"Bearer {LINE_ACCESS_TOKEN}", "Content-Type": "application/json"}

def create_rich_menu():
    """Creates a rich menu for the LINE bot."""
    
    rich_menu_data = {
        "size": {"width": 2500, "height": 843},  # Standard rich menu size
        "selected": True,  # Default menu displayed when user opens chat
        "name": "Main Menu",
        "chatBarText": "📋 Open Menu",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 1250, "height": 843},
                "action": {"type": "postback", "data": "check_progress"}
            },
            {
                "bounds": {"x": 1250, "y": 0, "width": 1250, "height": 843},
                "action": {"type": "postback", "data": "view_leaderboard"}
            }
        ]
    }

    response = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        headers=HEADERS,
        data=json.dumps(rich_menu_data)
    )

    if response.status_code == 200:
        rich_menu_id = response.json()["richMenuId"]
        print(f"✅ Rich Menu Created! ID: {rich_menu_id}")
        return rich_menu_id
    else:
        print(f"🚨 Error: {response.text}")
        return None

def upload_rich_menu_image(rich_menu_id, image_path):
    """Uploads an image to the created rich menu."""
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "image/jpeg"  # Change to "image/png" if using PNG
    }

    with open(image_path, "rb") as image:
        response = requests.post(
            f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers=headers,
            data=image
        )

    if response.status_code == 200:
        print("✅ Image uploaded successfully!")
    else:
        print(f"🚨 Error uploading image: {response.text}")

def link_rich_menu_to_users(rich_menu_id):
    """Links the rich menu to all users."""
    response = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
        headers=HEADERS
    )

    if response.status_code == 200:
        print("✅ Rich menu linked to all users!")
    else:
        print(f"🚨 Error linking rich menu: {response.text}")

if __name__ == "__main__":
    rich_menu_id = create_rich_menu()
    if rich_menu_id:
        upload_rich_menu_image(rich_menu_id, "rich_menu.jpg")
        link_rich_menu_to_users(rich_menu_id)
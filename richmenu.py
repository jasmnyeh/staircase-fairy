import os
import json
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, PostbackAction, URITemplateAction

LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)

def create_rich_menu():
    """Create a rich menu with six sections"""
    rich_menu = RichMenu(
        size=RichMenuSize(width=1200, height=810),
        selected=True,
        name="Main Menu",
        chat_bar_text="選單 Menu",
        areas=[
            # Top row
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=400, height=405),
                action=PostbackAction(label="How to Play", data="how_to_play")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=400, y=0, width=400, height=405),
                action=PostbackAction(label="Points & Ranking", data="points_ranking")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=800, y=0, width=400, height=405),
                action=PostbackAction(label="Impacts", data="impacts")
            ),
            # Bottom row
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=405, width=400, height=405),
                action=PostbackAction(label="Rewards", data="rewards")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=400, y=405, width=400, height=405),
                action=PostbackAction(label="Language", data="language")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=800, y=405, width=400, height=405),
                action=PostbackAction(label="Others", data="others_menu")
            )
        ]
    )

    # Create rich menu
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)
    print(f"Rich menu created! ID: {rich_menu_id}")

    # Upload image for the rich menu (Modify path to your image)
    with open("menu.jpg", "rb") as image_file:
        line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", image_file)
    print("Rich menu image uploaded!")

    # Set as default rich menu
    line_bot_api.set_default_rich_menu(rich_menu_id)
    print("Rich menu set as default!")

if __name__ == "__main__":
    create_rich_menu()

import qrcode

# Replace with your bot's LINE ID
BOT_ID = "@925keedn"

# List of QR codes with staircase name and floor
qr_locations = [
    {"floor": "1F", "location": "機械系館1"},
    {"floor": "2F", "location": "機械系館1"},
    {"floor": "3F", "location": "機械系館1"},
    {"floor": "4F", "location": "機械系館1"},
    {"floor": "5F", "location": "機械系館1"},
]

for qr in qr_locations:
    # Format the message that will be sent to the bot
    message = f"STAIRCASE_QR_{qr['floor']}_{qr['location']}"

    # Create a LINE URL scheme that pre-fills the message
    qr_code_url = f"line://oaMessage/{BOT_ID}/?{message}"

    # Generate and save the QR code
    file_name = f"qr_{qr['floor']}_{qr['location']}.png"
    qrcode.make(qr_code_url).save(file_name)

    print(f"✅ QR Code saved: {file_name} → {qr_code_url}")

import qrcode

# Replace with your bot's LINE ID
BOT_ID = "@925keedn"

# List of QR codes with staircase name, floor, latitude, longitude
qr_locations = [
    {"floor": "1F", "location": "機械系館1", "lat": 25.0190037, "lng": 121.5395211},
]

for qr in qr_locations:
    message = f"STAIRCASE_QR_{qr['floor']}_{qr['location']}_{qr['lat']}_{qr['lng']}"
    qr_code_url = f"line://oaMessage/{BOT_ID}/?{message}"
    
    qrcode.make(qr_code_url).save(f"qr_{qr['floor']}_{qr['location']}.png")
    print(f"✅ QR Code saved: qr_{qr['floor']}_{qr['location']}.png → {qr_code_url}")

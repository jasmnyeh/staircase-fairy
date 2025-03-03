import qrcode
import os

BOT_ID = "@925keedn"

# Function to generate QR locations dynamically
def generate_qr_locations(location_name, floors):
    return [{"floor": f"{i}-{i+1}F", "location": location_name} for i in range(1, floors + 1)]

# List of locations with floors
target_locations = [
    ("機械系館1", 5),
    ("機械系館2", 5)
]

# Root directory to store QR codes
root_folder = "qrcodes"

# Generate QR codes
qr_locations = []
for location, floors in target_locations:
    qr_locations.extend(generate_qr_locations(location, floors))

for qr in qr_locations:
    # Format the message that will be sent to the bot
    message = f"STAIRCASE_QR_{qr['floor']}_{qr['location']}"

    # Create a LINE URL scheme that pre-fills the message
    qr_code_url = f"line://oaMessage/{BOT_ID}/?{message}"

    # Define folder for each location
    location_folder = os.path.join(root_folder, qr["location"])
    os.makedirs(location_folder, exist_ok=True)

    # Generate and save the QR code in the correct folder
    file_name = os.path.join(location_folder, f"qr_{qr['floor']}.png")
    qrcode.make(qr_code_url).save(file_name)

    print(f"✅ QR Code saved: {file_name} → {qr_code_url}")
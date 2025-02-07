user_message = "STAIRCASE_QR_1F_機械系館1_25.031757_121.544729"
_, _, floor, location, qr_lat, qr_lng = user_message.split("_")

# Convert GPS values to float
qr_lat, qr_lng = float(qr_lat), float(qr_lng)

print(f"Floor: {floor}")         # Output: 1F
print(f"Location: {location}")   # Output: 機械系館_1
print(f"Latitude: {qr_lat}")     # Output: 25.031757
print(f"Longitude: {qr_lng}")    # Output: 121.544729
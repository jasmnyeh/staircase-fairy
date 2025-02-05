import qrcode
import json
import os

def generate_qr_code(location_name, floor, latitude, longitude, output_dir='qrcodes'):
    # Create data dictionary
    data = {
        "name": location_name,
        "floor": floor,
        "latitude": latitude,
        "longitude": longitude
    }
    
    # Convert to JSON string
    json_data = json.dumps(data)
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Add data
    qr.add_data(json_data)
    qr.make(fit=True)
    
    # Create image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save image
    filename = f"{output_dir}/{location_name.replace(' ', '_')}_{floor}.png"
    qr_image.save(filename)
    return filename

if __name__ == "__main__":
    # Example usage
    locations = [
        {
            "name": "Main Staircase",
            "floor": "1",
            "latitude": 25.031757,
            "longitude": 121.544729
        },
        {
            "name": "Emergency Exit",
            "floor": "2",
            "latitude": 25.031757,
            "longitude": 121.544729
        }
    ]
    
    for location in locations:
        filename = generate_qr_code(
            location["name"],
            location["floor"],
            location["latitude"],
            location["longitude"]
        )
        print(f"Generated QR code: {filename}")
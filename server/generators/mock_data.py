import csv
import io
import random
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd

fake = Faker(['en_IN'])

AHMEDABAD_WARDS = [
    "Navrangpura", "Vastrapur", "Satellite", "Naranpura", "Girdhar Nagar", 
    "Paldi", "Bodakdev", "Jodhpur", "Bopal", "Thaltej", "Ranip", 
    "Chandkheda", "Sabarmati", "Nikol", "Maninagar", "Kalupur", 
    "Jamalpur", "Shahpur", "Dariapur", "Astodia"
]

COMPLAINT_DESCRIPTIONS = [
    # Sewer Blockage / Drainage
    {"desc": "Sewer leakage/blockage near the main road. Water is overflowing.", "cat": "Sewer & Drainage", "lang": "English"},
    {"desc": "ગટર ઉભરાય છે અને ગંદુ પાણી રસ્તા પર આવે છે.", "cat": "Sewer & Drainage", "lang": "Gujarati"},
    {"desc": "drainage line choke up hogayi hai, smell bohot gandi aa rahi hai.", "cat": "Sewer & Drainage", "lang": "Hinglish"},
    {"desc": "Blockage in drainage pipe behind standard chartered bank.", "cat": "Sewer & Drainage", "lang": "English"},
    {"desc": "Water logging due to blocked sewer outlet in our society lane.", "cat": "Sewer & Drainage", "lang": "English"},
    {"desc": "ગટર લાઇન સાફ કરવાની જરૂર છે, ગંદકી વધી ગઈ છે.", "cat": "Sewer & Drainage", "lang": "Gujarati"},
    
    # Garbage & Solid Waste
    {"desc": "Huge garbage pile at the corner of the street. Nobody is cleaning it.", "cat": "Garbage & Waste", "lang": "English"},
    {"desc": "કચરાપેટી ભરાઈ ગઈ છે, બહાર બધો કચરો પડ્યો છે.", "cat": "Garbage & Waste", "lang": "Gujarati"},
    {"desc": "yahan par kachra bohot jama ho gaya hai, clean karvao please.", "cat": "Garbage & Waste", "lang": "Hinglish"},
    {"desc": "Garbage truck has not come since 3 days.", "cat": "Garbage & Waste", "lang": "English"},
    
    # Streetlights
    {"desc": "Street light is not working. The entire alley is dark and unsafe.", "cat": "Streetlights", "lang": "English"},
    {"desc": "સ્ટ્રીટ લાઈટ બંધ છે, રાત્રે અંધારું રહે છે.", "cat": "Streetlights", "lang": "Gujarati"},
    {"desc": "street light kharab hai, switch board me se smoke nikal raha hai.", "cat": "Streetlights", "lang": "Hinglish"},
    {"desc": "Broken streetlight pole outside house number 45.", "cat": "Streetlights", "lang": "English"},
    
    # Potholes & Roads
    {"desc": "Huge pothole in the middle of the road causing traffic block.", "cat": "Roads & Potholes", "lang": "English"},
    {"desc": "રસ્તા પર મોટા ખાડા પડી ગયા છે, બાઇક ચલાવવામાં તકલીફ થાય છે.", "cat": "Roads & Potholes", "lang": "Gujarati"},
    {"desc": "road damage ho gaya hai pipe fitting work ke baad, repairing baki hai.", "cat": "Roads & Potholes", "lang": "Hinglish"},
    {"desc": "Main road asphalt is completely ruined after recent rain.", "cat": "Roads & Potholes", "lang": "English"},
    
    # Water Supply
    {"desc": "No water supply in our area since yesterday morning.", "cat": "Water Supply", "lang": "English"},
    {"desc": "પીવાના પાણીમાં ગંદુ ગટરનું પાણી મિક્સ થઈને આવે છે.", "cat": "Water Supply", "lang": "Gujarati"},
    {"desc": "pani ka pressure bohot low hai, building ke upper floor pe nahi chadta.", "cat": "Water Supply", "lang": "Hinglish"},
    {"desc": "Water pipeline leakage near the garden wall.", "cat": "Water Supply", "lang": "English"}
]

MISSPELLED_WARDS = {
    "Navrangpura": ["Navrngpura", "Nvarangpura", "Navrang pura", "Navrnagpura"],
    "Vastrapur": ["Vastrapur", "Vastrapur area", "Vastrapur lake side", "Vstrapur"],
    "Satellite": ["Satelite", "Satellight", "Satelite Road"],
    "Naranpura": ["Naranpra", "Narnapura", "Naranpura cross"],
    "Bodakdev": ["Bodakdev", "Bdkdev", "Bodak dev"],
    "Thaltej": ["Thaltej", "Thaltej char rasta", "Thalteej"],
    "Chandkheda": ["Chandkheda", "Chandkheda village", "Chandkeda"]
}

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y %I:%M %p",
    "%b %d, %Y",
    "%Y/%m/%d"
]

PHONE_FORMATS = [
    "+91 {}{}",
    "0{}{}",
    "{}{}",
    "+91-{}-{}"
]

def generate_dirty_row() -> dict:
    # Choose complaint template
    tmpl = random.choice(COMPLAINT_DESCRIPTIONS)
    desc = tmpl["desc"]
    
    # Choose ward name
    ward = random.choice(AHMEDABAD_WARDS)
    dirty_ward = ward
    if ward in MISSPELLED_WARDS and random.random() < 0.6:
        dirty_ward = random.choice(MISSPELLED_WARDS[ward])
    elif random.random() < 0.2:
        # completely missing ward or vague ward name
        dirty_ward = random.choice(["", "Ahmedabad City", "Main Chowk", "Near Temple"])

    # Phone number formats
    p1 = str(random.randint(6, 9))
    p2 = "".join([str(random.randint(0, 9)) for _ in range(9)])
    phone_raw = p1 + p2
    phone_fmt = random.choice(PHONE_FORMATS)
    if "-" in phone_fmt:
        dirty_phone = phone_fmt.format(phone_raw[:5], phone_raw[5:])
    elif " " in phone_fmt:
        dirty_phone = f"+91 {phone_raw[:5]} {phone_raw[5:]}"
    elif phone_fmt == "{}{}":
        dirty_phone = phone_raw
    else:
        dirty_phone = phone_fmt.format(phone_raw[:5], phone_raw[5:])
        
    if random.random() < 0.15:
        dirty_phone = "" # Missing phone
    elif random.random() < 0.08:
        dirty_phone = "12345" # invalid length

    # Date formatting
    date_val = datetime.now() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
    date_fmt = random.choice(DATE_FORMATS)
    dirty_date = date_val.strftime(date_fmt)
    
    if random.random() < 0.1:
        dirty_date = "N/A" # Invalid date
        
    # Postal code
    # Ahmedabad postal codes are 3800xx
    postal_code = f"3800{random.randint(10, 99):02d}"
    dirty_postal = postal_code
    if random.random() < 0.2:
        dirty_postal = random.choice(["", "380 001", "38000", "000000", "Ahmedabad"])
        
    # Coordinates
    # Ahmedabad lat: 23.0225, lng: 72.5714
    lat = 23.0225 + random.uniform(-0.08, 0.08)
    lng = 72.5714 + random.uniform(-0.08, 0.08)
    
    dirty_lat = str(lat)
    dirty_lng = str(lng)
    
    # Missing coordinates (Very common in unstructured CSVs)
    if random.random() < 0.4:
        dirty_lat = ""
        dirty_lng = ""
    elif random.random() < 0.1:
        dirty_lat = "0.0"
        dirty_lng = "0.0"

    # Add noise / unstructured attributes
    return {
        "Complaint ID": f"311-{random.randint(100000, 999999)}",
        "Date": dirty_date,
        "Ward/Area": dirty_ward,
        "Complaint Details": desc,
        "Reporter Phone": dirty_phone,
        "Pincode": dirty_postal,
        "Latitude": dirty_lat,
        "Longitude": dirty_lng,
        "Reporter Name": fake.name() if random.random() > 0.15 else "",
        "Extra Notes": fake.sentence() if random.random() < 0.3 else ""
    }

def generate_dirty_csv_data(num_rows: int = 50) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Complaint ID", "Date", "Ward/Area", "Complaint Details", 
        "Reporter Phone", "Pincode", "Latitude", "Longitude", 
        "Reporter Name", "Extra Notes"
    ])
    writer.writeheader()
    
    rows = []
    for _ in range(num_rows):
        rows.append(generate_dirty_row())
        
    # Let's inject some duplicate records
    # Duplicate records will have the exact same/slightly different Complaint Details and same Ward/Area
    num_dups = int(num_rows * 0.15)
    for _ in range(num_dups):
        if len(rows) > 0:
            base_row = random.choice(rows).copy()
            # Modify Complaint ID slightly or keep same
            if random.random() < 0.5:
                base_row["Complaint ID"] = f"311-{random.randint(100000, 999999)}"
            # Alter date slightly
            base_row["Date"] = (datetime.now() - timedelta(minutes=random.randint(5, 120))).strftime(random.choice(DATE_FORMATS))
            # Insert into random position
            rows.insert(random.randint(0, len(rows)), base_row)

    for row in rows:
        writer.writerow(row)
        
    return output.getvalue()

if __name__ == "__main__":
    # Generate 500 records
    print("Generating 500 mock 311 records...")
    csv_content = generate_dirty_csv_data(500)
    
    # Save to main project directory
    # '..' because this script is in server/generators/
    import os
    file_path = os.path.join(os.getcwd(), "urbanfix_mock_311.csv")
    
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_content)
        
    print(f"Successfully generated 500 records and saved to: {file_path}")

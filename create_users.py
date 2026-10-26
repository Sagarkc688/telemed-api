# create_users.py
# Adds the starting user accounts to the users collection - one for each role.
# Passwords are hashed with bcrypt so the real password is never stored.

from pymongo import MongoClient
import bcrypt

client = MongoClient("mongodb://localhost:27017")
db = client.TelemedDB
users = db.users

# usernames must be unique - MongoDB will refuse a duplicate
users.create_index("username", unique=True)

user_list = [
    {"username": "admin", "name": "Admin User", "email": "admin@telemed.com",
     "password": "admin123", "role": "admin"},
    # linked to doctor D101 (Dr Aoife Wilson, Dermatology) in the doctors collection
    {"username": "drwilson", "name": "Dr Aoife Wilson", "email": "aoife.wilson@telemed.com",
     "password": "doctor123", "role": "doctor", "doctor_id": "D101"},
    # same email as the patient in consultation C1000, so we can link her to her consultations
    {"username": "sarah", "name": "Sarah Smith", "email": "sarah.smith@example.com",
     "password": "patient123", "role": "patient"},
]

for user in user_list:
    # skip anyone who already exists, so the script is safe to run twice
    if users.find_one({"username": user["username"]}) is not None:
        print("Already exists:", user["username"])
        continue

    # hash the password - .encode() turns text into bytes, which bcrypt needs
    hashed = bcrypt.hashpw(user["password"].encode("utf-8"), bcrypt.gensalt())
    user["password"] = hashed.decode("utf-8")     # store as text so it's readable in Compass
    users.insert_one(user)
    print("Created:", user["username"], "(" + user["role"] + ")")
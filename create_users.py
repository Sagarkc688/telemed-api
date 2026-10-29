from pymongo import MongoClient
import bcrypt

# adds one user for each role, passwords are hashed with bcrypt

client = MongoClient("mongodb://localhost:27017")
db = client.TelemedDB
users = db.users

# no duplicate usernames
users.create_index("username", unique=True)

user_list = [
    {"username": "admin", "name": "Admin User", "email": "admin@telemed.com",
     "password": "admin123", "role": "admin"},
    # linked to doctor D101 in the doctors collection
    {"username": "drwilson", "name": "Dr Aoife Wilson", "email": "aoife.wilson@telemed.com",
     "password": "doctor123", "role": "doctor", "doctor_id": "D101"},
    # same email as the patient in C1000
    {"username": "sarah", "name": "Sarah Smith", "email": "sarah.smith@example.com",
     "password": "patient123", "role": "patient"},
]

for user in user_list:
    # skip users that already exist so it can be run again
    if users.find_one({"username": user["username"]}) is not None:
        print("Already exists:", user["username"])
        continue

    hashed = bcrypt.hashpw(user["password"].encode("utf-8"), bcrypt.gensalt())
    user["password"] = hashed.decode("utf-8")    # saved as text
    users.insert_one(user)
    print("Created:", user["username"], "(" + user["role"] + ")")
from pymongo import MongoClient

# shared by every file - the database connection, secret key and fixed values

# connect to my telemedicine database (capital T - must match Compass exactly)
client = MongoClient("mongodb://localhost:27017")
db = client.TelemedDB

secret_key = 'telemed-api-secret-key-change-me-2026'    # signs the tokens - in a real app this would be kept secret

# fixed values used for checking input - tuples because they never change
SPECIALTIES = ("General Practice", "Dermatology", "Cardiology", "Paediatrics", "Mental Health", "Respiratory")

# symptoms that need emergency help straight away (lower case so the check ignores capitals)
EMERGENCY_SYMPTOMS = ("chest pain", "difficulty breathing", "severe bleeding", "loss of consciousness",
                      "stroke symptoms", "severe allergic reaction", "suicidal thoughts")

# city coordinates [longitude, latitude] - same as in mygenerator.py
CITIES = {
    "Belfast": [-5.9301, 54.5973],
    "Derry": [-7.3086, 54.9966],
    "Newry": [-6.3374, 54.1751],
    "Armagh": [-6.6547, 54.3503],
    "Lisburn": [-6.0353, 54.5162],
    "Coleraine": [-6.6683, 55.1325],
    "Enniskillen": [-7.6390, 54.3438],
    "Ballymena": [-6.2758, 54.8643]
}
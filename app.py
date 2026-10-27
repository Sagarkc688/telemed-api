from flask import Flask, make_response, jsonify, request, g
from pymongo import MongoClient
from bson import ObjectId

from functools import wraps
import datetime
import jwt
import bcrypt

app = Flask(__name__)

# connect to my telemedicine database (capital T - must match Compass exactly)
client = MongoClient("mongodb://localhost:27017")
db = client.TelemedDB
consultations = db.consultations
doctors = db.doctors
users = db.users

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


app.config['SECRET_KEY'] = 'telemed-api-secret-key-change-me-2026'    # signs the tokens - in a real app this would be kept secret


# decorator - only lets the request through if it has a valid login token
# same idea as jwt_required in class, but the token is sent in a header instead of the URL
def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return make_response(jsonify({"message": "Token is missing"}), 401)

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return make_response(jsonify({"message": "Token has expired - please log in again"}), 401)
        except jwt.InvalidTokenError:
            return make_response(jsonify({"message": "Token is invalid"}), 401)

        # remember who is logged in for this request, so routes and role checks can use it
        g.user = data
        return func(*args, **kwargs)
    return jwt_required_wrapper


# decorator factory - only lets in users whose role is in the list
# *roles collects any number of roles into a tuple, e.g. role_required("doctor", "admin") -> ("doctor", "admin")
# must be used AFTER @jwt_required, which works out who is logged in
def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def role_required_wrapper(*args, **kwargs):
            if g.user["role"] not in roles:
                return make_response(jsonify({"message": "You do not have permission to do this"}), 403)
            return func(*args, **kwargs)
        return role_required_wrapper
    return decorator


# decorator - checks the id in the URL is a valid MongoDB ObjectId
# so the same check isn't repeated in every route
def valid_id_required(func):
    @wraps(func)
    def valid_id_wrapper(*args, **kwargs):
        # print("args:", args, "kwargs:", kwargs)   # test: args is a tuple, kwargs is a dictionary
        # first version - only checked one id
        # if not ObjectId.is_valid(kwargs['id']):
        #     return make_response(jsonify({"error": "Invalid ID"}), 400)

        # Flask passes every id in the URL as a keyword argument, e.g. {'id': '6ad6...', 'p_id': '6ae3...'}
        # so loop through all of them - works for routes with one id or two
        for value in kwargs.values():
            if not ObjectId.is_valid(value):
                return make_response(jsonify({"error": "Invalid ID"}), 400)
        return func(*args, **kwargs)
    return valid_id_wrapper


# checks if the logged-in user is allowed to see this consultation
# admin - any consultation, doctor - only their own patients, patient - only their own
def can_access(consultation):
    user = g.user
    if user["role"] == "admin":
        return True
    if user["role"] == "doctor":
        return consultation["doctor"]["doctor_id"] == user.get("doctor_id")
    if user["role"] == "patient":
        return consultation.get("patient", {}).get("contact", {}).get("email") == user.get("email")
    return False


# finds a consultation and checks the user is allowed to use it
# returns a tuple: (consultation, None) if ok, or (None, error response) if not
def find_consultation_for_user(id):
    consultation = consultations.find_one({"_id": ObjectId(id)})
    if consultation is None:
        return None, make_response(jsonify({"error": "Consultation not found"}), 404)
    if not can_access(consultation):
        return None, make_response(jsonify({"message": "You do not have permission to do this"}), 403)
    return consultation, None


# LOGIN - checks username and password (sent with Basic Auth) and returns a token
@app.route("/api/v1.0/login", methods=["GET"])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({"message": "Username and password required"}), 401,
                             {'WWW-Authenticate': 'Basic realm="Login required"'})

    user = users.find_one({"username": auth.username})

    # same message whether the username or the password is wrong - doesn't tell an attacker which one
    if user is None or not bcrypt.checkpw(auth.password.encode("utf-8"), user["password"].encode("utf-8")):
        return make_response(jsonify({"message": "Wrong username or password"}), 401)

    token = jwt.encode({
        "user": user["username"],
        "role": user["role"],                       # used later to check what this user is allowed to do
        "email": user["email"],                     # used to find a patient's own consultations
        "doctor_id": user.get("doctor_id"),         # only doctors have this - None for everyone else
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return make_response(jsonify({"token": token}), 200)


@app.route("/", methods=["GET"])
def index():
    return make_response("<h1>Telemedicine API</h1>", 200)


# GET all consultations - with paging and optional filters
# e.g. /api/v1.0/consultations?status=completed&specialty=Cardiology&urgency=high
#      /api/v1.0/consultations?symptom=Fever&date_from=2026-03-01&date_to=2026-03-31
@app.route("/api/v1.0/consultations", methods=["GET"])
@jwt_required
def show_all_consultations():
    page_num, page_size = 1, 5

    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))

    page_start = page_size * (page_num - 1)

    # build the search one filter at a time - only filters that were sent are added
    query = {}

    if request.args.get('status'):
        status = request.args.get('status').strip()
        if status not in ("pending", "booked", "completed", "cancelled"):
            return make_response(jsonify({"error": "Invalid status"}), 400)
        query['appointment.status'] = status

    if request.args.get('urgency'):
        urgency = request.args.get('urgency').strip()
        if urgency not in ("low", "medium", "high"):
            return make_response(jsonify({"error": "urgency must be low, medium or high"}), 400)
        query['urgency_level'] = urgency

    if request.args.get('specialty'):
        query['doctor.specialty'] = request.args.get('specialty').strip()

    if request.args.get('symptom'):
        # searches inside the symptoms array
        query['symptoms.name'] = request.args.get('symptom').strip()

    # date range - dates are stored as "YYYY-MM-DD" text, which sorts in date order
    date_range = {}
    for arg, operator in (('date_from', '$gte'), ('date_to', '$lte')):
        if request.args.get(arg):
            value = request.args.get(arg).strip()
            try:
                datetime.datetime.strptime(value, "%Y-%m-%d")    # check it's a real date
            except ValueError:
                return make_response(jsonify({"error": arg + " must be a date like 2026-03-31"}), 400)
            date_range[operator] = value
    if date_range:
        query['appointment.date'] = date_range

    # doctors only see their own patients, patients only see their own consultations, admin sees all
    if g.user["role"] == "doctor":
        query['doctor.doctor_id'] = g.user["doctor_id"]
    elif g.user["role"] == "patient":
        query['patient.contact.email'] = g.user["email"]

    data_to_return = []
    for consultation in consultations.find(query).skip(page_start).limit(page_size):
        consultation['_id'] = str(consultation['_id'])
        # each prescription has its own _id (like the reviews in class) - convert to text for JSON
        for prescription in consultation.get('prescriptions', []):
            if '_id' in prescription:
                prescription['_id'] = str(prescription['_id'])
        data_to_return.append(consultation)

    return make_response(jsonify(data_to_return), 200)


# GET one consultation by its _id
@app.route("/api/v1.0/consultations/<string:id>", methods=["GET"])
@jwt_required
@valid_id_required
def show_one_consultation(id):
    # first version - now done by the @valid_id_required decorator
    # if not ObjectId.is_valid(id):
    #     return make_response(jsonify({"error": "Invalid consultation ID"}), 400)

    # second version - also checks this user is allowed to see it
    # consultation = consultations.find_one({'_id': ObjectId(id)})
    # if consultation is None:
    #     return make_response(jsonify({"error": "Consultation not found"}), 404)
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    consultation['_id'] = str(consultation['_id'])
    for prescription in consultation.get('prescriptions', []):
        if '_id' in prescription:
            prescription['_id'] = str(prescription['_id'])
    return make_response(jsonify(consultation), 200)


# POST - book a new consultation
@app.route("/api/v1.0/consultations", methods=["POST"])
@jwt_required
@role_required("patient", "admin")
def add_consultation():
    # fields that must be sent - a tuple because this list never changes
    required = ("patient_name", "patient_email", "doctor_id", "date", "time_slot", "type")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    # appointment type can only be video or phone (.strip() removes hidden spaces/tabs)
    if request.form["type"].strip() not in ("video", "phone"):
        return make_response(jsonify({"error": "type must be video or phone"}), 400)

    # the doctor must exist in the doctors collection
    doctor = doctors.find_one({"doctor_id": request.form["doctor_id"].strip()})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    new_consultation = {
        "patient": {
            "name": request.form["patient_name"].strip(),
            "contact": {"email": request.form["patient_email"].strip()}
        },
        "doctor": {
            "doctor_id": doctor["doctor_id"],
            "name": doctor["name"],
            "specialty": doctor["specialty"]
        },
        "appointment": {
            "date": request.form["date"].strip(),
            "time_slot": request.form["time_slot"].strip(),
            "type": request.form["type"].strip(),
            "status": "booked"
        },
        "symptoms": [],
        "consultation_notes": None,
        "prescriptions": [],
        "feedback": None
    }

    result = consultations.insert_one(new_consultation)
    new_link = "http://localhost:5001/api/v1.0/consultations/" + str(result.inserted_id)
    return make_response(jsonify({"url": new_link}), 201)


# PUT - edit a consultation's appointment (only the fields that are sent)
@app.route("/api/v1.0/consultations/<string:id>", methods=["PUT"])
@jwt_required
@valid_id_required
def edit_consultation(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # first version - now done by the @valid_id_required decorator
    # if not ObjectId.is_valid(id):
    #     return make_response(jsonify({"error": "Invalid consultation ID"}), 400)

    # fields a user is allowed to change - a tuple because this never changes
    allowed = ("date", "time_slot", "type", "status")
    updates = {}
    for field in allowed:
        if request.form.get(field):
            # dot notation updates a field inside the nested appointment
            updates["appointment." + field] = request.form[field].strip()

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

    # check the values are allowed
    if "appointment.type" in updates and updates["appointment.type"] not in ("video", "phone"):
        return make_response(jsonify({"error": "type must be video or phone"}), 400)
    if "appointment.status" in updates and updates["appointment.status"] not in ("pending", "booked", "completed", "cancelled"):
        return make_response(jsonify({"error": "Invalid status"}), 400)

    result = consultations.update_one({"_id": ObjectId(id)}, {"$set": updates})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    edited_link = "http://localhost:5001/api/v1.0/consultations/" + id
    return make_response(jsonify({"url": edited_link}), 200)


# DELETE - remove a consultation
@app.route("/api/v1.0/consultations/<string:id>", methods=["DELETE"])
@jwt_required
@role_required("admin")
@valid_id_required
def delete_consultation(id):
    # first version - now done by the @valid_id_required decorator
    # if not ObjectId.is_valid(id):
    #     return make_response(jsonify({"error": "Invalid consultation ID"}), 400)

    result = consultations.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    return make_response(jsonify({"message": "Consultation deleted"}), 200)


# GET all prescriptions for one consultation
@app.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["GET"])
@jwt_required
@valid_id_required
def show_all_prescriptions(id):
    # first version - projection, only brought back the prescriptions field
    # consultation = consultations.find_one({"_id": ObjectId(id)}, {"prescriptions": 1, "_id": 0})
    # if consultation is None:
    #     return make_response(jsonify({"error": "Consultation not found"}), 404)
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    data_to_return = []
    for prescription in consultation.get("prescriptions", []):
        if "_id" in prescription:
            prescription["_id"] = str(prescription["_id"])
        data_to_return.append(prescription)

    return make_response(jsonify(data_to_return), 200)


# POST - add a new prescription to a consultation
@app.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["POST"])
@jwt_required
@role_required("doctor")
@valid_id_required
def add_prescription(id):
    # a doctor can only prescribe for their own patients
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # fields that must be sent - a tuple because this never changes
    required = ("medicine", "dosage", "frequency", "duration_days")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    # type check - duration must be a whole number
    try:
        duration = int(request.form["duration_days"])
    except ValueError:
        return make_response(jsonify({"error": "duration_days must be a whole number"}), 400)

    # range check - between 1 day and 1 year
    if duration < 1 or duration > 365:
        return make_response(jsonify({"error": "duration_days must be between 1 and 365"}), 400)

    new_prescription = {
        "_id": ObjectId(),          # its own id, like the reviews in class
        "medicine": request.form["medicine"].strip(),
        "dosage": request.form["dosage"].strip(),
        "frequency": request.form["frequency"].strip(),
        "duration_days": duration   # saved as a number, not text
    }

    # $push adds the new prescription to the end of the prescriptions array
    result = consultations.update_one({"_id": ObjectId(id)}, {"$push": {"prescriptions": new_prescription}})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    new_link = "http://localhost:5001/api/v1.0/consultations/" + id + "/prescriptions/" + str(new_prescription["_id"])
    return make_response(jsonify({"url": new_link}), 201)


# GET one prescription from a consultation
@app.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["GET"])
@jwt_required
@valid_id_required
def show_one_prescription(id, p_id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # "prescriptions.$" - only return the ONE prescription that matched, not the whole array
    consultation = consultations.find_one(
        {"_id": ObjectId(id), "prescriptions._id": ObjectId(p_id)},
        {"prescriptions.$": 1, "_id": 0}
    )
    if consultation is None:
        return make_response(jsonify({"error": "Prescription not found"}), 404)

    prescription = consultation["prescriptions"][0]
    prescription["_id"] = str(prescription["_id"])
    return make_response(jsonify(prescription), 200)


# PUT - edit one prescription (only the fields that are sent)
@app.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["PUT"])
@jwt_required
@role_required("doctor")
@valid_id_required
def edit_prescription(id, p_id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    allowed = ("medicine", "dosage", "frequency", "duration_days")
    updates = {}
    for field in allowed:
        if request.form.get(field):
            # $ means "the prescription that matched the query" - so only that one is changed
            updates["prescriptions.$." + field] = request.form[field].strip()

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

    # same type and range check as when adding
    if "prescriptions.$.duration_days" in updates:
        try:
            duration = int(updates["prescriptions.$.duration_days"])
        except ValueError:
            return make_response(jsonify({"error": "duration_days must be a whole number"}), 400)
        if duration < 1 or duration > 365:
            return make_response(jsonify({"error": "duration_days must be between 1 and 365"}), 400)
        updates["prescriptions.$.duration_days"] = duration

    result = consultations.update_one(
        {"_id": ObjectId(id), "prescriptions._id": ObjectId(p_id)},
        {"$set": updates}
    )
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Prescription not found"}), 404)

    edited_link = "http://localhost:5001/api/v1.0/consultations/" + id + "/prescriptions/" + p_id
    return make_response(jsonify({"url": edited_link}), 200)


# DELETE - remove one prescription from a consultation
@app.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["DELETE"])
@jwt_required
@role_required("doctor")
@valid_id_required
def delete_prescription(id, p_id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # $pull removes the item from the array that has this _id
    result = consultations.update_one(
        {"_id": ObjectId(id)},
        {"$pull": {"prescriptions": {"_id": ObjectId(p_id)}}}
    )
    if result.modified_count == 0:
        return make_response(jsonify({"error": "Prescription not found"}), 404)

    return make_response(jsonify({"message": "Prescription deleted"}), 200)


# GET all doctors - with optional filters and paging
# e.g. /api/v1.0/doctors?specialty=Dermatology&city=Belfast&accepting=true
@app.route("/api/v1.0/doctors", methods=["GET"])
def show_all_doctors():
    page_num, page_size = 1, 5
    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = page_size * (page_num - 1)

    # build the search one filter at a time - only filters that were sent are added
    query = {}
    if request.args.get('specialty'):
        query['specialty'] = request.args.get('specialty').strip()
    if request.args.get('city'):
        query['clinic.city'] = request.args.get('city').strip()     # nested field
    if request.args.get('accepting'):
        accepting = request.args.get('accepting').strip().lower()
        if accepting not in ("true", "false"):
            return make_response(jsonify({"error": "accepting must be true or false"}), 400)
        query['accepting_patients'] = (accepting == "true")         # text -> real True/False

    data_to_return = []
    for doctor in doctors.find(query).skip(page_start).limit(page_size):
        doctor['_id'] = str(doctor['_id'])
        data_to_return.append(doctor)

    return make_response(jsonify(data_to_return), 200)


# GET one doctor by its _id
@app.route("/api/v1.0/doctors/<string:id>", methods=["GET"])
@valid_id_required
def show_one_doctor(id):
    doctor = doctors.find_one({'_id': ObjectId(id)})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    doctor['_id'] = str(doctor['_id'])
    return make_response(jsonify(doctor), 200)


# GET doctors near a location - nearest first
# e.g. /api/v1.0/doctors/nearby?lat=54.597&lng=-5.930&distance=30&specialty=Dermatology
@app.route("/api/v1.0/doctors/nearby", methods=["GET"])
def show_nearby_doctors():
    # lat and lng must be sent
    if not request.args.get('lat') or not request.args.get('lng'):
        return make_response(jsonify({"error": "lat and lng are required"}), 400)

    # type check - they must be numbers
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        distance_km = float(request.args.get('distance', 30))    # 30 km if not sent
    except ValueError:
        return make_response(jsonify({"error": "lat, lng and distance must be numbers"}), 400)

    # range check - real map coordinates and a sensible distance
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return make_response(jsonify({"error": "lat must be -90 to 90 and lng -180 to 180"}), 400)
    if distance_km <= 0 or distance_km > 500:
        return make_response(jsonify({"error": "distance must be between 0 and 500 km"}), 400)

    # optional extra filter - e.g. only dermatologists near me
    query = {}
    if request.args.get('specialty'):
        query['specialty'] = request.args.get('specialty').strip()

    # $geoNear - finds doctors nearest to the point and works out how far away each one is
    pipeline = [
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": [lng, lat]},   # MongoDB wants longitude first
            "distanceField": "distance_km",       # new field added to each result
            "maxDistance": distance_km * 1000,    # MongoDB works in metres
            "distanceMultiplier": 0.001,          # turn the result from metres into km
            "spherical": True,                    # the earth is round
            "query": query
        }}
    ]

    data_to_return = []
    for doctor in doctors.aggregate(pipeline):
        doctor['_id'] = str(doctor['_id'])
        doctor['distance_km'] = round(doctor['distance_km'], 1)
        data_to_return.append(doctor)

    return make_response(jsonify(data_to_return), 200)


# ANALYTICS - most common symptoms (optionally for one specialty)
# e.g. /api/v1.0/analytics/top-symptoms?limit=5&specialty=Respiratory
@app.route("/api/v1.0/analytics/top-symptoms", methods=["GET"])
@jwt_required
@role_required("admin")
def top_symptoms():
    try:
        limit = int(request.args.get('limit', 5))      # top 5 if not sent
    except ValueError:
        return make_response(jsonify({"error": "limit must be a whole number"}), 400)
    if limit < 1 or limit > 50:
        return make_response(jsonify({"error": "limit must be between 1 and 50"}), 400)

    pipeline = []
    # optional - only look at one specialty
    if request.args.get('specialty'):
        pipeline.append({"$match": {"doctor.specialty": request.args.get('specialty').strip()}})

    pipeline += [
        {"$unwind": "$symptoms"},                        # one row per symptom
        {"$group": {
            "_id": "$symptoms.name",                     # group rows with the same symptom
            "count": {"$sum": 1},                        # how many times it appears
            "average_severity": {"$avg": "$symptoms.severity"}
        }},
        {"$sort": {"count": -1}},                        # most common first
        {"$limit": limit},
        {"$project": {"_id": 0, "symptom": "$_id", "count": 1,
                      "average_severity": {"$round": ["$average_severity", 1]}}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)


# ANALYTICS - average patient rating for each doctor, best first
@app.route("/api/v1.0/analytics/doctor-ratings", methods=["GET"])
@jwt_required
@role_required("admin")
def doctor_ratings():
    pipeline = [
        # only completed consultations have feedback
        {"$match": {"appointment.status": "completed", "feedback.rating": {"$exists": True}}},
        {"$group": {
            "_id": "$doctor.doctor_id",                  # group by id, not name - two doctors can share a name
            "name": {"$first": "$doctor.name"},
            "specialty": {"$first": "$doctor.specialty"},
            "average_rating": {"$avg": "$feedback.rating"},
            "total_consultations": {"$sum": 1}
        }},
        {"$sort": {"average_rating": -1, "total_consultations": -1}},
        {"$project": {"_id": 0, "doctor_id": "$_id", "name": 1, "specialty": 1, "total_consultations": 1,
                      "average_rating": {"$round": ["$average_rating", 2]}}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)


# ANALYTICS - consultations per month, with how many were completed and cancelled
@app.route("/api/v1.0/analytics/monthly", methods=["GET"])
@jwt_required
@role_required("admin")
def consultations_per_month():
    pipeline = [
        {"$group": {
            # dates are "2026-03-17" - the first 7 characters are the month "2026-03"
            "_id": {"$substrBytes": ["$appointment.date", 0, 7]},
            "total": {"$sum": 1},
            # $cond is an if/else - add 1 if the status matches, otherwise 0
            "completed": {"$sum": {"$cond": [{"$eq": ["$appointment.status", "completed"]}, 1, 0]}},
            "cancelled": {"$sum": {"$cond": [{"$eq": ["$appointment.status", "cancelled"]}, 1, 0]}}
        }},
        {"$sort": {"_id": 1}},                           # January first
        {"$project": {"_id": 0, "month": "$_id", "total": 1, "completed": 1, "cancelled": 1}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)

# POST - admin adds a new doctor
@app.route("/api/v1.0/doctors", methods=["POST"])
@jwt_required
@role_required("admin")
def add_doctor():
    # fields that must be sent - a tuple because this never changes
    required = ("name", "specialty", "city", "years_experience")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    specialty = request.form["specialty"].strip()
    if specialty not in SPECIALTIES:
        return make_response(jsonify({"error": "specialty must be one of: " + ", ".join(SPECIALTIES)}), 400)

    city = request.form["city"].strip()
    if city not in CITIES:
        return make_response(jsonify({"error": "city must be one of: " + ", ".join(CITIES)}), 400)

    # type and range check
    try:
        years = int(request.form["years_experience"])
    except ValueError:
        return make_response(jsonify({"error": "years_experience must be a whole number"}), 400)
    if years < 0 or years > 60:
        return make_response(jsonify({"error": "years_experience must be between 0 and 60"}), 400)

    # next doctor id - count how many doctors there are and add 100, e.g. 24 doctors -> D124
    # keep adding 1 if that id is already taken (e.g. after a doctor was deleted)
    number = 100 + doctors.count_documents({})
    while doctors.find_one({"doctor_id": "D" + str(number)}) is not None:
        number += 1

    new_doctor = {
        "doctor_id": "D" + str(number),
        "name": request.form["name"].strip(),
        "specialty": specialty,
        "years_experience": years,
        "available_days": [],
        "accepting_patients": True,
        "clinic": {
            "name": city + " Health Centre",
            "city": city,
            "location": {"type": "Point", "coordinates": CITIES[city]}
        }
    }

    result = doctors.insert_one(new_doctor)
    new_link = "http://localhost:5001/api/v1.0/doctors/" + str(result.inserted_id)
    return make_response(jsonify({"url": new_link, "doctor_id": new_doctor["doctor_id"]}), 201)

# PUT - admin edits a doctor (only the fields that are sent)
@app.route("/api/v1.0/doctors/<string:id>", methods=["PUT"])
@jwt_required
@role_required("admin")
@valid_id_required
def edit_doctor(id):
    updates = {}

    if request.form.get("name"):
        updates["name"] = request.form["name"].strip()

    if request.form.get("specialty"):
        specialty = request.form["specialty"].strip()
        if specialty not in SPECIALTIES:
            return make_response(jsonify({"error": "specialty must be one of: " + ", ".join(SPECIALTIES)}), 400)
        updates["specialty"] = specialty

    if request.form.get("city"):
        city = request.form["city"].strip()
        if city not in CITIES:
            return make_response(jsonify({"error": "city must be one of: " + ", ".join(CITIES)}), 400)
        # moving city changes the whole clinic, including its map position
        updates["clinic"] = {
            "name": city + " Health Centre",
            "city": city,
            "location": {"type": "Point", "coordinates": CITIES[city]}
        }

    if request.form.get("years_experience"):
        try:
            years = int(request.form["years_experience"])
        except ValueError:
            return make_response(jsonify({"error": "years_experience must be a whole number"}), 400)
        if years < 0 or years > 60:
            return make_response(jsonify({"error": "years_experience must be between 0 and 60"}), 400)
        updates["years_experience"] = years

    if request.form.get("accepting_patients"):
        accepting = request.form["accepting_patients"].strip().lower()
        if accepting not in ("true", "false"):
            return make_response(jsonify({"error": "accepting_patients must be true or false"}), 400)
        updates["accepting_patients"] = (accepting == "true")

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

    result = doctors.update_one({"_id": ObjectId(id)}, {"$set": updates})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    edited_link = "http://localhost:5001/api/v1.0/doctors/" + id
    return make_response(jsonify({"url": edited_link}), 200)

# DELETE - admin removes a doctor
@app.route("/api/v1.0/doctors/<string:id>", methods=["DELETE"])
@jwt_required
@role_required("admin")
@valid_id_required
def delete_doctor(id):
    doctor = doctors.find_one({"_id": ObjectId(id)})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    # don't delete a doctor who still has upcoming appointments - those patients would be left without a doctor
    upcoming = consultations.count_documents({
        "doctor.doctor_id": doctor["doctor_id"],
        "appointment.status": {"$in": ["booked", "pending"]}
    })
    if upcoming > 0:
        return make_response(jsonify({"error": "Doctor has " + str(upcoming) + " upcoming appointments - cancel or move them first"}), 409)

    doctors.delete_one({"_id": ObjectId(id)})
    return make_response(jsonify({"message": "Doctor deleted"}), 200)


# PUT - a doctor updates their OWN working days (and whether they are taking new patients)
# available_days is sent as a comma-separated list, e.g. "Mon,Wed,Fri"
@app.route("/api/v1.0/doctors/availability", methods=["PUT"])
@jwt_required
@role_required("doctor")
def update_availability():
    updates = {}

    if request.form.get("available_days"):
        valid_days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        # split "Mon, Wed,Fri" into ["Mon", "Wed", "Fri"] and tidy each one
        days = [day.strip().capitalize() for day in request.form["available_days"].split(",") if day.strip()]
        for day in days:
            if day not in valid_days:
                return make_response(jsonify({"error": day + " is not a valid day - use Mon, Tue, Wed, Thu, Fri, Sat, Sun"}), 400)
        # remove duplicates but keep the order, e.g. "Mon,Mon,Fri" -> ["Mon", "Fri"]
        updates["available_days"] = list(dict.fromkeys(days))

    if request.form.get("accepting_patients"):
        accepting = request.form["accepting_patients"].strip().lower()
        if accepting not in ("true", "false"):
            return make_response(jsonify({"error": "accepting_patients must be true or false"}), 400)
        updates["accepting_patients"] = (accepting == "true")

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

    # the doctor is worked out from the login token - a doctor can only change their own availability
    result = doctors.update_one({"doctor_id": g.user["doctor_id"]}, {"$set": updates})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    return make_response(jsonify({"message": "Availability updated", "doctor_id": g.user["doctor_id"], **updates}), 200)

# POST - patient adds a symptom to their booking (the symptom form before the appointment)
# if the symptom is an emergency, the response tells them to call 999
@app.route("/api/v1.0/consultations/<string:id>/symptoms", methods=["POST"])
@jwt_required
@role_required("patient", "admin")
@valid_id_required
def add_symptom(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # symptoms can only be added before the appointment happens
    if consultation["appointment"]["status"] not in ("booked", "pending"):
        return make_response(jsonify({"error": "Symptoms can only be added to a booked or pending appointment"}), 400)

    required = ("name", "severity", "duration_days")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    # type and range checks
    try:
        severity = int(request.form["severity"])
        duration = int(request.form["duration_days"])
    except ValueError:
        return make_response(jsonify({"error": "severity and duration_days must be whole numbers"}), 400)
    if severity < 1 or severity > 10:
        return make_response(jsonify({"error": "severity must be between 1 and 10"}), 400)
    if duration < 1 or duration > 365:
        return make_response(jsonify({"error": "duration_days must be between 1 and 365"}), 400)

    name = request.form["name"].strip().capitalize()
    new_symptom = {"name": name, "severity": severity, "duration_days": duration}

    # work out the new urgency from the most severe symptom - same rule as the data generator
    all_severities = [s["severity"] for s in consultation.get("symptoms", [])] + [severity]
    worst = max(all_severities)
    if worst >= 8:
        urgency = "high"
    elif worst >= 5:
        urgency = "medium"
    else:
        urgency = "low"

    # emergency symptoms always make the case high urgency
    emergency = name.lower() in EMERGENCY_SYMPTOMS
    if emergency:
        urgency = "high"

    consultations.update_one(
        {"_id": ObjectId(id)},
        {"$push": {"symptoms": new_symptom}, "$set": {"urgency_level": urgency}}
    )

    response = {"message": "Symptom added", "symptom": new_symptom, "urgency_level": urgency}
    if emergency:
        response["warning"] = "This could be an emergency. Do not wait for your appointment - call 999 now."
    return make_response(jsonify(response), 201)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
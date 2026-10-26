from flask import Flask, make_response, jsonify, request
from pymongo import MongoClient
from bson import ObjectId

from functools import wraps
import datetime

app = Flask(__name__)

# connect to my telemedicine database (capital T - must match Compass exactly)
client = MongoClient("mongodb://localhost:27017")
db = client.TelemedDB
consultations = db.consultations
doctors = db.doctors


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


@app.route("/", methods=["GET"])
def index():
    return make_response("<h1>Telemedicine API</h1>", 200)


# GET all consultations - with paging and optional filters
# e.g. /api/v1.0/consultations?status=completed&specialty=Cardiology&urgency=high
#      /api/v1.0/consultations?symptom=Fever&date_from=2026-03-01&date_to=2026-03-31
@app.route("/api/v1.0/consultations", methods=["GET"])
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
@valid_id_required
def show_one_consultation(id):
    # first version - now done by the @valid_id_required decorator
    # if not ObjectId.is_valid(id):
    #     return make_response(jsonify({"error": "Invalid consultation ID"}), 400)

    consultation = consultations.find_one({'_id': ObjectId(id)})
    if consultation is None:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    consultation['_id'] = str(consultation['_id'])
    for prescription in consultation.get('prescriptions', []):
        if '_id' in prescription:
            prescription['_id'] = str(prescription['_id'])
    return make_response(jsonify(consultation), 200)


# POST - book a new consultation
@app.route("/api/v1.0/consultations", methods=["POST"])
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
@valid_id_required
def edit_consultation(id):
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
@valid_id_required
def show_all_prescriptions(id):
    # projection - only bring back the prescriptions field, not the whole consultation
    consultation = consultations.find_one({"_id": ObjectId(id)}, {"prescriptions": 1, "_id": 0})
    if consultation is None:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    data_to_return = []
    for prescription in consultation.get("prescriptions", []):
        if "_id" in prescription:
            prescription["_id"] = str(prescription["_id"])
        data_to_return.append(prescription)

    return make_response(jsonify(data_to_return), 200)


# POST - add a new prescription to a consultation
@app.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["POST"])
@valid_id_required
def add_prescription(id):
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
@valid_id_required
def show_one_prescription(id, p_id):
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
@valid_id_required
def edit_prescription(id, p_id):
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
@valid_id_required
def delete_prescription(id, p_id):
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
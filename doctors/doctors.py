from flask import Blueprint, make_response, jsonify, request, g
from bson import ObjectId
import globals
from decorators import jwt_required, role_required, valid_id_required

doctors = globals.db.doctors
consultations = globals.db.consultations

# search, nearby, admin add/edit/delete and a doctor's own availability
doctors_bp = Blueprint("doctors_bp", __name__)


# GET all doctors - with optional filters and paging
# e.g. /api/v1.0/doctors?specialty=Dermatology&city=Belfast&accepting=true
@doctors_bp.route("/api/v1.0/doctors", methods=["GET"])
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
@doctors_bp.route("/api/v1.0/doctors/<string:id>", methods=["GET"])
@valid_id_required
def show_one_doctor(id):
    doctor = doctors.find_one({'_id': ObjectId(id)})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    doctor['_id'] = str(doctor['_id'])
    return make_response(jsonify(doctor), 200)


# GET doctors near a location - nearest first
# e.g. /api/v1.0/doctors/nearby?lat=54.597&lng=-5.930&distance=30&specialty=Dermatology
@doctors_bp.route("/api/v1.0/doctors/nearby", methods=["GET"])
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


# POST - admin adds a new doctor
@doctors_bp.route("/api/v1.0/doctors", methods=["POST"])
@jwt_required
@role_required("admin")
def add_doctor():
    # fields that must be sent - a tuple because this never changes
    required = ("name", "specialty", "city", "years_experience")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    specialty = request.form["specialty"].strip()
    if specialty not in globals.SPECIALTIES:
        return make_response(jsonify({"error": "specialty must be one of: " + ", ".join(globals.SPECIALTIES)}), 400)

    city = request.form["city"].strip()
    if city not in globals.CITIES:
        return make_response(jsonify({"error": "city must be one of: " + ", ".join(globals.CITIES)}), 400)

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
            "location": {"type": "Point", "coordinates": globals.CITIES[city]}
        }
    }

    result = doctors.insert_one(new_doctor)
    new_link = "http://localhost:5001/api/v1.0/doctors/" + str(result.inserted_id)
    return make_response(jsonify({"url": new_link, "doctor_id": new_doctor["doctor_id"]}), 201)

# PUT - admin edits a doctor (only the fields that are sent)
@doctors_bp.route("/api/v1.0/doctors/<string:id>", methods=["PUT"])
@jwt_required
@role_required("admin")
@valid_id_required
def edit_doctor(id):
    updates = {}

    if request.form.get("name"):
        updates["name"] = request.form["name"].strip()

    if request.form.get("specialty"):
        specialty = request.form["specialty"].strip()
        if specialty not in globals.SPECIALTIES:
            return make_response(jsonify({"error": "specialty must be one of: " + ", ".join(globals.SPECIALTIES)}), 400)
        updates["specialty"] = specialty

    if request.form.get("city"):
        city = request.form["city"].strip()
        if city not in globals.CITIES:
            return make_response(jsonify({"error": "city must be one of: " + ", ".join(globals.CITIES)}), 400)
        # moving city changes the whole clinic, including its map position
        updates["clinic"] = {
            "name": city + " Health Centre",
            "city": city,
            "location": {"type": "Point", "coordinates": globals.CITIES[city]}
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
@doctors_bp.route("/api/v1.0/doctors/<string:id>", methods=["DELETE"])
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
@doctors_bp.route("/api/v1.0/doctors/availability", methods=["PUT"])
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
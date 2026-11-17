from flask import Blueprint, make_response, jsonify, request, g
from bson import ObjectId
import globals
from decorators import jwt_required, role_required, valid_id_required

doctors = globals.db.doctors
consultations = globals.db.consultations

doctors_bp = Blueprint("doctors_bp", __name__)


# get all doctors, with filters and paging (no login needed)
# eg /api/v1.0/doctors?specialty=Dermatology&city=Belfast&accepting=true
@doctors_bp.route("/api/v1.0/doctors", methods=["GET"])
def show_all_doctors():
    # page number and page size must be whole numbers
    try:
        page_num = int(request.args.get('pn', 1))
        page_size = int(request.args.get('ps', 5))
    except ValueError:
        return make_response(jsonify({"error": "pn and ps must be whole numbers"}), 400)
    if page_num < 1 or page_size < 1 or page_size > 50:
        return make_response(jsonify({"error": "pn must be 1 or more and ps between 1 and 50"}), 400)
    page_start = page_size * (page_num - 1)

    # only add the filters that were sent
    query = {}
    if request.args.get('specialty'):
        query['specialty'] = request.args.get('specialty').strip()
    if request.args.get('city'):
        query['clinic.city'] = request.args.get('city').strip()
    if request.args.get('accepting'):
        accepting = request.args.get('accepting').strip().lower()
        if accepting not in ("true", "false"):
            return make_response(jsonify({"error": "accepting must be true or false"}), 400)
        query['accepting_patients'] = (accepting == "true")    # turn text into a boolean

    data_to_return = []
    for doctor in doctors.find(query).skip(page_start).limit(page_size):
        doctor['_id'] = str(doctor['_id'])
        data_to_return.append(doctor)

    return make_response(jsonify(data_to_return), 200)


# get one doctor
@doctors_bp.route("/api/v1.0/doctors/<string:id>", methods=["GET"])
@valid_id_required
def show_one_doctor(id):
    doctor = doctors.find_one({'_id': ObjectId(id)})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    doctor['_id'] = str(doctor['_id'])
    return make_response(jsonify(doctor), 200)


# doctors near a location, nearest first
# eg /api/v1.0/doctors/nearby?lat=54.597&lng=-5.930&distance=30
@doctors_bp.route("/api/v1.0/doctors/nearby", methods=["GET"])
def show_nearby_doctors():
    if not request.args.get('lat') or not request.args.get('lng'):
        return make_response(jsonify({"error": "lat and lng are required"}), 400)

    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
        distance_km = float(request.args.get('distance', 30))    # default 30km
    except ValueError:
        return make_response(jsonify({"error": "lat, lng and distance must be numbers"}), 400)

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return make_response(jsonify({"error": "lat must be -90 to 90 and lng -180 to 180"}), 400)
    if distance_km <= 0 or distance_km > 500:
        return make_response(jsonify({"error": "distance must be between 0 and 500 km"}), 400)

    # optional specialty filter
    query = {}
    if request.args.get('specialty'):
        query['specialty'] = request.args.get('specialty').strip()

    # $geoNear sorts by distance and adds how far away each doctor is
    pipeline = [
        {"$geoNear": {
            "near": {"type": "Point", "coordinates": [lng, lat]},    # longitude first
            "distanceField": "distance_km",
            "maxDistance": distance_km * 1000,    # metres
            "distanceMultiplier": 0.001,    # back to km
            "spherical": True,
            "query": query
        }}
    ]

    data_to_return = []
    for doctor in doctors.aggregate(pipeline):
        doctor['_id'] = str(doctor['_id'])
        doctor['distance_km'] = round(doctor['distance_km'], 1)
        data_to_return.append(doctor)

    return make_response(jsonify(data_to_return), 200)


# admin adds a doctor
@doctors_bp.route("/api/v1.0/doctors", methods=["POST"])
@jwt_required
@role_required("admin")
def add_doctor():
    # required fields (tuple as it never changes)
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

    try:
        years = int(request.form["years_experience"])
    except ValueError:
        return make_response(jsonify({"error": "years_experience must be a whole number"}), 400)
    if years < 0 or years > 60:
        return make_response(jsonify({"error": "years_experience must be between 0 and 60"}), 400)

    # gmc number is optional but must be 7 digits
    gmc_number = request.form.get("gmc_number", "").strip()
    if gmc_number and (len(gmc_number) != 7 or not gmc_number.isdigit()):
        return make_response(jsonify({"error": "gmc_number must be 7 digits"}), 400)

    # next doctor id, eg 24 doctors -> D124
    # skip ids that are already taken
    number = 100 + doctors.count_documents({})
    while doctors.find_one({"doctor_id": "D" + str(number)}) is not None:
        number += 1

    new_doctor = {
        "doctor_id": "D" + str(number),
        "name": request.form["name"].strip(),
        "specialty": specialty,
        "gmc_number": gmc_number or None,
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


# admin edits a doctor (only fields that are sent)
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
        # new city means a new clinic location
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

    # working days, eg Mon,Wed,Fri
    if request.form.get("available_days"):
        valid_days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        days = [day.strip().capitalize() for day in request.form["available_days"].split(",") if day.strip()]
        for day in days:
            if day not in valid_days:
                return make_response(jsonify({"error": day + " is not a valid day - use Mon, Tue, Wed, Thu, Fri, Sat, Sun"}), 400)
        updates["available_days"] = list(dict.fromkeys(days))

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


# admin deletes a doctor
@doctors_bp.route("/api/v1.0/doctors/<string:id>", methods=["DELETE"])
@jwt_required
@role_required("admin")
@valid_id_required
def delete_doctor(id):
    doctor = doctors.find_one({"_id": ObjectId(id)})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    # can't delete a doctor who still has upcoming appointments
    upcoming = consultations.count_documents({
        "doctor.doctor_id": doctor["doctor_id"],
        "appointment.status": {"$in": ["booked", "pending"]}
    })
    if upcoming > 0:
        return make_response(jsonify({"error": "Doctor has " + str(upcoming) + " upcoming appointments - cancel or move them first"}), 409)

    doctors.delete_one({"_id": ObjectId(id)})
    return make_response(jsonify({"message": "Doctor deleted"}), 200)


# doctor updates their own working days
# available_days is sent like Mon,Wed,Fri
@doctors_bp.route("/api/v1.0/doctors/availability", methods=["PUT"])
@jwt_required
@role_required("doctor")
def update_availability():
    updates = {}

    if request.form.get("available_days"):
        valid_days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
        # split into a list and tidy each day
        days = [day.strip().capitalize() for day in request.form["available_days"].split(",") if day.strip()]
        for day in days:
            if day not in valid_days:
                return make_response(jsonify({"error": day + " is not a valid day - use Mon, Tue, Wed, Thu, Fri, Sat, Sun"}), 400)
        # remove duplicates
        updates["available_days"] = list(dict.fromkeys(days))

    if request.form.get("accepting_patients"):
        accepting = request.form["accepting_patients"].strip().lower()
        if accepting not in ("true", "false"):
            return make_response(jsonify({"error": "accepting_patients must be true or false"}), 400)
        updates["accepting_patients"] = (accepting == "true")

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

    # doctor_id comes from the token so they can only change their own
    result = doctors.update_one({"doctor_id": g.user["doctor_id"]}, {"$set": updates})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    return make_response(jsonify({"message": "Availability updated", "doctor_id": g.user["doctor_id"], **updates}), 200)
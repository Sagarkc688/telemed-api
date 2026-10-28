from flask import Blueprint, make_response, jsonify, request, g
from bson import ObjectId
import datetime
import globals
from decorators import jwt_required, role_required, valid_id_required, find_consultation_for_user

consultations = globals.db.consultations
doctors = globals.db.doctors

# booking, symptoms, doctor notes and feedback
consultations_bp = Blueprint("consultations_bp", __name__)


# GET all consultations - with paging and optional filters
# e.g. /api/v1.0/consultations?status=completed&specialty=Cardiology&urgency=high
#      /api/v1.0/consultations?symptom=Fever&date_from=2026-03-01&date_to=2026-03-31
@consultations_bp.route("/api/v1.0/consultations", methods=["GET"])
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
@consultations_bp.route("/api/v1.0/consultations/<string:id>", methods=["GET"])
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
@consultations_bp.route("/api/v1.0/consultations", methods=["POST"])
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
@consultations_bp.route("/api/v1.0/consultations/<string:id>", methods=["PUT"])
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
@consultations_bp.route("/api/v1.0/consultations/<string:id>", methods=["DELETE"])
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


# POST - patient adds a symptom to their booking (the symptom form before the appointment)
# if the symptom is an emergency, the response tells them to call 999
@consultations_bp.route("/api/v1.0/consultations/<string:id>/symptoms", methods=["POST"])
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
    emergency = name.lower() in globals.EMERGENCY_SYMPTOMS
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

# PUT - doctor writes the consultation notes after the appointment
# adds the diagnosis and follow-up, can confirm or change the urgency, and marks the appointment completed
@consultations_bp.route("/api/v1.0/consultations/<string:id>/notes", methods=["PUT"])
@jwt_required
@role_required("doctor")
@valid_id_required
def add_notes(id):
    # a doctor can only write notes for their own patients
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    if consultation["appointment"]["status"] == "cancelled":
        return make_response(jsonify({"error": "Cannot add notes to a cancelled appointment"}), 400)

    if not request.form.get("diagnosis"):
        return make_response(jsonify({"error": "Missing field: diagnosis"}), 400)

    # follow-up is optional - if a date is sent, check it's a real date
    follow_up = {"required": False, "date": None}
    if request.form.get("follow_up_date"):
        follow_up_date = request.form["follow_up_date"].strip()
        try:
            datetime.datetime.strptime(follow_up_date, "%Y-%m-%d")
        except ValueError:
            return make_response(jsonify({"error": "follow_up_date must be a date like 2026-11-20"}), 400)
        follow_up = {"required": True, "date": follow_up_date}

    updates = {
        "consultation_notes": {
            "diagnosis": request.form["diagnosis"].strip(),
            "notes": request.form.get("notes", "").strip(),
            "follow_up": follow_up
        },
        "appointment.status": "completed",
        "timestamps.updated_at": str(datetime.date.today())
    }

    # the doctor can confirm or change the urgency set from the symptom form
    if request.form.get("urgency_level"):
        urgency = request.form["urgency_level"].strip()
        if urgency not in ("low", "medium", "high"):
            return make_response(jsonify({"error": "urgency_level must be low, medium or high"}), 400)
        updates["urgency_level"] = urgency

    consultations.update_one({"_id": ObjectId(id)}, {"$set": updates})

    edited_link = "http://localhost:5001/api/v1.0/consultations/" + id
    return make_response(jsonify({"message": "Notes added and appointment completed", "url": edited_link}), 200)


# POST - patient rates their consultation after it is completed
@consultations_bp.route("/api/v1.0/consultations/<string:id>/feedback", methods=["POST"])
@jwt_required
@role_required("patient")
@valid_id_required
def add_feedback(id):
    # a patient can only rate their own consultation
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    if consultation["appointment"]["status"] != "completed":
        return make_response(jsonify({"error": "You can only give feedback after the appointment is completed"}), 400)

    # only one rating per consultation
    if consultation.get("feedback"):
        return make_response(jsonify({"error": "Feedback has already been given for this consultation"}), 409)

    if not request.form.get("rating"):
        return make_response(jsonify({"error": "Missing field: rating"}), 400)

    # type and range check
    try:
        rating = int(request.form["rating"])
    except ValueError:
        return make_response(jsonify({"error": "rating must be a whole number"}), 400)
    if rating < 1 or rating > 5:
        return make_response(jsonify({"error": "rating must be between 1 and 5"}), 400)

    comment = request.form.get("comment", "").strip()
    if len(comment) > 500:
        return make_response(jsonify({"error": "comment must be 500 characters or less"}), 400)

    feedback = {"rating": rating, "comment": comment}
    consultations.update_one({"_id": ObjectId(id)}, {"$set": {"feedback": feedback}})

    return make_response(jsonify({"message": "Thank you for your feedback", "feedback": feedback}), 201)
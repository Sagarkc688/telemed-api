from flask import Blueprint, make_response, jsonify, request, g
from bson import ObjectId
import datetime
import globals
from decorators import jwt_required, role_required, valid_id_required, find_consultation_for_user

consultations = globals.db.consultations
doctors = globals.db.doctors

consultations_bp = Blueprint("consultations_bp", __name__)


# get consultations, with paging and filters
# eg /api/v1.0/consultations?status=completed&urgency=high&symptom=Fever
@consultations_bp.route("/api/v1.0/consultations", methods=["GET"])
@jwt_required
def show_all_consultations():
    page_num, page_size = 1, 5

    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))

    page_start = page_size * (page_num - 1)

    # only add the filters that were sent
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

    # date range (dates are stored as YYYY-MM-DD so they sort correctly)
    date_range = {}
    for arg, operator in (('date_from', '$gte'), ('date_to', '$lte')):
        if request.args.get(arg):
            value = request.args.get(arg).strip()
            try:
                datetime.datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return make_response(jsonify({"error": arg + " must be a date like 2026-03-31"}), 400)
            date_range[operator] = value
    if date_range:
        query['appointment.date'] = date_range

    # doctors and patients only see their own
    if g.user["role"] == "doctor":
        query['doctor.doctor_id'] = g.user["doctor_id"]
    elif g.user["role"] == "patient":
        query['patient.contact.email'] = g.user["email"]

    data_to_return = []
    for consultation in consultations.find(query).skip(page_start).limit(page_size):
        consultation['_id'] = str(consultation['_id'])
        # ObjectId to string for JSON
        for prescription in consultation.get('prescriptions', []):
            if '_id' in prescription:
                prescription['_id'] = str(prescription['_id'])
        data_to_return.append(consultation)

    return make_response(jsonify(data_to_return), 200)


# get one consultation
@consultations_bp.route("/api/v1.0/consultations/<string:id>", methods=["GET"])
@jwt_required
@valid_id_required
def show_one_consultation(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    consultation['_id'] = str(consultation['_id'])
    for prescription in consultation.get('prescriptions', []):
        if '_id' in prescription:
            prescription['_id'] = str(prescription['_id'])
    return make_response(jsonify(consultation), 200)


# book a consultation
@consultations_bp.route("/api/v1.0/consultations", methods=["POST"])
@jwt_required
@role_required("patient", "admin")
def add_consultation():
    # required fields (tuple as it never changes)
    required = ("patient_name", "patient_email", "doctor_id", "date", "time_slot", "type")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    # strip() removes any extra spaces
    appointment_type = request.form["type"].strip()
    if appointment_type not in ("video", "phone"):
        return make_response(jsonify({"error": "type must be video or phone"}), 400)

    doctor = doctors.find_one({"doctor_id": request.form["doctor_id"].strip()})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    new_id = ObjectId()    # made first so the video link can use it
    today = str(datetime.date.today())

    new_consultation = {
        "_id": new_id,
        "patient": {
            "name": request.form["patient_name"].strip(),
            "contact": {"email": request.form["patient_email"].strip()}
        },
        "doctor": {
            "doctor_id": doctor["doctor_id"],
            "name": doctor["name"],
            "specialty": doctor["specialty"],
            "gmc_number": doctor.get("gmc_number")
        },
        "appointment": {
            "date": request.form["date"].strip(),
            "time_slot": request.form["time_slot"].strip(),
            "type": appointment_type,
            "video_link": "https://meet.example.com/" + str(new_id) if appointment_type == "video" else None,
            "status": "booked"
        },
        "symptoms": [],
        "urgency_level": "low",    # updated when symptoms are added
        "consultation_notes": None,
        "prescriptions": [],
        "feedback": None,
        "timestamps": {"created_at": today, "updated_at": today}
    }

    consultations.insert_one(new_consultation)
    new_link = "http://localhost:5001/api/v1.0/consultations/" + str(new_id)
    return make_response(jsonify({"url": new_link}), 201)


# edit the appointment (only fields that are sent), also used to cancel
@consultations_bp.route("/api/v1.0/consultations/<string:id>", methods=["PUT"])
@jwt_required
@valid_id_required
def edit_consultation(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # fields that can be changed
    allowed = ("date", "time_slot", "type", "status")
    updates = {}
    for field in allowed:
        if request.form.get(field):
            # dot notation to update inside appointment
            updates["appointment." + field] = request.form[field].strip()

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

    if "appointment.type" in updates and updates["appointment.type"] not in ("video", "phone"):
        return make_response(jsonify({"error": "type must be video or phone"}), 400)
    if "appointment.status" in updates and updates["appointment.status"] not in ("pending", "booked", "completed", "cancelled"):
        return make_response(jsonify({"error": "Invalid status"}), 400)

    result = consultations.update_one({"_id": ObjectId(id)}, {"$set": updates})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    edited_link = "http://localhost:5001/api/v1.0/consultations/" + id
    return make_response(jsonify({"url": edited_link}), 200)


# admin deletes a consultation
@consultations_bp.route("/api/v1.0/consultations/<string:id>", methods=["DELETE"])
@jwt_required
@role_required("admin")
@valid_id_required
def delete_consultation(id):
    result = consultations.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    return make_response(jsonify({"message": "Consultation deleted"}), 200)


# patient adds a symptom before the appointment
# emergency symptoms get a 999 warning
@consultations_bp.route("/api/v1.0/consultations/<string:id>/symptoms", methods=["POST"])
@jwt_required
@role_required("patient", "admin")
@valid_id_required
def add_symptom(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    if consultation["appointment"]["status"] not in ("booked", "pending"):
        return make_response(jsonify({"error": "Symptoms can only be added to a booked or pending appointment"}), 400)

    required = ("name", "severity", "duration_days")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

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

    # urgency is based on the worst symptom
    all_severities = [s["severity"] for s in consultation.get("symptoms", [])] + [severity]
    worst = max(all_severities)
    if worst >= 8:
        urgency = "high"
    elif worst >= 5:
        urgency = "medium"
    else:
        urgency = "low"

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


# doctor adds notes after the appointment and marks it completed
@consultations_bp.route("/api/v1.0/consultations/<string:id>/notes", methods=["PUT"])
@jwt_required
@role_required("doctor")
@valid_id_required
def add_notes(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    if consultation["appointment"]["status"] == "cancelled":
        return make_response(jsonify({"error": "Cannot add notes to a cancelled appointment"}), 400)

    if not request.form.get("diagnosis"):
        return make_response(jsonify({"error": "Missing field: diagnosis"}), 400)

    # follow up date is optional
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

    # doctor can confirm or change the urgency
    if request.form.get("urgency_level"):
        urgency = request.form["urgency_level"].strip()
        if urgency not in ("low", "medium", "high"):
            return make_response(jsonify({"error": "urgency_level must be low, medium or high"}), 400)
        updates["urgency_level"] = urgency

    consultations.update_one({"_id": ObjectId(id)}, {"$set": updates})

    edited_link = "http://localhost:5001/api/v1.0/consultations/" + id
    return make_response(jsonify({"message": "Notes added and appointment completed", "url": edited_link}), 200)


# patient leaves feedback after a completed appointment
@consultations_bp.route("/api/v1.0/consultations/<string:id>/feedback", methods=["POST"])
@jwt_required
@role_required("patient")
@valid_id_required
def add_feedback(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    if consultation["appointment"]["status"] != "completed":
        return make_response(jsonify({"error": "You can only give feedback after the appointment is completed"}), 400)

    # only one rating allowed
    if consultation.get("feedback"):
        return make_response(jsonify({"error": "Feedback has already been given for this consultation"}), 409)

    if not request.form.get("rating"):
        return make_response(jsonify({"error": "Missing field: rating"}), 400)

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
from flask import Flask, make_response, jsonify, request
from pymongo import MongoClient
from bson import ObjectId

from functools import wraps

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


# GET all consultations - with paging (pn = page number, ps = page size)
@app.route("/api/v1.0/consultations", methods=["GET"])
def show_all_consultations():
    page_num, page_size = 1, 5

    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))

    page_start = page_size * (page_num - 1)

    data_to_return = []
    for consultation in consultations.find().skip(page_start).limit(page_size):
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
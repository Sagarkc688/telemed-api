from flask import Blueprint, make_response, jsonify, request
from bson import ObjectId
import globals
from decorators import jwt_required, role_required, valid_id_required, find_consultation_for_user

consultations = globals.db.consultations

# prescriptions - the sub-documents inside a consultation
prescriptions_bp = Blueprint("prescriptions_bp", __name__)


# GET all prescriptions for one consultation
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["GET"])
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
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["POST"])
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
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["GET"])
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
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["PUT"])
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
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["DELETE"])
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
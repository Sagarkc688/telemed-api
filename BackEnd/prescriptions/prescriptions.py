from flask import Blueprint, make_response, jsonify, request
from bson import ObjectId
import globals
from decorators import jwt_required, role_required, valid_id_required, find_consultation_for_user

consultations = globals.db.consultations

# prescriptions are stored inside each consultation
prescriptions_bp = Blueprint("prescriptions_bp", __name__)


# get all prescriptions for a consultation
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["GET"])
@jwt_required
@valid_id_required
def show_all_prescriptions(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    data_to_return = []
    for prescription in consultation.get("prescriptions", []):
        if "_id" in prescription:
            prescription["_id"] = str(prescription["_id"])
        data_to_return.append(prescription)

    return make_response(jsonify(data_to_return), 200)


# doctor adds a prescription
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions", methods=["POST"])
@jwt_required
@role_required("doctor")
@valid_id_required
def add_prescription(id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # required fields (tuple as it never changes)
    required = ("medicine", "dosage", "frequency", "duration_days")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    try:
        duration = int(request.form["duration_days"])
    except ValueError:
        return make_response(jsonify({"error": "duration_days must be a whole number"}), 400)

    # 1 day to 1 year
    if duration < 1 or duration > 365:
        return make_response(jsonify({"error": "duration_days must be between 1 and 365"}), 400)

    new_prescription = {
        "_id": ObjectId(),    # own id so it can be edited/deleted later
        "medicine": request.form["medicine"].strip(),
        "dosage": request.form["dosage"].strip(),
        "frequency": request.form["frequency"].strip(),
        "duration_days": duration
    }

    # $push adds it to the prescriptions array
    result = consultations.update_one({"_id": ObjectId(id)}, {"$push": {"prescriptions": new_prescription}})
    if result.matched_count == 0:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    new_link = "http://localhost:5001/api/v1.0/consultations/" + id + "/prescriptions/" + str(new_prescription["_id"])
    return make_response(jsonify({"url": new_link}), 201)


# get one prescription
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["GET"])
@jwt_required
@valid_id_required
def show_one_prescription(id, p_id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # prescriptions.$ returns only the matching prescription
    consultation = consultations.find_one(
        {"_id": ObjectId(id), "prescriptions._id": ObjectId(p_id)},
        {"prescriptions.$": 1, "_id": 0}
    )
    if consultation is None:
        return make_response(jsonify({"error": "Prescription not found"}), 404)

    prescription = consultation["prescriptions"][0]
    prescription["_id"] = str(prescription["_id"])
    return make_response(jsonify(prescription), 200)


# doctor edits a prescription (only fields that are sent)
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
            # $ = the prescription that matched
            updates["prescriptions.$." + field] = request.form[field].strip()

    if not updates:
        return make_response(jsonify({"error": "No fields to update"}), 400)

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


# doctor deletes a prescription
@prescriptions_bp.route("/api/v1.0/consultations/<string:id>/prescriptions/<string:p_id>", methods=["DELETE"])
@jwt_required
@role_required("doctor")
@valid_id_required
def delete_prescription(id, p_id):
    consultation, error = find_consultation_for_user(id)
    if error:
        return error

    # $pull removes it from the array
    result = consultations.update_one(
        {"_id": ObjectId(id)},
        {"$pull": {"prescriptions": {"_id": ObjectId(p_id)}}}
    )
    if result.modified_count == 0:
        return make_response(jsonify({"error": "Prescription not found"}), 404)

    return make_response(jsonify({"message": "Prescription deleted"}), 200)
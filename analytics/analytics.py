from flask import Blueprint, make_response, jsonify, request
import globals
from decorators import jwt_required, role_required

consultations = globals.db.consultations

analytics_bp = Blueprint("analytics_bp", __name__)


# most common symptoms, can filter by specialty
@analytics_bp.route("/api/v1.0/analytics/top-symptoms", methods=["GET"])
@jwt_required
@role_required("admin")
def top_symptoms():
    try:
        limit = int(request.args.get('limit', 5))    # default 5
    except ValueError:
        return make_response(jsonify({"error": "limit must be a whole number"}), 400)
    if limit < 1 or limit > 50:
        return make_response(jsonify({"error": "limit must be between 1 and 50"}), 400)

    pipeline = []
    if request.args.get('specialty'):
        pipeline.append({"$match": {"doctor.specialty": request.args.get('specialty').strip()}})

    pipeline += [
        {"$unwind": "$symptoms"},    # one row per symptom
        {"$group": {
            "_id": "$symptoms.name",
            "count": {"$sum": 1},
            "average_severity": {"$avg": "$symptoms.severity"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "symptom": "$_id", "count": 1,
                      "average_severity": {"$round": ["$average_severity", 1]}}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)


# average rating for each doctor
@analytics_bp.route("/api/v1.0/analytics/doctor-ratings", methods=["GET"])
@jwt_required
@role_required("admin")
def doctor_ratings():
    pipeline = [
        {"$match": {"appointment.status": "completed", "feedback.rating": {"$exists": True}}},
        {"$group": {
            "_id": "$doctor.doctor_id",    # id not name, two doctors could have the same name
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


# consultations per month, with completed and cancelled counts
@analytics_bp.route("/api/v1.0/analytics/monthly", methods=["GET"])
@jwt_required
@role_required("admin")
def consultations_per_month():
    pipeline = [
        {"$group": {
            # first 7 characters of the date is the month, eg 2026-03
            "_id": {"$substrBytes": ["$appointment.date", 0, 7]},
            "total": {"$sum": 1},
            # $cond works like an if/else
            "completed": {"$sum": {"$cond": [{"$eq": ["$appointment.status", "completed"]}, 1, 0]}},
            "cancelled": {"$sum": {"$cond": [{"$eq": ["$appointment.status", "cancelled"]}, 1, 0]}}
        }},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "month": "$_id", "total": 1, "completed": 1, "cancelled": 1}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)


# most prescribed medicines, can filter by specialty
@analytics_bp.route("/api/v1.0/analytics/top-medicines", methods=["GET"])
@jwt_required
@role_required("admin")
def top_medicines():
    try:
        limit = int(request.args.get('limit', 5))    # default 5
    except ValueError:
        return make_response(jsonify({"error": "limit must be a whole number"}), 400)
    if limit < 1 or limit > 50:
        return make_response(jsonify({"error": "limit must be between 1 and 50"}), 400)

    pipeline = []
    if request.args.get('specialty'):
        pipeline.append({"$match": {"doctor.specialty": request.args.get('specialty').strip()}})

    pipeline += [
        {"$unwind": "$prescriptions"},
        {"$group": {
            "_id": "$prescriptions.medicine",
            "times_prescribed": {"$sum": 1},
            "average_days": {"$avg": "$prescriptions.duration_days"}
        }},
        {"$sort": {"times_prescribed": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "medicine": "$_id", "times_prescribed": 1,
                      "average_days": {"$round": ["$average_days", 1]}}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)


# busiest days and time slots
@analytics_bp.route("/api/v1.0/analytics/peak-times", methods=["GET"])
@jwt_required
@role_required("admin")
def peak_times():
    day_names = ["", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    pipeline = [
        # don't count cancelled ones
        {"$match": {"appointment.status": {"$ne": "cancelled"}}},
        # $facet runs two pipelines at once
        {"$facet": {
            "busiest_days": [
                # day of week from the date (1 = Sunday)
                {"$group": {
                    "_id": {"$dayOfWeek": {"$dateFromString": {
                        "dateString": "$appointment.date", "onError": None, "onNull": None}}},
                    "bookings": {"$sum": 1}
                }},
                {"$match": {"_id": {"$ne": None}}},
                {"$sort": {"bookings": -1}},
                {"$project": {"_id": 0, "day": {"$arrayElemAt": [day_names, "$_id"]}, "bookings": 1}}
            ],
            "busiest_time_slots": [
                {"$group": {"_id": "$appointment.time_slot", "bookings": {"$sum": 1}}},
                {"$sort": {"bookings": -1}},
                {"$limit": 5},
                {"$project": {"_id": 0, "time_slot": "$_id", "bookings": 1}}
            ]
        }}
    ]

    result = list(consultations.aggregate(pipeline))[0]
    return make_response(jsonify(result), 200)
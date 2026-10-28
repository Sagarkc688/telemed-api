from flask import Blueprint, make_response, jsonify, request
import globals
from decorators import jwt_required, role_required

consultations = globals.db.consultations

# admin reports - aggregation pipelines
analytics_bp = Blueprint("analytics_bp", __name__)


# ANALYTICS - most common symptoms (optionally for one specialty)
# e.g. /api/v1.0/analytics/top-symptoms?limit=5&specialty=Respiratory
@analytics_bp.route("/api/v1.0/analytics/top-symptoms", methods=["GET"])
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
@analytics_bp.route("/api/v1.0/analytics/doctor-ratings", methods=["GET"])
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
@analytics_bp.route("/api/v1.0/analytics/monthly", methods=["GET"])
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


# ANALYTICS - most prescribed medicines (optionally for one specialty)
# e.g. /api/v1.0/analytics/top-medicines?limit=5&specialty=Cardiology
@analytics_bp.route("/api/v1.0/analytics/top-medicines", methods=["GET"])
@jwt_required
@role_required("admin")
def top_medicines():
    try:
        limit = int(request.args.get('limit', 5))      # top 5 if not sent
    except ValueError:
        return make_response(jsonify({"error": "limit must be a whole number"}), 400)
    if limit < 1 or limit > 50:
        return make_response(jsonify({"error": "limit must be between 1 and 50"}), 400)

    pipeline = []
    if request.args.get('specialty'):
        pipeline.append({"$match": {"doctor.specialty": request.args.get('specialty').strip()}})

    pipeline += [
        {"$unwind": "$prescriptions"},                   # one row per prescription
        {"$group": {
            "_id": "$prescriptions.medicine",            # group rows with the same medicine
            "times_prescribed": {"$sum": 1},
            "average_days": {"$avg": "$prescriptions.duration_days"}
        }},
        {"$sort": {"times_prescribed": -1}},             # most prescribed first
        {"$limit": limit},
        {"$project": {"_id": 0, "medicine": "$_id", "times_prescribed": 1,
                      "average_days": {"$round": ["$average_days", 1]}}}
    ]

    return make_response(jsonify(list(consultations.aggregate(pipeline))), 200)


# ANALYTICS - peak booking times: busiest days of the week and busiest time slots
@analytics_bp.route("/api/v1.0/analytics/peak-times", methods=["GET"])
@jwt_required
@role_required("admin")
def peak_times():
    day_names = ["", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    pipeline = [
        # cancelled appointments didn't happen, so don't count them
        {"$match": {"appointment.status": {"$ne": "cancelled"}}},
        # $facet runs two separate pipelines on the same data and returns both results together
        {"$facet": {
            "busiest_days": [
                # turn the text date into a real date, then get the day of the week (1 = Sunday ... 7 = Saturday)
                {"$group": {
                    "_id": {"$dayOfWeek": {"$dateFromString": {
                        "dateString": "$appointment.date", "onError": None, "onNull": None}}},
                    "bookings": {"$sum": 1}
                }},
                {"$match": {"_id": {"$ne": None}}},      # skip any dates that couldn't be read
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

    # $facet always returns one document holding both lists
    result = list(consultations.aggregate(pipeline))[0]
    return make_response(jsonify(result), 200)
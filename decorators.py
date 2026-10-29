from flask import make_response, jsonify, request, g
from bson import ObjectId
from functools import wraps
import jwt
import globals

consultations = globals.db.consultations
blacklist = globals.db.blacklist


# checks the login token sent in the x-access-token header
def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return make_response(jsonify({"message": "Token is missing"}), 401)

        # token was logged out
        if blacklist.find_one({"token": token}):
            return make_response(jsonify({"message": "You have logged out - please log in again"}), 401)

        try:
            data = jwt.decode(token, globals.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return make_response(jsonify({"message": "Token has expired - please log in again"}), 401)
        except jwt.InvalidTokenError:
            return make_response(jsonify({"message": "Token is invalid"}), 401)

        # save the user so the routes can use it
        g.user = data
        return func(*args, **kwargs)
    return jwt_required_wrapper


# only allows the given roles, eg @role_required("doctor", "admin")
# needs to go after @jwt_required
def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def role_required_wrapper(*args, **kwargs):
            if g.user["role"] not in roles:
                return make_response(jsonify({"message": "You do not have permission to do this"}), 403)
            return func(*args, **kwargs)
        return role_required_wrapper
    return decorator


# checks every id in the URL is a valid ObjectId
# ids come in kwargs so this works for routes with one or two ids
def valid_id_required(func):
    @wraps(func)
    def valid_id_wrapper(*args, **kwargs):
        for value in kwargs.values():
            if not ObjectId.is_valid(value):
                return make_response(jsonify({"error": "Invalid ID"}), 400)
        return func(*args, **kwargs)
    return valid_id_wrapper


# admin sees everything, doctors see their own patients, patients see their own
def can_access(consultation):
    user = g.user
    if user["role"] == "admin":
        return True
    if user["role"] == "doctor":
        return consultation["doctor"]["doctor_id"] == user.get("doctor_id")
    if user["role"] == "patient":
        return consultation.get("patient", {}).get("contact", {}).get("email") == user.get("email")
    return False


# finds a consultation and checks the user can access it
# returns (consultation, None) or (None, error)
def find_consultation_for_user(id):
    consultation = consultations.find_one({"_id": ObjectId(id)})
    if consultation is None:
        return None, make_response(jsonify({"error": "Consultation not found"}), 404)
    if not can_access(consultation):
        return None, make_response(jsonify({"message": "You do not have permission to do this"}), 403)
    return consultation, None
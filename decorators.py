from flask import make_response, jsonify, request, g
from bson import ObjectId
from functools import wraps
import jwt
import globals

consultations = globals.db.consultations
blacklist = globals.db.blacklist

# decorators and helpers used by the routes in every Blueprint


# decorator - only lets the request through if it has a valid login token
# same idea as jwt_required in class, but the token is sent in a header instead of the URL
def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return make_response(jsonify({"message": "Token is missing"}), 401)

        
        # a token from a user who logged out can't be used again
        if blacklist.find_one({"token": token}):
            return make_response(jsonify({"message": "You have logged out - please log in again"}), 401)

        try:
            data = jwt.decode(token, globals.secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return make_response(jsonify({"message": "Token has expired - please log in again"}), 401)
        except jwt.InvalidTokenError:
            return make_response(jsonify({"message": "Token is invalid"}), 401)

        # remember who is logged in for this request, so routes and role checks can use it
        g.user = data
        return func(*args, **kwargs)
    return jwt_required_wrapper


# decorator factory - only lets in users whose role is in the list
# *roles collects any number of roles into a tuple, e.g. role_required("doctor", "admin") -> ("doctor", "admin")
# must be used AFTER @jwt_required, which works out who is logged in
def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def role_required_wrapper(*args, **kwargs):
            if g.user["role"] not in roles:
                return make_response(jsonify({"message": "You do not have permission to do this"}), 403)
            return func(*args, **kwargs)
        return role_required_wrapper
    return decorator


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


# checks if the logged-in user is allowed to see this consultation
# admin - any consultation, doctor - only their own patients, patient - only their own
def can_access(consultation):
    user = g.user
    if user["role"] == "admin":
        return True
    if user["role"] == "doctor":
        return consultation["doctor"]["doctor_id"] == user.get("doctor_id")
    if user["role"] == "patient":
        return consultation.get("patient", {}).get("contact", {}).get("email") == user.get("email")
    return False


# finds a consultation and checks the user is allowed to use it
# returns a tuple: (consultation, None) if ok, or (None, error response) if not
def find_consultation_for_user(id):
    consultation = consultations.find_one({"_id": ObjectId(id)})
    if consultation is None:
        return None, make_response(jsonify({"error": "Consultation not found"}), 404)
    if not can_access(consultation):
        return None, make_response(jsonify({"message": "You do not have permission to do this"}), 403)
    return consultation, None
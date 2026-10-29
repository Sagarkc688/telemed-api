from flask import Blueprint, make_response, jsonify, request
import datetime
import jwt
import bcrypt
import globals
from decorators import jwt_required

users = globals.db.users
blacklist = globals.db.blacklist

auth_bp = Blueprint("auth_bp", __name__)


# login with Basic Auth, returns a token
@auth_bp.route("/api/v1.0/login", methods=["GET"])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return make_response(jsonify({"message": "Username and password required"}), 401,
                             {'WWW-Authenticate': 'Basic realm="Login required"'})

    user = users.find_one({"username": auth.username})

    # same message for both so it doesn't give away which one was wrong
    if user is None or not bcrypt.checkpw(auth.password.encode("utf-8"), user["password"].encode("utf-8")):
        return make_response(jsonify({"message": "Wrong username or password"}), 401)

    # role, email and doctor_id are used by the routes
    token = jwt.encode({
        "user": user["username"],
        "role": user["role"],
        "email": user["email"],
        "doctor_id": user.get("doctor_id"),
        "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=30)
    }, globals.secret_key, algorithm="HS256")

    return make_response(jsonify({"token": token}), 200)


# logout - adds the token to the blacklist
@auth_bp.route("/api/v1.0/logout", methods=["GET"])
@jwt_required
def logout():
    token = request.headers.get('x-access-token')
    blacklist.insert_one({"token": token})
    return make_response(jsonify({"message": "Logged out"}), 200)
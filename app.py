from flask import Flask, make_response, jsonify, request
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)

# connect to my telemedicine database (capital T - must match Compass exactly)
client = MongoClient("mongodb://localhost:27017")
db = client.TelemedDB
consultations = db.consultations
doctors = db.doctors


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
        data_to_return.append(consultation)

    return make_response(jsonify(data_to_return), 200)

# GET one consultation by its _id
@app.route("/api/v1.0/consultations/<string:id>", methods=["GET"])
def show_one_consultation(id):
    if not ObjectId.is_valid(id):
        return make_response(jsonify({"error": "Invalid consultation ID"}), 400)

    consultation = consultations.find_one({'_id': ObjectId(id)})
    if consultation is None:
        return make_response(jsonify({"error": "Consultation not found"}), 404)

    consultation['_id'] = str(consultation['_id'])
    return make_response(jsonify(consultation), 200)

# POST - book a new consultation
@app.route("/api/v1.0/consultations", methods=["POST"])
def add_consultation():
    # fields that must be sent - a tuple because this list never changes
    required = ("patient_name", "patient_email", "doctor_id", "date", "time_slot", "type")
    for field in required:
        if not request.form.get(field):
            return make_response(jsonify({"error": "Missing field: " + field}), 400)

    # appointment type can only be video or phone
    if request.form["type"].strip() not in ("video", "phone"):        return make_response(jsonify({"error": "type must be video or phone"}), 400)

    # the doctor must exist in the doctors collection
    doctor = doctors.find_one({"doctor_id": request.form["doctor_id"]})
    if doctor is None:
        return make_response(jsonify({"error": "Doctor not found"}), 404)

    new_consultation = {
        "patient": {
            "name": request.form["patient_name"],
            "contact": {"email": request.form["patient_email"]}
        },
        "doctor": {
            "doctor_id": doctor["doctor_id"],
            "name": doctor["name"],
            "specialty": doctor["specialty"]
        },
        "appointment": {
            "date": request.form["date"],
            "time_slot": request.form["time_slot"],
            "type": request.form["type"],
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
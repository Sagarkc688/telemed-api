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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
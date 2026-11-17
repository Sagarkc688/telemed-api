from flask import Flask, make_response
import globals

from auth.auth import auth_bp
from consultations.consultations import consultations_bp
from prescriptions.prescriptions import prescriptions_bp
from doctors.doctors import doctors_bp
from analytics.analytics import analytics_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = globals.secret_key

# register the blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(consultations_bp)
app.register_blueprint(prescriptions_bp)
app.register_blueprint(doctors_bp)
app.register_blueprint(analytics_bp)


@app.route("/", methods=["GET"])
def index():
    return make_response("<h1>Telemedicine API</h1>", 200)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
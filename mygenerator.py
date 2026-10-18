import random
import json
from datetime import date, timedelta

specialties = ['General Practice', 'Dermatology', 'Cardiology']
# symptoms that make sense for each specialty
symptoms_by_specialty = {
    'General Practice': ['Headache', 'Fever', 'Sore throat', 'Fatigue', 'Back pain'],
    'Dermatology': ['Rash', 'Itching', 'Acne', 'Dry skin'],
    'Cardiology': ['Palpitations', 'Dizziness', 'Chest tightness', 'Shortness of breath']
}

#print(random.choice(specialties))   # test 1: checked random picks work

first_names = ['Sarah', 'James', 'Aoife', 'Ciaran', 'Emma', 'Liam']
last_names = ['Kelly', 'Wilson', 'Murphy', 'Campbell', 'Smith', 'Brown']

# city coordinates [longitude, latitude] for location searches later
cities = {
    'Belfast': [-5.9301, 54.5973],
    'Derry': [-7.3086, 54.9966],
    'Newry': [-6.3374, 54.1751],
    'Armagh': [-6.6547, 54.3503]
}

streets = ['Main Street', 'High Street', 'Church Road', 'Station Road', 'Mill Lane']

time_slots = ['09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00', '15:30', '16:00']

# test 2: made one doctor first to check the structure
#name = 'Dr ' + random.choice(first_names) + ' ' + random.choice(last_names)
#doctor = {
#    'doctor_id': 'D100',
#    'name': name,
#    'specialty': random.choice(specialties),
#    'years_experience': random.randint(2, 30)
#}
#print(doctor)

doctor_list = []

for i in range(10):
    name = 'Dr ' + random.choice(first_names) + ' ' + random.choice(last_names)
    city = random.choice(list(cities.keys()))

    doctor = {
        'doctor_id': 'D' + str(100 + i),
        'name': name,
        'specialty': random.choice(specialties),
        'years_experience': random.randint(2, 30),
        'available_days': random.sample(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], 3),
        'accepting_patients': random.choice([True, False]),
        'clinic': {                       # nested document
            'name': city + ' Health Centre',
            'city': city,
            'location': {                 # GeoJSON point for geo queries
                'type': 'Point',
                'coordinates': cities[city]
            }
        }
    }

    doctor_list.append(doctor)

#print(doctor_list)   # test 3: checked the list before saving

with open('doctors.json', 'w', encoding='utf-8') as fout:
    json.dump(doctor_list, fout, indent=4)

print('Created', len(doctor_list), 'doctors')


# ---- consultations ----

# ---- consultations ----

consultation_list = []

for i in range(20):
    chosen_doctor = random.choice(doctor_list)   # pick one of our doctors
    patient_name = random.choice(first_names) + ' ' + random.choice(last_names)
    patient_city = random.choice(list(cities.keys()))

    # each patient gets 1-3 symptoms that match the doctor's specialty
    specialty = chosen_doctor['specialty']
    symptoms = []
    for symptom_name in random.sample(symptoms_by_specialty[specialty], random.randint(1, 3)):
        symptoms.append({
            'name': symptom_name,
            'severity': random.randint(1, 10),
            'duration_days': random.randint(1, 21)
        })

    # urgency depends on the most severe symptom
    worst = max(s['severity'] for s in symptoms)
    if worst >= 8:
        urgency = 'high'
    elif worst >= 5:
        urgency = 'medium'
    else:
        urgency = 'low'

    # random date in 2026 - past ones are finished, future ones are still to come
    appointment_date = date(2026, 1, 5) + timedelta(days=random.randint(0, 345))
    if appointment_date < date(2026, 10, 16):
        status = random.choice(['completed', 'completed', 'completed', 'cancelled'])
    else:
        status = random.choice(['booked', 'pending'])

    consultation = {
        'consultation_id': 'C' + str(1000 + i),
        'patient': {                             # nested patient document
            'patient_id': 'P' + str(random.randint(1000, 1999)),
            'name': patient_name,
            'date_of_birth': f'{random.randint(1950, 2015)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}',
            'gender': random.choice(['Female', 'Male']),
            'contact': {                         # nested inside patient
                'phone': '07700 ' + str(random.randint(900000, 900999)),
                'email': patient_name.lower().replace(' ', '.') + '@example.com',
                'address': {                     # nested again
                    'street': str(random.randint(1, 120)) + ' ' + random.choice(streets),
                    'city': patient_city,
                    'postcode': 'BT' + str(random.randint(1, 94))
                }
            }
        },
        'doctor': {                              # copy of the doctor's key details
            'doctor_id': chosen_doctor['doctor_id'],
            'name': chosen_doctor['name'],
            'specialty': chosen_doctor['specialty']
        },
        'appointment': {                         # nested appointment details
            'date': str(appointment_date),
            'time_slot': random.choice(time_slots),
            'type': random.choice(['video', 'video', 'phone']),
            'video_link': 'https://meet.example.com/c' + str(1000 + i),
            'status': status
        },
        'symptoms': symptoms,                    # array of objects
        #'urgency_level': random.choice(['low', 'medium', 'high'])   # first version: random
        'urgency_level': urgency
    }

    consultation_list.append(consultation)

with open('consultations.json', 'w', encoding='utf-8') as fout:
    json.dump(consultation_list, fout, indent=4)

print('Created', len(consultation_list), 'consultations')
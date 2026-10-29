import random
import json
from datetime import date, timedelta

# generates doctors.json and consultations.json

specialties = ['General Practice', 'Dermatology', 'Cardiology',
               'Paediatrics', 'Mental Health', 'Respiratory']

# symptoms, diagnoses and medicines for each specialty
symptoms_by_specialty = {
    'General Practice': ['Headache', 'Fever', 'Sore throat', 'Fatigue', 'Back pain'],
    'Dermatology': ['Rash', 'Itching', 'Acne', 'Dry skin'],
    'Cardiology': ['Palpitations', 'Dizziness', 'Chest tightness', 'Shortness of breath'],
    'Paediatrics': ['Fever', 'Earache', 'Cough', 'Rash', 'Vomiting'],
    'Mental Health': ['Anxiety', 'Low mood', 'Insomnia', 'Stress', 'Poor concentration'],
    'Respiratory': ['Cough', 'Wheezing', 'Shortness of breath', 'Chest infection']
}

diagnoses_by_specialty = {
    'General Practice': ['Viral infection', 'Migraine', 'Tonsillitis', 'Muscle strain'],
    'Dermatology': ['Eczema', 'Contact dermatitis', 'Acne', 'Psoriasis'],
    'Cardiology': ['High blood pressure', 'Benign palpitations', 'Anxiety-related symptoms'],
    'Paediatrics': ['Ear infection', 'Viral rash', 'Common cold', 'Gastroenteritis'],
    'Mental Health': ['Generalised anxiety', 'Mild depression', 'Insomnia', 'Work-related stress'],
    'Respiratory': ['Asthma flare-up', 'Chest infection', 'Bronchitis']
}

medicines_by_specialty = {
    'General Practice': [
        {'medicine': 'Paracetamol', 'dosage': '500mg'},
        {'medicine': 'Ibuprofen', 'dosage': '400mg'},
        {'medicine': 'Amoxicillin', 'dosage': '500mg'}
    ],
    'Dermatology': [
        {'medicine': 'Hydrocortisone cream', 'dosage': '1%'},
        {'medicine': 'Cetirizine', 'dosage': '10mg'},
        {'medicine': 'Emollient cream', 'dosage': 'Apply thinly'}
    ],
    'Cardiology': [
        {'medicine': 'Amlodipine', 'dosage': '5mg'},
        {'medicine': 'Ramipril', 'dosage': '2.5mg'},
        {'medicine': 'Bisoprolol', 'dosage': '2.5mg'}
    ],
    'Paediatrics': [
        {'medicine': 'Calpol (paracetamol)', 'dosage': '120mg/5ml'},
        {'medicine': 'Amoxicillin suspension', 'dosage': '125mg/5ml'},
        {'medicine': 'Oral rehydration salts', 'dosage': '1 sachet'}
    ],
    'Mental Health': [
        {'medicine': 'Sertraline', 'dosage': '50mg'},
        {'medicine': 'Melatonin', 'dosage': '2mg'}
    ],
    'Respiratory': [
        {'medicine': 'Salbutamol inhaler', 'dosage': '100mcg'},
        {'medicine': 'Clarithromycin', 'dosage': '500mg'},
        {'medicine': 'Prednisolone', 'dosage': '5mg'}
    ]
}

frequencies = ['Once daily', 'Twice daily', 'Three times daily', 'When needed']

# feedback comments split by rating
good_comments = ['Quick and helpful', 'Doctor was very kind', 'Easy to use', 'Would use again']
okay_comments = ['Had to wait a long time', 'Helpful but the call felt rushed']
bad_comments = ['Did not feel listened to', 'Had to wait a long time']

conditions = ['Asthma', 'Diabetes', 'High blood pressure', 'Eczema', 'Migraine', 'Anxiety']
allergies_list = ['Penicillin', 'Peanuts', 'Latex', 'Pollen', 'Ibuprofen']

female_names = ['Sarah', 'Aoife', 'Emma', 'Niamh', 'Grace', 'Orla']
male_names = ['James', 'Ciaran', 'Liam', 'Conor', 'Ryan', 'Sean']
first_names = female_names + male_names
last_names = ['Kelly', 'Wilson', 'Murphy', 'Campbell', 'Smith', 'Brown', 'McLaughlin',
              'Doherty', 'Quinn', 'Stewart', 'Moore', 'Walsh', 'Johnston', 'Thompson']

# [longitude, latitude]
cities = {
    'Belfast': [-5.9301, 54.5973],
    'Derry': [-7.3086, 54.9966],
    'Newry': [-6.3374, 54.1751],
    'Armagh': [-6.6547, 54.3503],
    'Lisburn': [-6.0353, 54.5162],
    'Coleraine': [-6.6683, 55.1325],
    'Enniskillen': [-7.6390, 54.3438],
    'Ballymena': [-6.2758, 54.8643]
}

streets = ['Main Street', 'High Street', 'Church Road', 'Station Road', 'Mill Lane']

time_slots = ['09:00', '09:30', '10:00', '10:30', '11:00', '14:00', '14:30', '15:00', '15:30', '16:00']

# ---- doctors ----

doctor_list = []

for i in range(24):
    name = 'Dr ' + random.choice(first_names) + ' ' + random.choice(last_names)
    city = random.choice(list(cities.keys()))
    if i == 1:
        name = 'Dr Aoife Wilson'    # matches the drwilson login

    # move each clinic a bit so they're not all on the same spot
    lng = round(cities[city][0] + random.uniform(-0.04, 0.04), 4)
    lat = round(cities[city][1] + random.uniform(-0.02, 0.02), 4)

    doctor = {
        'doctor_id': 'D' + str(100 + i),
        'name': name,
        'specialty': specialties[i % len(specialties)],
        'gmc_number': str(random.randint(6000000, 7999999)),
        'years_experience': random.randint(2, 30),
        'available_days': random.sample(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'], 3),
        'accepting_patients': random.choice([True, False]),
        'clinic': {
            'name': city + ' Health Centre',
            'city': city,
            'location': {    # GeoJSON for the nearby search
                'type': 'Point',
                'coordinates': [lng, lat]
            }
        }
    }

    doctor_list.append(doctor)

with open('doctors.json', 'w', encoding='utf-8') as fout:
    json.dump(doctor_list, fout, indent=4)

print('Created', len(doctor_list), 'doctors')

# ---- consultations ----

consultation_list = []

for i in range(300):
    chosen_doctor = random.choice(doctor_list)
    gender = random.choice(['Female', 'Male'])
    if gender == 'Female':
        patient_name = random.choice(female_names) + ' ' + random.choice(last_names)
    else:
        patient_name = random.choice(male_names) + ' ' + random.choice(last_names)
    patient_city = random.choice(list(cities.keys()))

    # number added so every email is unique
    email = patient_name.lower().replace(' ', '.') + str(1000 + i) + '@example.com'
    if i == 0:
        patient_name, gender = 'Sarah Smith', 'Female'
        email = 'sarah.smith@example.com'    # matches the sarah login

    # diagnosis year has to be after birth year
    birth_year = random.randint(1950, 2015)
    appointment_type = random.choice(['video', 'video', 'phone'])

    medical_history = []
    for condition in random.sample(conditions, random.randint(0, 2)):
        medical_history.append({
            'condition': condition,
            'diagnosed_year': random.randint(birth_year + 1, 2025)
        })

    # 1-3 symptoms that match the doctor's specialty
    specialty = chosen_doctor['specialty']
    symptoms = []
    for symptom_name in random.sample(symptoms_by_specialty[specialty], random.randint(1, 3)):
        symptoms.append({
            'name': symptom_name,
            'severity': random.randint(1, 10),
            'duration_days': random.randint(1, 21)
        })

    # urgency from the worst symptom
    worst = max(s['severity'] for s in symptoms)
    if worst >= 8:
        urgency = 'high'
    elif worst >= 5:
        urgency = 'medium'
    else:
        urgency = 'low'

    # past dates are completed/cancelled, future ones booked/pending
    appointment_date = date(2026, 1, 5) + timedelta(days=random.randint(0, 345))
    if appointment_date < date(2026, 10, 16):
        status = random.choice(['completed', 'completed', 'completed', 'cancelled'])
    else:
        status = random.choice(['booked', 'pending'])

    # only completed ones have notes, prescriptions and feedback
    consultation_notes = None
    prescriptions = []
    feedback = None

    if status == 'completed':
        follow_up_needed = random.choice([True, False])
        consultation_notes = {
            'diagnosis': random.choice(diagnoses_by_specialty[specialty]),
            'notes': 'Patient assessed remotely. Advice given.',
            'follow_up': {
                'required': follow_up_needed,
                'date': str(appointment_date + timedelta(days=14)) if follow_up_needed else None
            }
        }

        for med in random.sample(medicines_by_specialty[specialty], random.randint(0, 2)):
            prescriptions.append({
                'medicine': med['medicine'],
                'dosage': med['dosage'],
                'frequency': random.choice(frequencies),
                'duration_days': random.choice([5, 7, 14, 28])
            })

        rating = random.randint(1, 5)
        if rating >= 4:
            comment = random.choice(good_comments)
        elif rating == 3:
            comment = random.choice(okay_comments)
        else:
            comment = random.choice(bad_comments)
            if appointment_type == 'video' and random.random() < 0.5:
                comment = 'Video kept freezing'
        feedback = {'rating': rating, 'comment': comment}

    created_date = appointment_date - timedelta(days=random.randint(1, 10))

    consultation = {
        'consultation_id': 'C' + str(1000 + i),
        'patient': {
            'patient_id': 'P' + str(2000 + i),
            'name': patient_name,
            'date_of_birth': f'{birth_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}',
            'gender': gender,
            'contact': {
                'phone': '07700 ' + str(random.randint(900000, 900999)),
                'email': email,
                'address': {
                    'street': str(random.randint(1, 120)) + ' ' + random.choice(streets),
                    'city': patient_city,
                    'postcode': 'BT' + str(random.randint(1, 94)) + ' ' + str(random.randint(1, 9)) + random.choice('ABDEHJLNPRSTUWXYZ') + random.choice('ABDEHJLNPRSTUWXYZ')
                }
            },
            'medical_history': medical_history,
            'allergies': random.sample(allergies_list, random.randint(0, 2))
        },
        'doctor': {    # copy of the doctor's details
            'doctor_id': chosen_doctor['doctor_id'],
            'name': chosen_doctor['name'],
            'specialty': chosen_doctor['specialty'],
            'gmc_number': chosen_doctor['gmc_number']
        },
        'appointment': {
            'date': str(appointment_date),
            'time_slot': random.choice(time_slots),
            'type': appointment_type,
            'video_link': 'https://meet.example.com/c' + str(1000 + i) if appointment_type == 'video' else None,
            'status': status
        },
        'symptoms': symptoms,
        'urgency_level': urgency,
        'consultation_notes': consultation_notes,
        'prescriptions': prescriptions,
        'feedback': feedback,
        'timestamps': {
            'created_at': str(created_date),
            'updated_at': str(appointment_date) if status == 'completed' else str(created_date)
        }
    }

    consultation_list.append(consultation)

with open('consultations.json', 'w', encoding='utf-8') as fout:
    json.dump(consultation_list, fout, indent=4)

print('Created', len(consultation_list), 'consultations')
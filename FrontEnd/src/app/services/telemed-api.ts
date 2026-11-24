import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class TelemedApi {
  // where the Flask API lives (CW1)
  private apiUrl = 'http://localhost:5001/api/v1.0';

  constructor(private http: HttpClient) {}

  // GET /doctors  or  /doctors?specialty=Dermatology
  getDoctors(specialty: string = '') {
    let params = new HttpParams();

    // only send specialty if one was chosen
    if (specialty) {
      params = params.set('specialty', specialty);
    }

    return this.http.get<any[]>(this.apiUrl + '/doctors', { params });
  }

  // GET /consultations?pn=1&ps=5&status=completed&urgency=high
  // needs login - the interceptor adds the token
  getConsultations(page: number, pageSize: number, status: string = '', urgency: string = '') {
    let params = new HttpParams()
      .set('pn', page)
      .set('ps', pageSize);

    if (status) {
      params = params.set('status', status);
    }
    if (urgency) {
      params = params.set('urgency', urgency);
    }

    return this.http.get<any[]>(this.apiUrl + '/consultations', { params });
  }

  // POST /consultations/<id>/symptoms  (patient or admin, needs login)
  // the API reads request.form, so we send FORM DATA, not JSON
  addSymptom(consultationId: string, symptom: any) {
    const formData = new FormData();
    formData.append('name', symptom.name);
    formData.append('severity', String(symptom.severity));
    formData.append('duration_days', String(symptom.duration_days));

    return this.http.post<any>(this.apiUrl + '/consultations/' + consultationId + '/symptoms', formData);
  }

  // POST /consultations - book (patient, needs login, form data like Postman)
  bookConsultation(booking: any) {
    const formData = new FormData();
    for (const key of ['patient_name', 'patient_email', 'doctor_id', 'date', 'time_slot', 'type']) {
      formData.append(key, booking[key]);
    }
    return this.http.post<any>(this.apiUrl + '/consultations', formData);
  }

  // PUT /consultations/<id> - only the fields we send are changed
  // e.g. { date, time_slot, type } to reschedule, or { status: 'cancelled' } to cancel
  updateConsultation(id: string, changes: any) {
    const formData = new FormData();
    for (const key in changes) {
      formData.append(key, changes[key]);
    }
    return this.http.put<any>(this.apiUrl + '/consultations/' + id, formData);
  }

  // DELETE /consultations/<id> - admin only, removes the record for good
  deleteConsultation(id: string) {
    return this.http.delete<any>(this.apiUrl + '/consultations/' + id);
  }

  // GET /doctors/<_id>  - one doctor by their MongoDB id
  getDoctor(id: string) {
    return this.http.get<any>(this.apiUrl + '/doctors/' + id);
  }
}
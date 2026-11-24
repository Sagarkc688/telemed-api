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

  // GET /doctors/<_id>  - one doctor by their MongoDB id
  getDoctor(id: string) {
    return this.http.get<any>(this.apiUrl + '/doctors/' + id);
  }
}
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

  // GET /doctors/<_id>  - one doctor by their MongoDB id
  getDoctor(id: string) {
    return this.http.get<any>(this.apiUrl + '/doctors/' + id);
  }
}
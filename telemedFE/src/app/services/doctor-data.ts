import { Injectable } from '@angular/core';
import jsonData from '../data/doctors.json';

@Injectable({
  providedIn: 'root',
})
export class DoctorData {

  pageSize: number = 8;

  getDoctors(page: number) {
    let pageStart = (page - 1) * this.pageSize;
    let pageEnd = pageStart + this.pageSize;
    return jsonData.slice(pageStart, pageEnd);
  }

  getLastPageNumber() {
    return Math.ceil(jsonData.length / this.pageSize);
  }

}
import { Component } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { switchMap, catchError, of } from 'rxjs';
import { DoctorData } from '../../services/doctor-data';
import { TelemedApi } from '../../services/telemed-api';

@Component({
  selector: 'app-doctor',
  imports: [RouterModule],
  providers: [DoctorData, TelemedApi],
  templateUrl: './doctor.html',
  styleUrl: './doctor.css'
})
export class Doctor {
  doctor: any = null;
  loading: boolean = true;
  notFound: boolean = false;
  errorMessage: string = '';

  initials: string = '';
  weekDays: string[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  mapUrl: SafeResourceUrl | null = null;
  directionsUrl: string = '';

  constructor(protected doctorData: DoctorData,
              private telemedApi: TelemedApi,
              private route: ActivatedRoute,
              private sanitizer: DomSanitizer) {}

  ngOnInit() {
    this.route.paramMap.pipe(
      // new id in the URL -> cancel any old request, fetch this doctor
      switchMap(params => {
        const id = params.get('id') || '';
        this.loading = true;
        this.notFound = false;
        this.errorMessage = '';

        return this.telemedApi.getDoctor(id).pipe(
          catchError(error => {
            // 400 = not a valid MongoDB id, 404 = no doctor with that id
            if (error.status == 400 || error.status == 404) {
              this.notFound = true;
            } else {
              this.errorMessage = "Sorry, we couldn't load this doctor. Please check the API is running.";
            }
            return of(null);
          })
        );
      })
    ).subscribe(doctor => {
      this.doctor = doctor;
      this.loading = false;
      if (doctor) {
        this.initials = this.makeInitials(doctor.name);
        this.makeMap();
      }
    });
  }

  // "Dr Aoife Wilson" -> "AW"
  makeInitials(name: string) {
    return name.replace('Dr ', '')
               .split(' ')
               .map(word => word[0])
               .join('');
  }

  // true if the doctor works on this day
  isAvailable(day: string) {
    return this.doctor.available_days.some(
      (d: string) => d.substring(0, 3).toLowerCase() == day.toLowerCase()
    );
  }

  // Build an OpenStreetMap link from the clinic's GeoJSON [lng, lat]
  makeMap() {
    let lng = this.doctor.clinic.location.coordinates[0];
    let lat = this.doctor.clinic.location.coordinates[1];
    let box = 0.01;

    let url = 'https://www.openstreetmap.org/export/embed.html?bbox='
              + (lng - box) + ',' + (lat - box) + ','
              + (lng + box) + ',' + (lat + box)
              + '&layer=mapnik&marker=' + lat + ',' + lng;

    this.mapUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
    this.directionsUrl = 'https://www.openstreetmap.org/?mlat=' + lat
                         + '&mlon=' + lng + '#map=16/' + lat + '/' + lng;
  }
}
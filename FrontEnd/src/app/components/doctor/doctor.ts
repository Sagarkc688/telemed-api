import { Component } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { DoctorData } from '../../services/doctor-data';

@Component({
  selector: 'app-doctor',
  imports: [RouterModule],
  providers: [DoctorData],
  templateUrl: './doctor.html',
  styleUrl: './doctor.css'
})
export class Doctor {
  doctor: any;
  initials: string = '';
  weekDays: string[] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  mapUrl: SafeResourceUrl | null = null;
  directionsUrl: string = '';

  constructor(protected doctorData: DoctorData,
              private route: ActivatedRoute,
              private sanitizer: DomSanitizer) {}

  ngOnInit() {
    let id = this.route.snapshot.paramMap.get('id') || '';
    this.doctor = this.doctorData.getDoctor(id);

    if (this.doctor) {
      this.initials = this.makeInitials(this.doctor.name);
      this.makeMap();
    }
  }

  // "Dr Aoife Wilson" -> "AW"
  makeInitials(name: string) {
    return name.replace('Dr ', '')
               .split(' ')
               .map(word => word[0])
               .join('');
  }

  // true if the doctor works on this day (works with "Mon" or "Monday")
  isAvailable(day: string) {
    return this.doctor.available_days.some(
      (d: string) => d.substring(0, 3).toLowerCase() == day.toLowerCase()
    );
  }

  // Build an OpenStreetMap link from the clinic's GeoJSON [lng, lat]
  makeMap() {
    let lng = this.doctor.clinic.location.coordinates[0];
    let lat = this.doctor.clinic.location.coordinates[1];
    let box = 0.01;   // how far the map zooms out around the clinic

    let url = 'https://www.openstreetmap.org/export/embed.html?bbox='
              + (lng - box) + ',' + (lat - box) + ','
              + (lng + box) + ',' + (lat + box)
              + '&layer=mapnik&marker=' + lat + ',' + lng;

    this.mapUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
    this.directionsUrl = 'https://www.openstreetmap.org/?mlat=' + lat
                         + '&mlon=' + lng + '#map=16/' + lat + '/' + lng;
  }
}
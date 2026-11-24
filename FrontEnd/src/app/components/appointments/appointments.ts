import { Component } from '@angular/core';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { DatePipe, TitleCasePipe } from '@angular/common';
import { switchMap, catchError, of } from 'rxjs';
import { TelemedApi } from '../../services/telemed-api';
import { Auth } from '../../services/auth';

@Component({
  selector: 'app-appointments',
  imports: [RouterModule, DatePipe, TitleCasePipe],
  templateUrl: './appointments.html',
  styleUrl: './appointments.css'
})
export class Appointments {
  appointments: any[] = [];
  page: number = 1;
  pageSize: number = 5;
  status: string = '';
  urgency: string = '';

  loading: boolean = true;
  errorMessage: string = '';
  openId: string | null = null;     // which appointment is expanded

  statuses = ['pending', 'booked', 'completed', 'cancelled'];
  urgencies = ['low', 'medium', 'high'];

  constructor(private telemedApi: TelemedApi,
              private route: ActivatedRoute,
              private router: Router,
              protected auth: Auth) {}

  ngOnInit() {
    // the page number and filters live in OUR url too: /appointments?page=2&status=completed
    this.route.queryParamMap.pipe(
      switchMap(params => {
        this.page = Math.max(Number(params.get('page')) || 1, 1);
        this.status = params.get('status') || '';
        this.urgency = params.get('urgency') || '';
        this.loading = true;
        this.errorMessage = '';
        this.openId = null;

        return this.telemedApi.getConsultations(this.page, this.pageSize, this.status, this.urgency).pipe(
          catchError(error => {
            // 401 is handled by the interceptor (sends you to log in)
            if (error.status != 401) {
              this.errorMessage = "Sorry, we couldn't load the appointments. Please try again.";
            }
            return of([]);
          })
        );
      })
    ).subscribe(data => {
      this.appointments = data;
      this.loading = false;
    });
  }

  // heading depends on who is logged in
  heading() {
    const role = this.auth.user()?.role;
    if (role == 'doctor') return "My patients' appointments";
    if (role == 'admin') return 'All appointments';
    return 'My appointments';
  }

  // change the page/filters by changing the URL - so Back button and bookmarks work
  updateUrl(changes: any) {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: changes,
      queryParamsHandling: 'merge'      // keep the other params
    });
  }

  setStatus(value: string) {
    this.updateUrl({ status: value || null, page: 1 });   // null removes it from the URL
  }

  setUrgency(value: string) {
    this.updateUrl({ urgency: value || null, page: 1 });
  }

  clearFilters() {
    this.updateUrl({ status: null, urgency: null, page: 1 });
  }

  previousPage() {
    if (this.page > 1) {
      this.updateUrl({ page: this.page - 1 });
    }
  }

  nextPage() {
    if (this.hasNextPage()) {
      this.updateUrl({ page: this.page + 1 });
    }
  }

  // the API doesn't send a total, so: a FULL page means there might be more
  hasNextPage() {
    return this.appointments.length == this.pageSize;
  }

  toggle(id: string) {
    this.openId = this.openId == id ? null : id;
  }

  // 4 -> "★★★★☆"
  stars(rating: number) {
    return '★'.repeat(rating) + '☆'.repeat(5 - rating);
  }
}
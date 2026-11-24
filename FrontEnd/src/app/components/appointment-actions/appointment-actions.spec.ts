import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AppointmentActions } from './appointment-actions';

describe('AppointmentActions', () => {
  let component: AppointmentActions;
  let fixture: ComponentFixture<AppointmentActions>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppointmentActions]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AppointmentActions);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

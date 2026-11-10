import { TestBed } from '@angular/core/testing';

import { DoctorData } from './doctor-data';

describe('DoctorData', () => {
  let service: DoctorData;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DoctorData);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});

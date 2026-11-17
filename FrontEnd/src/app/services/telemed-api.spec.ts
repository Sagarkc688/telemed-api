import { TestBed } from '@angular/core/testing';

import { TelemedApi } from './telemed-api';

describe('TelemedApi', () => {
  let service: TelemedApi;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TelemedApi);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});

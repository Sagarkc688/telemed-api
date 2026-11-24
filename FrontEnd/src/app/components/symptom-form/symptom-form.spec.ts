import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SymptomForm } from './symptom-form';

describe('SymptomForm', () => {
  let component: SymptomForm;
  let fixture: ComponentFixture<SymptomForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SymptomForm]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SymptomForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

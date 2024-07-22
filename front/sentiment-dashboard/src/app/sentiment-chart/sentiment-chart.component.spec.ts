import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SentimentChartComponent } from './sentiment-chart.component';

describe('SentimentChartComponent', () => {
  let component: SentimentChartComponent;
  let fixture: ComponentFixture<SentimentChartComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SentimentChartComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(SentimentChartComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

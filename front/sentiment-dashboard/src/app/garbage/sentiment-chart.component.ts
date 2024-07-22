// import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
// import { isPlatformBrowser } from '@angular/common';
// import { HttpClient } from '@angular/common/http';
// import { Chart, ChartItem, registerables, TooltipItem as ChartJSTooltipItem } from 'chart.js';
// import 'chartjs-adapter-date-fns';
// import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
// import { MatDatepickerModule } from '@angular/material/datepicker';
// import { MatFormFieldModule } from '@angular/material/form-field';
// import { MatInputModule } from '@angular/material/input';
// import { MatCheckboxModule } from '@angular/material/checkbox';
// import { MatNativeDateModule } from '@angular/material/core';
// import { MatDialog, MatDialogModule } from '@angular/material/dialog';
// import { SentimentDialogComponent } from './sentiment-dialog.component';
//
// Chart.register(...registerables);
//
// @Component({
//   selector: 'app-sentiment-chart',
//   templateUrl: './sentiment-chart.component.html',
//   styleUrls: ['./sentiment-chart.component.css'],
//   standalone: true,
//   imports: [
//     ReactiveFormsModule,
//     MatDatepickerModule,
//     MatFormFieldModule,
//     MatInputModule,
//     MatCheckboxModule,
//     MatNativeDateModule,
//     MatDialogModule
//   ]
// })
// export class SentimentChartComponent implements OnInit {
//   chart: Chart | undefined;
//   dateForm: FormGroup;
//   fullData: any[] = [];
//
//   constructor(private http: HttpClient, private fb: FormBuilder, @Inject(PLATFORM_ID) private platformId: Object, private dialog: MatDialog) {
//     this.dateForm = this.fb.group({
//       startDate: [null],
//       endDate: [null],
//       scaleByRelevance: [false],
//       scaleCircleByRelevance: [true],
//       relevanceScore: [0] // Add relevanceScore field
//     });
//
//     this.dateForm.get('scaleByRelevance')?.valueChanges.subscribe(() => {
//       this.updateChart();
//     });
//
//     this.dateForm.get('scaleCircleByRelevance')?.valueChanges.subscribe(() => {
//       this.updateChart();
//     });
//   }
//
//   ngOnInit(): void {
//     console.log('SentimentChartComponent initialized');
//     this.loadData();
//   }
//
//   loadData(startDate?: string, endDate?: string): void {
//     const relevanceScore = this.dateForm.get('relevanceScore')?.value || 0;
//     const apiUrl = `http://localhost:5000/api/sentiment?ticker=AAPL&start_date=${startDate || '2023-01-01'}&end_date=${endDate || '2024-08-01'}&relevance_score=${relevanceScore}`;
//     console.log('Fetching data from API:', apiUrl);
//
//     this.http.get<any[]>(apiUrl).subscribe({
//       next: data => {
//         console.log('API data received:', data);
//         this.fullData = data;
//         this.updateChart();
//       },
//       error: error => {
//         console.error('API request error:', error);
//       },
//       complete: () => {
//         console.log('API request completed');
//       }
//     });
//   }
//
//   updateChart(): void {
//     if (!isPlatformBrowser(this.platformId)) {
//       console.log("This is running on the server or other non-browser environment");
//       return;
//     }
//
//     const canvas = document.getElementById('sentimentChart') as HTMLCanvasElement;
//     const ctx = canvas.getContext('2d');
//     if (!ctx) {
//       console.error('Failed to get context');
//       return;
//     }
//
//     const dates = this.fullData.map(d => new Date(d.time_published));
//     const relevance = this.fullData.map(d => parseFloat(d.relevance_score));
//     let scores = this.fullData.map(d => parseFloat(d.sentiment_score));
//     const scaleByRelevance = this.dateForm.get('scaleByRelevance')?.value;
//     const scaleCircleByRelevance = this.dateForm.get('scaleCircleByRelevance')?.value;
//
//     if (scaleByRelevance) {
//       scores = scores.map((score, index) => score * relevance[index]);
//     }
//
//     if (this.chart) {
//       this.chart.destroy();
//     }
//
//     this.chart = new Chart(ctx as ChartItem, {
//       type: 'line',
//       data: {
//         labels: dates,
//         datasets: [{
//           label: 'Sentiment Score',
//           data: scores,
//           borderColor: 'rgb(75, 192, 192)',
//           backgroundColor: 'rgba(75, 192, 192, 0.5)',
//           pointRadius: scaleCircleByRelevance ? relevance.map(r => r * 10) : 5,
//         }]
//       },
//       options: {
//         responsive: true,
//         maintainAspectRatio: false,
//         scales: {
//           x: {
//             type: 'time',
//             time: {
//               unit: 'day'
//             }
//           },
//           y: {
//             beginAtZero: true
//           }
//         },
//         plugins: {
//           tooltip: {
//             callbacks: {
//               label: (context: ChartJSTooltipItem<'line'>) => {
//                 const index = context.dataIndex;
//                 const dataPoint = this.fullData[index];
//                 const numOfRelatedTickers = dataPoint.json_data.length;
//
//                 return [
//                   `URL: ${dataPoint.url}`,
//                   `Date: ${dataPoint.time_published}`,
//                   `Score: ${dataPoint.sentiment_score}`,
//                   `Relevance: ${dataPoint.relevance_score}`,
//                   `Title: ${dataPoint.title}`,
//                   `Summary: ${dataPoint.summary}`,
//                   `Number of Related Tickers: ${numOfRelatedTickers}`,
//                   `Ticker Sentiment:\n${dataPoint.json_data.map((item: any) =>
//                     `Ticker: ${item.ticker}, Score: ${item.ticker_sentiment_score}, Label: ${item.ticker_sentiment_label}`).join('\n')}`
//                 ];
//               }
//             }
//           }
//         }
//       }
//     });
//
//     canvas.onclick = (event) => {
//       const points = this.chart?.getElementsAtEventForMode(event, 'nearest', { intersect: true }, false);
//       if (points?.length) {
//         const firstPoint = points[0];
//         const data = this.fullData[firstPoint.index];
//         this.openDialog(data);
//       }
//     };
//
//     console.log('Chart updated successfully');
//   }
//
//   onSubmit(): void {
//     const startDate = this.dateForm.get('startDate')?.value;
//     const endDate = this.dateForm.get('endDate')?.value;
//     this.loadData(startDate?.toISOString().split('T')[0], endDate?.toISOString().split('T')[0]);
//   }
//
//   openDialog(data: any): void {
//     this.dialog.open(SentimentDialogComponent, {
//       data: data
//     });
//   }
//
//   endDateFilter = (date: Date | null): boolean => {
//     const startDate = this.dateForm.get('startDate')?.value;
//     if (!date || !startDate) {
//       return true;
//     }
//     return date >= startDate;
//   }
// }

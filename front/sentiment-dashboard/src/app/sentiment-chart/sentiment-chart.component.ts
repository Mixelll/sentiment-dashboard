import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Chart, ChartItem, registerables, TooltipItem as ChartJSTooltipItem, Point } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormArray } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { SentimentDialogComponent } from './sentiment-dialog.component';
import chroma from 'chroma-js';
import { format } from 'date-fns';

Chart.register(...registerables);

interface SentimentData {
  time_published: string;
  relevance_score: string;
  sentiment_score: string;
  title: string;
  summary: string;
  url: string;
  json_data: Array<{ ticker: string; relevance_score: string; ticker_sentiment_score: string; ticker_sentiment_label: string }>;
}

@Component({
  selector: 'app-sentiment-chart',
  templateUrl: './sentiment-chart.component.html',
  styleUrls: ['./sentiment-chart.component.css'],
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatNativeDateModule,
    MatDialogModule,
    MatSelectModule,
    MatIconModule
  ]
})
export class SentimentChartComponent implements OnInit {
  chart: Chart | undefined;
  dateForm: FormGroup;
  tickersList: string[] = [];
  fullData: { [ticker: string]: SentimentData[] } = {};
  colorMap: { [ticker: string]: string } = {};
  loadingTickers: Set<string> = new Set();
  fetchedTickers: Set<string> = new Set(); // Declaration for tracking fetched tickers

  constructor(private http: HttpClient, private fb: FormBuilder, @Inject(PLATFORM_ID) private platformId: Object, private dialog: MatDialog) {
    this.dateForm = this.fb.group({
      tickerInput: [''],
      startDate: [null],
      endDate: [null],
      scaleByRelevance: [false],
      scaleCircleByRelevance: [true],
      relevanceScore: [0],
      plotLines: [false] // Add plotLines checkbox
    });

    this.dateForm.get('scaleByRelevance')?.valueChanges.subscribe(() => {
      this.updateChart();
    });

    this.dateForm.get('scaleCircleByRelevance')?.valueChanges.subscribe(() => {
      this.updateChart();
    });

    this.dateForm.get('plotLines')?.valueChanges.subscribe(() => {
      this.updateChart();
    });
  }

  ngOnInit(): void {
    console.log('SentimentChartComponent initialized');
    this.addTicker(); // Initialize with one ticker input
  }

  addTicker(): void {
    const ticker = this.dateForm.get('tickerInput')?.value.trim();
    if (ticker && !this.tickersList.includes(ticker)) {
      this.tickersList.push(ticker);
      this.dateForm.get('tickerInput')?.reset();
      this.assignColorToTicker(ticker);
      if (!this.fetchedTickers.has(ticker)) {
        this.loadData(ticker);
      }
    }
  }

  removeTicker(index: number): void {
    const ticker = this.tickersList[index];
    this.tickersList.splice(index, 1);
    delete this.fullData[ticker];
    this.fetchedTickers.delete(ticker);
    this.updateChart();
  }

  assignColorToTicker(ticker: string): void {
    if (!this.colorMap[ticker]) {
      const colors: string[] = chroma.scale('Set1').mode('lab').colors(10);
      const usedColors = Object.values(this.colorMap);
      const availableColors = colors.filter(color => !usedColors.includes(color));
      this.colorMap[ticker] = availableColors.length > 0 ? availableColors[0] : chroma.random().hex();
    }
  }

  loadData(ticker: string): void {
    if (!ticker || this.fetchedTickers.has(ticker)) return; // Prevent reloading data for already fetched tickers

    const tickers = this.tickersList.filter(ticker => ticker.trim() !== '');
    const startDate = format(this.dateForm.get('startDate')?.value ?? new Date('2023-01-01'), 'yyyy-MM-dd');
    const endDate = format(this.dateForm.get('endDate')?.value ?? new Date('2024-08-01'), 'yyyy-MM-dd');
    const relevanceScore = this.dateForm.get('relevanceScore')?.value || 0;

    tickers.forEach((ticker: string) => {
      if (this.fetchedTickers.has(ticker)) {
        return;
      }

      this.fetchedTickers.add(ticker);
      const apiUrl = `http://localhost:5000/api/sentiment?ticker=${ticker}&start_date=${startDate}&end_date=${endDate}&relevance_score=${relevanceScore}`;
      console.log('Fetching data from API:', apiUrl);

      this.http.get<SentimentData[]>(apiUrl).subscribe({
        next: (data: SentimentData[]) => {
          console.log('API data received for', ticker, ':', data);
          this.fullData[ticker] = data;
          this.updateChart();
        },
        error: error => {
          console.error('API request error for', ticker, ':', error);
          this.removeTickerByName(ticker); // Remove from list if error
          alert(`Error fetching data for ticker: ${ticker}. It will be removed.`);
        },
        complete: () => {
          console.log('API request completed for', ticker);
          this.loadingTickers.delete(ticker);
        }
      });
    });
  }

  removeTickerByName(ticker: string): void {
    const index = this.tickersList.indexOf(ticker);
    if (index !== -1) {
      this.tickersList.splice(index, 1);
      delete this.fullData[ticker];
      this.fetchedTickers.delete(ticker);
      this.updateChart();
    }
  }

  updateChart(): void {
    if (!isPlatformBrowser(this.platformId)) {
      console.log("This is running on the server or other non-browser environment");
      return;
    }
    const canvas = document.getElementById('sentimentChart') as HTMLCanvasElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      console.error('Failed to get context');
      return;
    }

    const plotLines = this.dateForm.get('plotLines')?.value;

    const datasets = Object.keys(this.fullData).map((ticker) => {
      const dataPoints = this.fullData[ticker];
      const dates: Point[] = dataPoints.map((d: SentimentData) => ({ x: new Date(d.time_published).getTime(), y: parseFloat(d.sentiment_score) }));
      const relevance = dataPoints.map((d: SentimentData) => parseFloat(d.relevance_score));
      const scaleByRelevance = this.dateForm.get('scaleByRelevance')?.value;
      const scaleCircleByRelevance = this.dateForm.get('scaleCircleByRelevance')?.value;

      const scores = scaleByRelevance
        ? dataPoints.map((d, index) => ({ x: new Date(d.time_published).getTime(), y: parseFloat(d.sentiment_score) * relevance[index] }))
        : dates;

      const color = this.colorMap[ticker];

      return {
        label: `${ticker} Sentiment Score`,
        data: scores,
        borderColor: plotLines ? color : 'rgba(0,0,0,0)',
        backgroundColor: color,
        pointRadius: scaleCircleByRelevance ? relevance.map(r => r * 10) : 5,
        pointBorderColor: 'black', // Outline color
        pointBackgroundColor: color, // Dot color
        hidden: this.chart ? this.chart.getDatasetMeta(this.chart.data.datasets.findIndex(ds => ds.label === `${ticker} Sentiment Score`))?.hidden : false
      };
    });

    if (this.chart) {
      this.chart.destroy();
    }

    this.chart = new Chart(ctx as ChartItem, {
      type: 'line',
      data: {
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day'
            }
          },
          y: {
            beginAtZero: true
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (context: ChartJSTooltipItem<'line'>) => {
                const datasetLabel = context.dataset.label || '';
                const ticker = datasetLabel.split(' ')[0];
                const dataPoints = this.fullData[ticker];

                if (dataPoints) {
                  const dataPoint = dataPoints[context.dataIndex];
                  const numOfRelatedTickers = dataPoint.json_data.length;

                  return [
                    `URL: ${dataPoint.url}`,
                    `Date: ${dataPoint.time_published}`,
                    `Score: ${dataPoint.sentiment_score}`,
                    `Relevance: ${dataPoint.relevance_score}`,
                    `Title: ${dataPoint.title}`,
                    `Summary: ${dataPoint.summary}`,
                    `Number of Related Tickers: ${numOfRelatedTickers}`,
                    `Ticker Sentiment:\n${dataPoint.json_data.map((item: any) =>
                      `Ticker: ${item.ticker}, Relevance Score: ${item.relevance_score}, Score: ${item.ticker_sentiment_score}, Label: ${item.ticker_sentiment_label}`).join('\n')}`
                  ];
                }

                return [];
              }
            }
          }
        }
      }
    });

    canvas.onclick = (event) => {
      const points = this.chart?.getElementsAtEventForMode(event, 'nearest', { intersect: true }, false);
      if (points?.length) {
        const firstPoint = points[0];
        const datasetIndex = firstPoint.datasetIndex;
        const index = firstPoint.index;
        const datasetLabel = this.chart?.data.datasets[datasetIndex].label || '';
        const ticker = datasetLabel.split(' ')[0];
        const dataPoints = this.fullData[ticker];

        if (dataPoints) {
          const data = dataPoints[index];
          this.openDialog(data);
        }
      }
    };

    console.log('Chart updated successfully');
  }

  onSubmit(): void {
    // Refresh all tickers data logic here
    console.log('Form submitted:', this.dateForm.value);
    this.fetchedTickers.clear(); // Optional: Clear the fetched tickers set to force refreshing all data
    this.tickersList.forEach(ticker => this.loadData(ticker));
  }

  openDialog(data: any): void {
    this.dialog.open(SentimentDialogComponent, {
      data: data
    });
  }

  endDateFilter = (date: Date | null): boolean => {
    const startDate = this.dateForm.get('startDate')?.value;
    if (!date || !startDate) {
      return true;
    }
    return date >= startDate;
  }
}

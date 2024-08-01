import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Chart, ChartItem, registerables, TooltipItem as ChartJSTooltipItem, Point } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { FormBuilder, FormGroup, ReactiveFormsModule, FormArray, FormControl } from '@angular/forms';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatNativeDateModule } from '@angular/material/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';  // Import MatTooltipModule
import { SentimentDialogComponent } from './sentiment-dialog.component';
import chroma from 'chroma-js';
import { format, parse } from 'date-fns';
import { environment } from '../../environments/environment'; // Import environment

Chart.register(...registerables);

interface SentimentData {
  time_published: string;
  relevance_score: string;
  sentiment_score: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  tickers_json: Array<{ ticker: string; relevance_score: string; ticker_sentiment_score: string; ticker_sentiment_label: string }>;
  topics_json: Array<{ topic: string; relevance_score: string}>;
}

@Component({
  selector: 'app-sentiment-chart',
  templateUrl: './sentiment-chart.component.html',
  styleUrls: ['./sentiment-chart.component.css'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatNativeDateModule,
    MatDialogModule,
    MatSelectModule,
    MatIconModule,
    MatTooltipModule  // Add MatTooltipModule to imports
  ]
})
export class SentimentChartComponent implements OnInit {
  chart: Chart | undefined;
  dateForm: FormGroup;
  tickersList: string[] = [];
  fullData: { [ticker: string]: SentimentData[] } = {};
  colorMap: { [ticker: string]: string } = {};
  loadingTickers: Set<string> = new Set();
  fetchedTickers: Set<string> = new Set();
  sourcesList: string[] = []; // List of unique sources
  topicsList: string[] = []; // List of unique topics
  sourcesForm: FormGroup; // FormGroup for sources
  topicsForm: FormGroup; // FormGroup for topics
  selectedSourcesControl: FormControl; // FormControl for selected sources
  selectedTopicsControl: FormControl; // FormControl for selected topics
  topicRelevanceScoreControl: FormControl; // FormControl for topic relevance score

  lastStartDate: string | null = null;
  lastEndDate: string | null = null;
  lastRelevanceScore: number | null = null;

  constructor(private http: HttpClient, private fb: FormBuilder, @Inject(PLATFORM_ID) private platformId: Object, private dialog: MatDialog) {
    this.dateForm = this.fb.group({
      tickerInput: [''],
      startDate: [null],
      endDate: [null],
      scaleByRelevance: [false],
      scaleCircleByRelevance: [true],
      relevanceScore: [0],
      plotLines: [false]
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

    this.sourcesForm = this.fb.group({
      sources: this.fb.array([])
    });

    this.topicsForm = this.fb.group({
      topics: this.fb.array([])
    });

    this.selectedSourcesControl = new FormControl([]);
    this.selectedTopicsControl = new FormControl([]);
    this.topicRelevanceScoreControl = new FormControl(0);
  }

  ngOnInit(): void {
    console.log('SentimentChartComponent initialized');
    this.initializeDefaultValues(); // Initialize with default values
  }

  get sourcesArray(): FormArray {
    return this.sourcesForm.get('sources') as FormArray;
  }

  get topicsArray(): FormArray {
    return this.topicsForm.get('topics') as FormArray;
  }

  initializeDefaultValues(): void {
    this.dateForm.patchValue({
      tickerInput: 'AAPL',
      startDate: parse('2024-01-01', 'yyyy-MM-dd', new Date())
    });
    this.addTicker();
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
      const colors: string[] = chroma.scale(['#1f77b4', '#2ca02c', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'])
        .colors(8); // Custom color palette excluding red and yellow
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
      const apiUrl = `${environment.apiUrl}/sentiment?ticker=${ticker}&start_date=${startDate}&end_date=${endDate}&relevance_score=${relevanceScore}`; // Use environment.apiUrl
      console.log('API URL:', environment.apiUrl); // Log API URL
      console.log('Fetching data from API:', apiUrl);

      this.http.get<SentimentData[]>(apiUrl).subscribe({
        next: (data: SentimentData[]) => {
          console.log('API data received for', ticker, ':', data);
          this.fullData[ticker] = data;
          this.extractSources(data); // Extract unique sources
          this.extractTopics(data); // Extract unique topics
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

  extractSources(data: SentimentData[]): void {
    const sources = data.map(d => d.source);
    const uniqueSources = Array.from(new Set(sources)).sort(); // Sort the sources alphabetically
    uniqueSources.forEach(source => {
      if (!this.sourcesList.includes(source)) {
        this.sourcesList.push(source);
        this.sourcesArray.push(this.fb.control(false));
      }
    });
  }

  extractTopics(data: SentimentData[]): void {
    const topics = data.flatMap(d => d.topics_json.map(t => t.topic));
    const uniqueTopics = Array.from(new Set(topics)).sort(); // Sort the topics alphabetically
    uniqueTopics.forEach(topic => {
      if (!this.topicsList.includes(topic)) {
        this.topicsList.push(topic);
        this.topicsArray.push(this.fb.control(false));
      }
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

  const selectedSources = this.selectedSourcesControl.value;
  const selectedTopics = this.selectedTopicsControl.value;
  const topicRelevanceThreshold = this.topicRelevanceScoreControl.value;

  const plotLines = this.dateForm.get('plotLines')?.value;

  // Create a mapping from the filtered data points to the original data points
  const dataPointMapping: { [key: string]: SentimentData[] } = {};

  const datasets = Object.keys(this.fullData).map((ticker) => {
    const dataPoints = this.fullData[ticker];

    const filteredDataPoints = dataPoints.filter(d => {
      const sourceMatch = selectedSources.length === 0 || selectedSources.includes(d.source);
      const topicMatch = selectedTopics.length === 0 || d.topics_json.some(t => selectedTopics.includes(t.topic) && parseFloat(t.relevance_score) >= topicRelevanceThreshold);
      return sourceMatch && topicMatch;
    });

    // Store the mapping
    dataPointMapping[ticker] = filteredDataPoints;

    const dates: Point[] = filteredDataPoints.map((d: SentimentData) => ({ x: new Date(d.time_published).getTime(), y: parseFloat(d.sentiment_score) }));
    const relevance = filteredDataPoints.map((d: SentimentData) => parseFloat(d.relevance_score));
    const scaleByRelevance = this.dateForm.get('scaleByRelevance')?.value;
    const scaleCircleByRelevance = this.dateForm.get('scaleCircleByRelevance')?.value;

    const scores = scaleByRelevance
      ? filteredDataPoints.map((d, index) => ({ x: new Date(d.time_published).getTime(), y: parseFloat(d.sentiment_score) * relevance[index] }))
      : dates;
    const color = this.colorMap[ticker];

    return {
      label: `${ticker} Sentiment Score`,
      data: scores,
      borderColor: plotLines ? color : 'rgba(0,0,0,0)',
      backgroundColor: color,
      pointRadius: scaleCircleByRelevance ? relevance.map(r => r * 10) : 5,
      pointBorderColor: 'black', // Outline color
      pointBackgroundColor: color // Dot color
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
      maintainAspectRatio: false, // Change this to true to fit the chart to the screen
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'day'
          },
          ticks: {
            font: {
              size: 20, // Increase this value to make the font larger
              weight: 'bold'
            }
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            font: {
              size: 23, // Increase this value to make the font larger
              weight: 'bold'
            }
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (context: ChartJSTooltipItem<'line'>) => {
              const datasetLabel = context.dataset.label || '';
              const ticker = datasetLabel.split(' ')[0];
              const dataPoints = dataPointMapping[ticker];

              if (dataPoints) {
                const dataPoint = dataPoints[context.dataIndex];
                const numOfRelatedTickers = dataPoint.tickers_json.length;
                const numOfTopics = dataPoint.topics_json.length;

                return [
                  `URL: ${dataPoint.url}`,
                  `Source: ${dataPoint.source}`,
                  `Date: ${dataPoint.time_published}`,
                  `Score: ${parseFloat(dataPoint.sentiment_score).toFixed(2)}`,
                  `Relevance: ${parseFloat(dataPoint.relevance_score).toFixed(2)}`,
                  `Title: ${dataPoint.title}`,
                  `Summary: ${dataPoint.summary}`,
                  `Number of Related Tickers: ${numOfRelatedTickers}`,
                  `Ticker Sentiment:\n${dataPoint.tickers_json.map((item: any) =>
                    `Ticker: ${item.ticker}, Relevance Score: ${parseFloat(item.relevance_score).toFixed(2)}, Score: ${parseFloat(item.ticker_sentiment_score).toFixed(2)}, Label: ${item.ticker_sentiment_label}`).join('\n')}`,
                  `Number of Associated Topics: ${numOfTopics}`,
                  `Topic Relevance:\n${dataPoint.topics_json.map((item: any) => `${item.topic}: ${parseFloat(item.relevance_score).toFixed(2)}`).join('\n')}`
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
      const dataPoints = dataPointMapping[ticker];

      if (dataPoints) {
        const data = dataPoints[index];
        this.openDialog(data);
      }
    }
  };

  console.log('Chart updated successfully');
}


  onSubmit(): void {
    console.log('Form submitted:', this.dateForm.value);
    const currentStartDate = format(this.dateForm.get('startDate')?.value ?? new Date('2024-01-01'), 'yyyy-MM-dd');
    const currentEndDate = format(this.dateForm.get('endDate')?.value ?? new Date('2024-08-01'), 'yyyy-MM-dd');
    const currentRelevanceScore = this.dateForm.get('relevanceScore')?.value || 0;

    // Check if the new date range is outside the last fetched date range
    const isOutsideFetchedRange =
      !this.lastStartDate ||
      !this.lastEndDate ||
      currentStartDate < this.lastStartDate ||
      currentEndDate > this.lastEndDate;

    // Refresh data if the new date range is outside the last fetched date range
    if (isOutsideFetchedRange || this.lastRelevanceScore !== currentRelevanceScore) {
      this.fetchedTickers.clear(); // Clear the fetched tickers set to force refreshing all data
      this.tickersList.forEach(ticker => this.loadData(ticker));
      this.lastStartDate = currentStartDate;
      this.lastEndDate = currentEndDate;
      this.lastRelevanceScore = currentRelevanceScore;
    } else {
      // If no need to refresh data, just update the chart
      this.updateChart();
    }
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

  getSelectedSourcesTooltip(): string {
    return this.selectedSourcesControl.value.join(', ') || 'None';
  }

  getSelectedTopicsTooltip(): string {
    return this.selectedTopicsControl.value.join(', ') || 'None';
  }
}

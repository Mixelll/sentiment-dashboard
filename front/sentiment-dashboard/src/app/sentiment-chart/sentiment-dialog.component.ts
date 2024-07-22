import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-sentiment-dialog',
  template: `
    <h2 mat-dialog-title>Details</h2>
    <mat-dialog-content>
      <p><strong>URL:</strong> <a href="{{ data.url }}" target="_blank">{{ data.url }}</a></p>
      <p><strong>Date:</strong> {{ data.time_published }}</p>
      <p><strong>Score:</strong> {{ data.sentiment_score }}</p>
      <p><strong>Relevance:</strong> {{ data.relevance_score }}</p>
      <p><strong>Title:</strong> {{ data.title }}</p>
      <p><strong>Summary:</strong> {{ data.summary }}</p>
      <p><strong>Number of Related Tickers:</strong> {{ data.json_data.length }}</p>
      <p><strong>Ticker Sentiment:</strong></p>
      <pre>{{ formatJsonData(data.json_data) }}</pre>
    </mat-dialog-content>
    <mat-dialog-actions>
      <button mat-button mat-dialog-close>Close</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
    .summary {
      white-space: pre-wrap; /* Ensures wrapping */
      word-wrap: break-word; /* Ensures wrapping */
      display: block;
      overflow-wrap: break-word; /* For better word wrapping */
    }
    pre {
      white-space: pre-wrap; /* Ensures wrapping */
      word-wrap: break-word; /* Ensures wrapping */
    }
    `
  ],
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule
  ]
})
export class SentimentDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: any) {}

  formatJsonData(jsonData: any[]): string {
    return jsonData.map(item =>
      `Ticker: ${item.ticker}, Relevance Score: ${item.relevance_score}, Score: ${item.ticker_sentiment_score}, Label: ${item.ticker_sentiment_label}`
    ).join('\n');
  }
}

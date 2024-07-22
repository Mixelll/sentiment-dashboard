import { Component } from '@angular/core';
import {} from '@angular/common/http';
import { RouterOutlet } from '@angular/router';
import { SentimentChartComponent } from './sentiment-chart/sentiment-chart.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [

// TODO: `HttpClientModule` should not be imported into a component directly.
// Please refactor the code to add `provideHttpClient()` call to the provider list in the
// application bootstrap logic and remove the `HttpClientModule` import from this component.
  // Include HttpClientModule if making HTTP requests
    RouterOutlet,
    SentimentChartComponent  // Only include if SentimentChartComponent is standalone too
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'sentiment-dashboard';
}


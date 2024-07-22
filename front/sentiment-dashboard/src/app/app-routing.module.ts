import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { SentimentChartComponent } from './sentiment-chart/sentiment-chart.component'; // Ensure the path is correct

const routes: Routes = [
  { path: '', component: SentimentChartComponent }, // Default route
  // Add more routes as needed
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }

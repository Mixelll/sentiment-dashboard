import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ReactiveFormsModule } from '@angular/forms';
import { MatMomentDateModule, MAT_MOMENT_DATE_ADAPTER_OPTIONS } from '@angular/material-moment-adapter';
import { MatNativeDateModule, NativeDateAdapter, DateAdapter, MAT_DATE_FORMATS, MAT_DATE_LOCALE } from '@angular/material/core';
import { AppRoutingModule } from './app-routing.module';
import { MatDateFnsModule } from '@angular/material-date-fns-adapter';


@NgModule({
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    // MatMomentDateModule,
    // MatNativeDateModule, // Ensure this is imported
    AppRoutingModule,
    MatDateFnsModule
  ],
  providers: [
    { provide: DateAdapter, useClass: MatDateFnsModule  },
    { provide: MAT_DATE_LOCALE, useValue: 'en-US' },
    // { provide: MAT_MOMENT_DATE_ADAPTER_OPTIONS, useValue: { useUtc: true } },
  ],
})
export class AppModule { }




// import { NgModule } from '@angular/core';
// import { BrowserModule } from '@angular/platform-browser';
// import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
// import { MatDatepickerModule } from '@angular/material/datepicker';
// import { MatFormFieldModule } from '@angular/material/form-field';
// import { MatInputModule } from '@angular/material/input';
// import { ReactiveFormsModule } from '@angular/forms';
// import { MatNativeDateModule, NativeDateAdapter, DateAdapter, MAT_DATE_FORMATS, MAT_DATE_LOCALE } from '@angular/material/core';
// import { AppRoutingModule } from './app-routing.module'; // Ensure this path is correct
// // import { AppComponent } from './app.component'; // Ensure this path is correct
//
// @NgModule({
//   imports: [
//     BrowserModule,
//     BrowserAnimationsModule,
//     MatDatepickerModule,
//     MatFormFieldModule,
//     MatInputModule,
//     ReactiveFormsModule,
//     MatNativeDateModule, // Import MatNativeDateModule
//     AppRoutingModule,
//   ],
//   providers: [
//     { provide: DateAdapter, useClass: NativeDateAdapter }, // Provide the NativeDateAdapter
//     { provide: MAT_DATE_LOCALE, useValue: 'en-US' },
//     { provide: MAT_DATE_FORMATS, useValue: {} }, // Optionally, provide custom date formats
//   ]
// })
// export class AppModule { }






// import { NgModule } from '@angular/core';
// import { BrowserModule } from '@angular/platform-browser';
// import { AppComponent } from './app.component';
// import { SentimentChartComponent } from './sentiment-chart/sentiment-chart.component';
//
// @NgModule({
//   declarations: [
//     AppComponent,
//     SentimentChartComponent
//   ],
//   imports: [
//     BrowserModule
//   ],
//   bootstrap: [AppComponent]
// })
// export class AppModule { }

// import { NgModule } from '@angular/core';
// import { BrowserModule, provideClientHydration } from '@angular/platform-browser';
// import { AppRoutingModule } from './app-routing.module';
//
// @NgModule({
//   imports: [
//     BrowserModule,
//     AppRoutingModule,
//   ],
//   providers: [
//     provideClientHydration({ appId: 'serverApp' })
//   ],
// })
// export class AppModule { }

// import { NgModule } from '@angular/core';
// import { BrowserModule } from '@angular/platform-browser';
// import { AppRoutingModule } from './app-routing.module'; // Ensure this path is correct
//
// @NgModule({
//   imports: [
//     BrowserModule,
//     AppRoutingModule,
//   ],
//   providers: []
// })
// export class AppModule { }




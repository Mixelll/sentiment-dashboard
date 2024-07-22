// import { bootstrapApplication } from '@angular/platform-browser';
// import { AppComponent } from './app/app.component';
// import { config } from './app/app.config.server';
//
// const bootstrap = () => bootstrapApplication(AppComponent, config);
//
// export default bootstrap;


// import { bootstrapApplication } from '@angular/platform-server';
// import { AppComponent } from './app/app.component';
// import { config } from './app/app.config.server';
//
// export const bootstrap = () => bootstrapApplication(AppComponent, config);
//
// export default bootstrap;

import 'zone.js';  // Simplified import, assuming zone.js properly initializes itself for server-side use

import { enableProdMode, importProvidersFrom } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { AppServerModule } from './app/app.server.module';
import { provideServerRendering } from '@angular/platform-server';
import { environment } from './environments/environment';

if (environment.production) {
  enableProdMode();
}


export const bootstrap = () => bootstrapApplication(AppComponent, {
  providers: [
    importProvidersFrom(AppServerModule),
    provideServerRendering()
  ]
});

export default bootstrap;




// import { bootstrapApplication } from '@angular/platform-server';
// import { AppComponent } from './app/app.component';
// import { appConfig } from './app/app.config.server';
//
// export const bootstrap = () => bootstrapApplication(AppComponent, appConfig);


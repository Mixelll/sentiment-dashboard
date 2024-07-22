// import { APP_BASE_HREF } from '@angular/common';
// import { CommonEngine } from '@angular/ssr';
// import express from 'express';
// import { fileURLToPath } from 'node:url';
// import { dirname, join, resolve } from 'node:path';
//
// export function app(): express.Express {
//   const server = express();
//   const serverDistFolder = dirname(fileURLToPath(import.meta.url));
//   const browserDistFolder = resolve(serverDistFolder, '../browser');
//   const indexHtml = join(browserDistFolder, 'index.html');
//
//   const commonEngine = new CommonEngine();
//
//   server.set('view engine', 'html');
//   server.set('views', browserDistFolder);
//
//   // Serve static files
//   server.get('*.*', express.static(browserDistFolder, {
//     maxAge: '1y'
//   }));
//
//   // All regular routes use the Universal engine
//   server.get('*', (req, res) => {
//     commonEngine.render({
//       documentFilePath: indexHtml,
//       url: req.url,
//       providers: [
//         { provide: APP_BASE_HREF, useValue: req.baseUrl }
//       ]
//     })
//     .then(html => res.send(html))
//     .catch(err => {
//       console.error(err);
//       res.status(500).send('Server error');
//     });
//   });
//
//   return server;
// }
//
// function run(): void {
//   const port = process.env['PORT'] || 4000;
//   const server = app();
//   server.listen(port, () => {
//     console.log(`Node Express server listening on http://localhost:${port}`);
//   });
// }
//
// run();


// import { APP_BASE_HREF } from '@angular/common';
// import { CommonEngine } from '@angular/ssr';
// import express from 'express';
// import { fileURLToPath } from 'node:url';
// import { dirname, join, resolve } from 'node:path';
// import { AppServerModule } from './src/app/app.server.module';
//
// export function app(): express.Express {
//   const server = express();
//   const serverDistFolder = dirname(fileURLToPath(import.meta.url));
//   const browserDistFolder = resolve(serverDistFolder, '../browser');
//   const indexHtml = join(browserDistFolder, 'index.html');
//
//   // Instantiating CommonEngine with the AppServerModule
//   const commonEngine = new CommonEngine();
//
//   server.set('view engine', 'html');
//   server.set('views', browserDistFolder);
//
//   // Serve static files
//   server.get('*.*', express.static(browserDistFolder, {
//     maxAge: '1y'
//   }));
//
//   // All regular routes use the Universal engine
//   server.get('*', (req, res) => {
//     commonEngine.render({
//       bootstrap: AppServerModule,
//       documentFilePath: indexHtml,
//       url: req.url,
//       providers: [
//         { provide: APP_BASE_HREF, useValue: req.baseUrl }
//       ]
//     })
//     .then(html => res.send(html))
//     .catch(err => {
//       console.error(err);
//       res.status(500).send('Server error');
//     });
//   });
//
//   return server;
// }
//
// function run(): void {
//   const port = process.env['PORT'] || 4000;
//   const server = app();
//   server.listen(port, () => {
//     console.log(`Node Express server listening on http://localhost:${port}`);
//   });
// }
//
// run();



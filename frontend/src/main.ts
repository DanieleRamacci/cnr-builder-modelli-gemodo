import { bootstrapApplication } from '@angular/platform-browser';

import { buildAppConfig } from './app/app.config';
import { App } from './app/app';
import { loadRuntimeConfig } from './app/runtime-config';

loadRuntimeConfig()
  .then((runtimeConfig) => bootstrapApplication(App, buildAppConfig(runtimeConfig)))
  .catch((err: unknown) => console.error(err));

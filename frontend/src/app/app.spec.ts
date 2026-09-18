import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideDesignAngularKit } from 'design-angular-kit';

import { App } from './app';
import { RUNTIME_CONFIG } from './runtime-config';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      // provideHttpClientTesting: the shell renders it-header/it-footer, which pull
      // in design-angular-kit's ngx-translate loader - without a testing backend it
      // tries a real XHR for its i18n JSON and throws an uncaught HttpErrorResponse
      // (harmless to the assertions, but noisy and a real fetch attempt in jsdom).
      providers: [
        provideRouter([]),
        provideDesignAngularKit(),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: RUNTIME_CONFIG,
          useValue: {
            keycloakIssuerUrl: 'https://example.test/realms/x',
            keycloakClientId: 'gemodo-frontend',
          },
        },
      ],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render the GEMODO brand in the shell header', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[brand]')?.textContent).toContain('GEMODO');
  });
});

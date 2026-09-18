import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Keycloak from 'keycloak-js';
import { IntegrazioniManagerComponent } from './integrazioni-manager.component';

describe('ACE integration selection', () => {
  it('opens with context roles alone and distinguishes token contexts from available integrations', () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: Keycloak,
          useValue: {
            tokenParsed: {
              contexts: {
                geban: { roles: ['ROLE_MANAGER#geban'] },
                altro: { roles: ['ROLE_USER#altro'] },
              },
            },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(IntegrazioniManagerComponent);
    const http = TestBed.inject(HttpTestingController);
    http
      .expectOne('/api/v1/builder/integrazioni')
      .flush([
        { id: 'source', codice: 'GEBAN', nome: 'Software connesso', codice_contesto: 'geban' },
      ]);
    fixture.detectChanges();
    const select: HTMLSelectElement = fixture.nativeElement.querySelector('select');
    select.value = 'geban';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Software connesso');
    select.value = 'altro';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Software connesso');
    expect(fixture.nativeElement.textContent).toContain('Nessuna integrazione connessa');
    http.verify();
  });
});

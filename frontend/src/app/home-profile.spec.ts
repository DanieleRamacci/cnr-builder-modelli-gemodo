import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Keycloak from 'keycloak-js';
import { HomeComponent } from './home.component';
import { ProfileComponent } from './profile.component';
describe('home and profile', () => {
  it('shows an explicit denial without operational links', () => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: Keycloak, useValue: { tokenParsed: {} } }],
    });
    const fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Non sei autorizzato');
    expect(fixture.nativeElement.querySelector('a')).toBeNull();
  });
  it('shows both operational areas for an admin manager', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        {
          provide: Keycloak,
          useValue: {
            tokenParsed: {
              resource_access: {
                'gemodo-backend': { roles: ['GEMODO_ADMIN', 'GEMODO_MODELLI_GESTORE'] },
              },
            },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('a[href="/configurazione"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('a[href="/contesti"]')).toBeTruthy();
    expect(fixture.nativeElement.textContent).not.toContain('canale');
  });
  it('keeps the token hidden until requested and logs out through Keycloak', () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
      providers: [
        {
          provide: Keycloak,
          useValue: { token: 'TEST_TOKEN', tokenParsed: { name: 'Demo Utente' }, logout },
        },
      ],
    });
    const fixture = TestBed.createComponent(ProfileComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Demo Utente');
    expect(fixture.nativeElement.textContent).not.toContain('TEST_TOKEN');
    fixture.nativeElement.querySelector('button').click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('TEST_TOKEN');
    fixture.nativeElement.querySelectorAll('button')[1].click();
    expect(logout).toHaveBeenCalledWith({ redirectUri: window.location.origin });
  });
});

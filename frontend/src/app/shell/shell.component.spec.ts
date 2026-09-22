import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Keycloak from 'keycloak-js';
import { provideDesignAngularKit } from 'design-angular-kit';
import { ShellComponent } from './shell.component';
import { RUNTIME_CONFIG } from '../runtime-config';

function setup(roles: string[]) {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      provideDesignAngularKit(),
      { provide: RUNTIME_CONFIG, useValue: { keycloakIssuerUrl: '', keycloakClientId: '' } },
      {
        provide: Keycloak,
        useValue: {
          tokenParsed: { name: 'Maria Bianchi', resource_access: { 'gemodo-backend': { roles } } },
        },
      },
    ],
  });
  const fixture = TestBed.createComponent(ShellComponent);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

const voci = (root: HTMLElement) =>
  Array.from(root.querySelectorAll('nav a')).map((a) => a.textContent!.trim());

describe('header applicativo (design handoff)', () => {
  it('shows the admin navigation without the retired Tipi documento entry', () => {
    const root = setup(['GEMODO_ADMIN']);
    expect(voci(root)).toEqual(['Contesti', 'Impostazioni']);
    expect(root.textContent).not.toContain('Tipi documento');
  });

  it('shows only what a model editor can reach', () => {
    const root = setup(['GEMODO_MODELLI_GESTORE']);
    expect(voci(root)).toEqual(['Contesti', 'Modelli']);
  });

  it('shows the full design navigation for users with both roles', () => {
    const root = setup(['GEMODO_ADMIN', 'GEMODO_MODELLI_GESTORE']);
    expect(voci(root)).toEqual(['Contesti', 'Modelli', 'Impostazioni']);
  });

  it('shows the user initials in the avatar, not a generic icon', () => {
    const root = setup(['GEMODO_ADMIN']);
    const avatar = root.querySelector('.avatar')!;
    expect(avatar.textContent!.trim()).toBe('MB');
    expect(root.querySelector('a[href="/profilo"]')).not.toBeNull();
  });

  it('is a single bar, not the three-band Bootstrap Italia header', () => {
    const root = setup(['GEMODO_ADMIN']);
    expect(root.querySelectorAll('header').length).toBe(1);
    expect(root.querySelector('header .slim-header')).toBeNull();
    // Nav e identita' vivono nella stessa barra del logo.
    const header = root.querySelector('header')!;
    expect(header.querySelector('nav')).not.toBeNull();
    expect(header.querySelector('a[href="/profilo"]')).not.toBeNull();
  });
});

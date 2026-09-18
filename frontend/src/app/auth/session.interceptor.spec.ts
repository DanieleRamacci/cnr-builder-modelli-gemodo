import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import Keycloak from 'keycloak-js';
import { firstValueFrom } from 'rxjs';
import { sessionInterceptor } from './session.interceptor';

describe('session interceptor', () => {
  let keycloak: {
    authenticated: boolean;
    token: string;
    updateToken: ReturnType<typeof vi.fn>;
    isTokenExpired: ReturnType<typeof vi.fn>;
  };
  beforeEach(() => {
    keycloak = {
      authenticated: true,
      token: 'TEST_TOKEN',
      updateToken: vi.fn().mockResolvedValue(false),
      isTokenExpired: vi.fn().mockReturnValue(false),
    };
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([sessionInterceptor])),
        provideHttpClientTesting(),
        { provide: Keycloak, useValue: keycloak },
      ],
    });
  });
  afterEach(() => TestBed.inject(HttpTestingController).verify());
  it('refreshes before sending the current token', async () => {
    keycloak.updateToken.mockImplementation(async () => {
      keycloak.token = 'REFRESHED_TOKEN';
      return true;
    });
    const result = firstValueFrom(TestBed.inject(HttpClient).get('/api/v1/test'));
    await Promise.resolve();
    await Promise.resolve();
    const request = TestBed.inject(HttpTestingController).expectOne('/api/v1/test');
    expect(request.request.headers.get('Authorization')).toBe('Bearer REFRESHED_TOKEN');
    request.flush({});
    await result;
  });
  it('blocks a write if refresh fails without sending or retrying it', async () => {
    keycloak.updateToken.mockRejectedValue(new Error('Refresh rejected'));
    const result = firstValueFrom(TestBed.inject(HttpClient).post('/api/v1/test', {}));
    await expect(result).rejects.toMatchObject({
      status: 401,
      error: { codice: 'SESSIONE_SCADUTA' },
    });
    TestBed.inject(HttpTestingController).expectNone('/api/v1/test');
  });
  it('never sends a token to external destinations', async () => {
    const result = firstValueFrom(TestBed.inject(HttpClient).get('https://external.test/api/test'));
    const request = TestBed.inject(HttpTestingController).expectOne(
      'https://external.test/api/test',
    );
    expect(request.request.headers.has('Authorization')).toBe(false);
    expect(keycloak.updateToken).not.toHaveBeenCalled();
    request.flush({});
    await result;
  });
});

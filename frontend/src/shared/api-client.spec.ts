import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { ApiClient } from './api-client';
import type { ApiError } from './api-error';

describe('ApiClient', () => {
  let client: ApiClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    client = TestBed.inject(ApiClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('returns the decoded body on success', async () => {
    const promise = firstValueFrom(client.get<{ ok: boolean }>('/api/v1/test'));
    httpMock.expectOne('/api/v1/test').flush({ ok: true });
    await expect(promise).resolves.toEqual({ ok: true });
  });

  it('maps the backend {codice, messaggio} envelope on error', async () => {
    const promise = firstValueFrom(client.get('/api/v1/test'));
    httpMock
      .expectOne('/api/v1/test')
      .flush(
        { codice: 'REVISIONE_SUPERATA', messaggio: 'Rileggere la configurazione corrente' },
        { status: 409, statusText: 'Conflict' },
      );
    await expect(promise).rejects.toEqual({
      codice: 'REVISIONE_SUPERATA',
      messaggio: 'Rileggere la configurazione corrente',
      status: 409,
    } satisfies ApiError);
  });

  it('falls back to a generic error when the response has no envelope', async () => {
    const promise = firstValueFrom(client.get('/api/v1/test'));
    httpMock.expectOne('/api/v1/test').flush(null, { status: 502, statusText: 'Bad Gateway' });
    await expect(promise).rejects.toMatchObject({ status: 502, codice: 'ERRORE_SCONOSCIUTO' });
  });

  it('sends POST/PUT bodies untouched', async () => {
    const postPromise = firstValueFrom(client.post('/api/v1/test', { a: 1 }));
    const postReq = httpMock.expectOne('/api/v1/test');
    expect(postReq.request.method).toBe('POST');
    expect(postReq.request.body).toEqual({ a: 1 });
    postReq.flush({});
    await postPromise;

    const putPromise = firstValueFrom(client.put('/api/v1/test', { b: 2 }));
    const putReq = httpMock.expectOne('/api/v1/test');
    expect(putReq.request.method).toBe('PUT');
    expect(putReq.request.body).toEqual({ b: 2 });
    putReq.flush({});
    await putPromise;
  });
});

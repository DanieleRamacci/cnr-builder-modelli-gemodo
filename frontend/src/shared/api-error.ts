/** UI-facing shape of the backend's `{codice, messaggio}` error envelope. */
export interface ApiError {
  readonly codice: string;
  readonly messaggio: string;
  readonly status: number;
}

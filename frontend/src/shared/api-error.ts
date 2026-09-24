/** UI-facing shape of the backend's `{codice, messaggio, dettagli}` error envelope. */
export interface ApiError {
  readonly codice: string;
  readonly messaggio: string;
  readonly status: number;
  /** Presente quando l'errore porta con se' cosa esattamente e' coinvolto. */
  readonly dettagli?: readonly Record<string, string>[];
}

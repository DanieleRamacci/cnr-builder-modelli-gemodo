/**
 * jsdom non calcola il layout: le misure che ProseMirror chiede per portare
 * il cursore in vista (rettangoli di un intervallo, elemento sotto un punto)
 * qui non esistono. Si rispondono con rettangoli vuoti, cosi' che i test di
 * componente possano usare l'editor vero (012 T077).
 */
const RETTANGOLO_VUOTO = {
  x: 0,
  y: 0,
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  width: 0,
  height: 0,
  toJSON: () => ({}),
} as DOMRect;

if (typeof Range !== 'undefined') {
  Range.prototype.getClientRects ??= () => [] as unknown as DOMRectList;
  Range.prototype.getBoundingClientRect ??= () => RETTANGOLO_VUOTO;
}
if (typeof document !== 'undefined') {
  document.elementFromPoint ??= () => null;
}

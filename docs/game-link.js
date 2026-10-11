// Follows RED's battle by reading the game's RAM straight out of the emulator.
//
// The game keeps a status block in RAM (sStatus in pokefirered/src/dailyred.c):
// the magic "DAILYRED-STATUS1", the seed it was booted with, a phase byte and a
// result byte. We search the emulator's WebAssembly memory for the magic
// followed by our seed (the ROM's own copy of the magic isn't followed by it),
// remember where it is, and read the two bytes on each call.

const MAGIC = new Uint32Array(new TextEncoder().encode('DAILYRED-STATUS1').buffer);

export const PHASE = { EXPLORING: 0, BATTLE: 1, RESULT: 2, FINISHED: 3 };
export const RESULT = { NONE: 0, WON: 1, LOST: 2 };

// Returns read(): { phase, result }, or null until the game has set up its
// status block (just after boot).
export function createGameLink(emulator, seed) {
  let offset = -1;
  return function read() {
    const heap = emulator.getEmscriptenModule().HEAPU8; // replaced if memory grows
    if (offset < 0) offset = findStatus(heap, seed >>> 0);
    if (offset < 0) return null;
    return { phase: heap[offset + 20], result: heap[offset + 21] };
  };
}

function findStatus(heap, seed) {
  const words = new Uint32Array(heap.buffer, heap.byteOffset, heap.byteLength >>> 2);
  for (let i = 0, end = words.length - 5; i < end; i++) {
    if (words[i] === MAGIC[0] && words[i + 1] === MAGIC[1] && words[i + 2] === MAGIC[2]
     && words[i + 3] === MAGIC[3] && words[i + 4] === seed) {
      return i * 4;
    }
  }
  return -1;
}

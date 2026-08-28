/// <reference types="vite/client" />

// The precomputed payload is large; typing it structurally from the file would
// slow the compiler down for no benefit. It is cast to `Payload` on import.
declare module '*.json' {
  const value: unknown;
  export default value;
}

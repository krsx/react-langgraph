import "@testing-library/jest-dom/vitest";

// jsdom doesn't implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// TanStack Query v5 sends AbortSignal — patch jsdom's AbortController to use the global
Object.defineProperty(globalThis, "AbortSignal", {
  writable: true,
  value: globalThis.AbortSignal,
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

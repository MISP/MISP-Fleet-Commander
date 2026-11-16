import { vi } from "vitest"

// The app's wiring (store, router, API client) pulls in every view: modules under test only need it to exist.
// A test that checks calls to the API mocks the API module it uses
vi.mock("@/store/index", () => ({ default: {} }))
vi.mock("@/router", () => ({ default: {} }))
vi.mock("@/api/common", () => ({
    default: {
        getClient: vi.fn(),
        handleError: vi.fn(),
        fetchImageObjectURL: vi.fn(),
        appendFleetIDIfDefined: vi.fn(),
        searchAll: vi.fn(),
    },
}))

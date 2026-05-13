import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './mocks/server'

// jsdom doesn't implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = () => {}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

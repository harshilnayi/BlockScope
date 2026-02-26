import { render,  cleanup } from '@testing-library/react'
import { describe, test, expect } from 'vitest'
import App from '../App'
import { vi } from 'vitest';


vi.mock('../apiClient', () => ({
  apiClient: {
    scanContract: vi.fn(),
  },
}));


describe('App component', () => {
  test('renders without crashing', () => {
    render(<App />)
    expect(document.body).toBeTruthy()
  })

  test('renders consistently on multiple renders', () => {
    const { rerender } = render(<App />)
    rerender(<App />)
    rerender(<App />)
    expect(document.body).toBeTruthy()
  })

  test('contains a root element', () => {
    const { container } = render(<App />)
    expect(container.firstChild).not.toBeNull()
  })

  test('does not throw during unmount', () => {
    const { unmount } = render(<App />)
    expect(() => unmount()).not.toThrow()
  })

  test('renders inside the document body', () => {
    render(<App />)
    expect(document.body.innerHTML.length).toBeGreaterThan(0)
  })

  test('cleanup removes App from DOM', () => {
    render(<App />)
    cleanup()
    expect(document.body.innerHTML).toBe('')
  })
})

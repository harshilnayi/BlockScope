import { render, screen, fireEvent } from '@testing-library/react'
import { describe, test, expect, vi } from 'vitest'
import FileUpload from '../components/FileUpload'

describe('FileUpload component', () => {
  test('renders file input', () => {
    render(<FileUpload />)
    const input = screen.getByTestId('file-input')
    expect(input).toBeInTheDocument()
    expect(input.type).toBe('file')
  })

  test('calls onFileSelect when a file is chosen', () => {
    const mockHandler = vi.fn()
    render(<FileUpload onFileSelect={mockHandler} />)

    const file = new File(['hello'], 'test.txt', { type: 'text/plain' })
    const input = screen.getByTestId('file-input')

    fireEvent.change(input, {
      target: { files: [file] },
    })

    expect(mockHandler).toHaveBeenCalledOnce()
    expect(mockHandler).toHaveBeenCalledWith(file)
  })
})

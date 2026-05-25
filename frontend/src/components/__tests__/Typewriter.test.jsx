import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import Typewriter from '../Typewriter'

test('Typewriter renders progressively and calls onComplete', () => {
  vi.useFakeTimers()
  const onComplete = vi.fn()

  render(<Typewriter text="Hi" speed={10} onComplete={onComplete} />)

  // Advance to first character
  vi.advanceTimersByTime(10)
  expect(screen.getByText(/H/)).toBeInTheDocument()

  // Advance to full text
  vi.advanceTimersByTime(10)
  expect(screen.getByText(/Hi/)).toBeInTheDocument()

  // Complete callback should be invoked after finishing
  vi.advanceTimersByTime(10)
  expect(onComplete).toHaveBeenCalled()

  vi.useRealTimers()
})

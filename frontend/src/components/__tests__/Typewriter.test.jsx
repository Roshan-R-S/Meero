import React from 'react'
import '@testing-library/jest-dom'
import { act, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import Typewriter from '../Typewriter'

describe('Typewriter', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  test('renders characters over time and calls onComplete', async () => {
    const onComplete = vi.fn()
    render(<Typewriter text={'Hi'} speed={10} onComplete={onComplete} />)

    // First character
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(screen.getByText(/H/)).toBeInTheDocument()

    // Second character
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(screen.getByText(/Hi/)).toBeInTheDocument()

    // Let completion callback effect fire
    act(() => {
      vi.advanceTimersByTime(10)
    })
    expect(onComplete).toHaveBeenCalled()
  })
})

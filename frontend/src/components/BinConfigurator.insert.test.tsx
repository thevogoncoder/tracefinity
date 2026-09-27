// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { BinConfigurator } from './BinConfigurator'
import { FACTORY_BIN_CONFIG } from '@/lib/binDefaults'

afterEach(cleanup)
beforeEach(() => localStorage.setItem('theme', 'dark'))

function row(label: string) {
  return within(screen.getByText(label, { exact: true }).parentElement!)
}

describe('contrast insert controls', () => {
  it('defaults an in-place insert to one layer and hides the fit clearance', () => {
    const onChange = vi.fn()
    const config = { ...FACTORY_BIN_CONFIG, insert_enabled: true }
    const { rerender } = render(<BinConfigurator config={config} onChange={onChange} />)
    expect(screen.getByText('Insert Fit')).toBeTruthy()
    fireEvent.click(row('Print in place').getByRole('button'))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ insert_in_place: true, insert_height: 0.2 }))
    rerender(<BinConfigurator config={onChange.mock.lastCall![0]} onChange={onChange} />)
    expect(screen.queryByText('Insert Fit')).toBeNull()
    expect(row('Insert Height').getByRole('spinbutton').getAttribute('min')).toBe('0.2')
  })

  it('keeps the chosen height when switching back to a loose insert', () => {
    const onChange = vi.fn()
    const { rerender } = render(<BinConfigurator config={{ ...FACTORY_BIN_CONFIG, insert_enabled: true, insert_in_place: true, insert_height: 0.4 }} onChange={onChange} />)
    fireEvent.click(row('Print in place').getByRole('button'))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ insert_in_place: false, insert_height: 0.4 }))
    rerender(<BinConfigurator config={onChange.mock.lastCall![0]} onChange={onChange} />)
    expect(screen.getByText('Insert Fit')).toBeTruthy()
  })
})

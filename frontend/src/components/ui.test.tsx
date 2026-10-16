import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ClassBadge, EmptyState, Pagination } from './ui'

describe('ui components', () => {
  it('shows a text label for classifications, not colour alone', () => {
    render(<><ClassBadge cls="DoS" suspicious severity="High" /><ClassBadge cls="Normal" suspicious={false} /></>)
    expect(screen.getByText('Suspicious: DoS')).toBeTruthy()
    expect(screen.getByText('Normal')).toBeTruthy()
  })
  it('renders an empty state with its message', () => {
    render(<MemoryRouter><EmptyState title="No analysis available yet" text="Import a network traffic CSV to begin." /></MemoryRouter>)
    expect(screen.getByText('Import a network traffic CSV to begin.')).toBeTruthy()
  })
  it('disables Previous on the first page', () => {
    render(<Pagination page={1} pageSize={25} total={100} onPage={() => {}} />)
    expect((screen.getByText('Previous') as HTMLButtonElement).disabled).toBe(true)
  })
})

import '@testing-library/jest-dom/vitest'
import 'vitest-axe/extend-expect'
import { expect, vi } from 'vitest'
import * as axeMatchers from 'vitest-axe/matchers'
import '../i18n'

// In React 19, act IS NOT exported from 'react'.
// @testing-library/react's act-compat checks for React.act first, which is undefined.
// Then it falls back to react-dom/test-utils.act which calls React.act (undefined) causing the error.
// We mock 'react' to export act from react-dom/test-utils so testing-library finds it.
// vi.mock is hoisted - runs before any imports.
vi.mock('react', async () => {
  const actual = await vi.importActual('react')
  const { act } = await vi.importActual('react-dom/test-utils')
  return {
    ...actual,
    act,
  }
})

expect.extend(axeMatchers)

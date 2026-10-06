/* eslint-disable @typescript-eslint/no-empty-object-type, @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars */
import 'vitest'
import type { AxeMatchers } from 'vitest-axe/matchers'

// vitest-axe only augments the legacy global `Vi` namespace, which Vitest 5 no
// longer uses for matcher types. Re-augment the `vitest` module so the
// `toHaveNoViolations` matcher typechecks in tests.
declare module 'vitest' {
  interface Assertion<T = any> extends AxeMatchers {}
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}

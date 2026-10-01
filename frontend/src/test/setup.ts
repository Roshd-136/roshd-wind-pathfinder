import '@testing-library/jest-dom/vitest'
import 'vitest-axe/extend-expect'
import { expect } from 'vitest'
import * as axeMatchers from 'vitest-axe/matchers'
import '../i18n'

expect.extend(axeMatchers)

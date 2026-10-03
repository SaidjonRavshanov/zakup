import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { queryClient } from '@/shared/api/query-client'
import { initI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { detectPerformanceMode } from '@/shared/lib/theme'
import { initTheme } from '@/shared/lib/use-theme'
import { AuthGate } from './AuthGate'
import { router } from './router'
import './styles/index.css'

telegram.init()
detectPerformanceMode()
initTheme()
initI18n()

const root = document.getElementById('root')
if (!root) throw new Error('#root topilmadi')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <RouterProvider router={router} />
      </AuthGate>
    </QueryClientProvider>
  </StrictMode>,
)

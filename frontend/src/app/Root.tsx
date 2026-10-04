import { RouterProvider } from '@tanstack/react-router'
import { lazy, Suspense } from 'react'
import { AuthGate } from './AuthGate'
import { router } from './router'

// Yetkazuvchi havolasi (/s/{token}) — kirishsiz, ilova qobig'isiz (alohida chunk)
const SupplierLinkPage = lazy(() => import('@/pages/supplier-link/SupplierLinkPage'))
const supplierToken = /^\/s\/([\w-]+)\/?$/.exec(window.location.pathname)?.[1]

export function Root() {
  if (supplierToken) {
    return (
      <Suspense>
        <SupplierLinkPage token={supplierToken} />
      </Suspense>
    )
  }
  return (
    <AuthGate>
      <RouterProvider router={router} />
    </AuthGate>
  )
}

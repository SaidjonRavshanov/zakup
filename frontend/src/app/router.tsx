import { createRootRoute, createRoute, createRouter, lazyRouteComponent } from '@tanstack/react-router'
import { CATALOG_TABS, type CatalogTab } from '@/entities/catalog'
import { NotFoundPage as NotFound } from '@/pages/not-found/NotFoundPage'
import { AppShell } from '@/widgets/app-shell/AppShell'

const rootRoute = createRootRoute({ notFoundComponent: NotFound })

// Layout route: BottomNav'li qobiq. Har bir sahifa — alohida lazy chunk.
const shellRoute = createRoute({ getParentRoute: () => rootRoute, id: 'shell', component: AppShell })

const dashboardRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/',
  component: lazyRouteComponent(() => import('@/pages/dashboard/DashboardPage')),
})

const todoRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/todo',
  component: lazyRouteComponent(() => import('@/pages/todo/TodoPage')),
})

const ordersRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/orders',
  component: lazyRouteComponent(() => import('@/pages/orders/OrdersPage')),
})

const receivingRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/receiving',
  component: lazyRouteComponent(() => import('@/pages/receiving/ReceivingListPage')),
})

export const receiveOrderRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/receiving/$orderId',
  component: lazyRouteComponent(() => import('@/pages/receiving/ReceiveOrderPage')),
})

const profileRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/profile',
  component: lazyRouteComponent(() => import('@/pages/profile/ProfilePage')),
})

const usersRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/admin/users',
  component: lazyRouteComponent(() => import('@/pages/admin-users/UsersPage')),
})

const userEditRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/admin/users/$userId',
  component: lazyRouteComponent(() => import('@/pages/admin-users/UserEditPage')),
})


const catalogRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/catalog',
  validateSearch: (search: Record<string, unknown>): { tab?: CatalogTab } =>
    CATALOG_TABS.includes(search.tab as CatalogTab) ? { tab: search.tab as CatalogTab } : {},
  component: lazyRouteComponent(() => import('@/pages/catalog/CatalogPage')),
})

const requestRoutes = [
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/requests',
    component: lazyRouteComponent(() => import('@/pages/requests/RequestsPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/requests/new',
    component: lazyRouteComponent(() => import('@/pages/requests/RequestNewPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/requests/$requestId',
    component: lazyRouteComponent(() => import('@/pages/requests/RequestPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/orders/$orderId',
    component: lazyRouteComponent(() => import('@/pages/orders/OrderPage')),
  }),
] as const

const receiptRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/receiving/receipts/$receiptId',
  component: lazyRouteComponent(() => import('@/pages/receiving/ReceiptPage')),
})

const financeRoutes = [
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/finance',
    component: lazyRouteComponent(() => import('@/pages/finance/FinancePage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/finance/suppliers/$supplierId',
    component: lazyRouteComponent(() => import('@/pages/finance/SupplierAccountPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/finance/payments/$paymentId',
    component: lazyRouteComponent(() => import('@/pages/finance/PaymentPage')),
  }),
]

const analyticsRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/analytics',
  component: lazyRouteComponent(() => import('@/pages/analytics/AnalyticsPage')),
})

const iikoRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/admin/iiko',
  component: lazyRouteComponent(() => import('@/pages/admin-iiko/IikoSyncPage')),
})

// Bir xil forma yaratish va tahrir uchun: bitta lazy chunk
const productFormImport = () => import('@/pages/catalog/ProductFormPage')
const supplierFormImport = () => import('@/pages/catalog/SupplierFormPage')
const offerFormImport = () => import('@/pages/catalog/OfferFormPage')

const catalogRoutes = [
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/products/new',
    component: lazyRouteComponent(productFormImport),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/products/$productId',
    component: lazyRouteComponent(() => import('@/pages/catalog/ProductPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/products/$productId/edit',
    component: lazyRouteComponent(productFormImport),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/products/$productId/cards/$storeId',
    component: lazyRouteComponent(() => import('@/pages/catalog/PurchaseCardPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/suppliers/new',
    component: lazyRouteComponent(supplierFormImport),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/suppliers/$supplierId',
    component: lazyRouteComponent(() => import('@/pages/catalog/SupplierPage')),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/suppliers/$supplierId/edit',
    component: lazyRouteComponent(supplierFormImport),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/suppliers/$supplierId/offers/new',
    component: lazyRouteComponent(offerFormImport),
  }),
  createRoute({
    getParentRoute: () => shellRoute,
    path: '/catalog/suppliers/$supplierId/offers/$offerId',
    component: lazyRouteComponent(offerFormImport),
  }),
] as const


const routeTree = rootRoute.addChildren([
  shellRoute.addChildren([dashboardRoute, todoRoute, ordersRoute, receivingRoute, receiveOrderRoute, profileRoute, usersRoute, userEditRoute, iikoRoute, receiptRoute, ...financeRoutes, analyticsRoute, ...requestRoutes, catalogRoute, ...catalogRoutes]),
])

export const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  defaultPendingMs: 150,
  scrollRestoration: true,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

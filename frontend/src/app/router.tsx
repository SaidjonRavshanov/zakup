import { createRootRoute, createRoute, createRouter, lazyRouteComponent } from '@tanstack/react-router'
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

// Prod build'da shart statik false bo'ladi → vitrin chunk'i bundle'ga kirmaydi
const devUiRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: '/dev/ui',
  component: import.meta.env.DEV ? lazyRouteComponent(() => import('@/pages/dev-ui/DevUiPage')) : NotFound,
})

const routeTree = rootRoute.addChildren([
  shellRoute.addChildren([dashboardRoute, ordersRoute, receivingRoute, receiveOrderRoute, profileRoute, devUiRoute]),
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

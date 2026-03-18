import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { apiMe } from '../lib/api.js'

const routes = [
  {
    path: '/login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    redirect: '/databases',
  },
  {
    path: '/',
    component: () => import('../views/AppLayout.vue'),
    children: [
      {
        path: 'databases',
        component: () => import('../views/DatabasesView.vue'),
      },
      {
        path: 'catalog',
        component: () => import('../views/CatalogView.vue'),
      },
      {
        path: 'n8n',
        component: () => import('../views/N8nView.vue'),
      },
      {
        path: 'security',
        component: () => import('../views/SecurityView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true

  const authStore = useAuthStore()

  if (!authStore.currentUser) {
    try {
      const res = await apiMe()
      if (!res || !res.ok) {
        return '/login'
      }
      const user = await res.json()
      authStore.setUser(user)
    } catch {
      return '/login'
    }
  }

  return true
})

export default router

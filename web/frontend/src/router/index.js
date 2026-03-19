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
      { path: 'databases',  component: () => import('../views/DatabasesView.vue') },
      { path: 'catalog',    component: () => import('../views/CatalogView.vue') },
      { path: 'library',    component: () => import('../views/LibraryView.vue') },
      { path: 'metabase',   component: () => import('../views/MetabaseView.vue') },
      { path: 'redis',      component: () => import('../views/RedisView.vue') },
      { path: 'postgrest',  component: () => import('../views/PostgRESTView.vue') },
      { path: 'mage',       component: () => import('../views/MageView.vue') },
      { path: 'minio',      component: () => import('../views/MinIOView.vue') },
      { path: 'mariadb',    component: () => import('../views/MariaDBView.vue') },
      { path: 'qdrant',     component: () => import('../views/QdrantView.vue') },
      { path: 'clickhouse', component: () => import('../views/ClickHouseView.vue') },
      { path: 'ollama',     component: () => import('../views/OllamaView.vue') },
      { path: 'superset',   component: () => import('../views/SupersetView.vue') },
      { path: 'airflow',    component: () => import('../views/AirflowView.vue') },
      { path: 'hasura',     component: () => import('../views/HasuraView.vue') },
      {
        path: 'security',
        component: () => import('../views/SecurityView.vue'),
        meta: { requiresAdmin: true },
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
      if (!res || !res.ok) return '/login'
      const user = await res.json()
      authStore.setUser(user)
    } catch {
      return '/login'
    }
  }

  if (to.meta.requiresAdmin && authStore.currentUser?.role !== 'admin') {
    return '/databases'
  }

  return true
})

export default router

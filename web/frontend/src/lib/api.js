async function fetchWithAuth(url, opts = {}) {
  let res = await fetch(url, opts)
  if (res.status !== 401) return res
  const rr = await fetch('/api/auth/refresh', { method: 'POST' })
  if (!rr.ok) {
    window.location.href = '/login'
    return null
  }
  return fetch(url, opts)
}

export { fetchWithAuth }

// Auth
export async function apiMe() {
  return fetchWithAuth('/api/me')
}

export async function apiLogin(username, password) {
  return fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export async function apiLogout() {
  return fetch('/api/auth/logout', { method: 'POST' })
}

// Postgres
export async function apiGetPostgres() {
  return fetchWithAuth('/api/postgres')
}

export async function apiGetPostgresInstance(id) {
  return fetchWithAuth(`/api/postgres/${id}`)
}

export async function apiCreatePostgres(body) {
  return fetchWithAuth('/api/postgres', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function apiDeletePostgres(id) {
  return fetchWithAuth(`/api/postgres/${id}`, { method: 'DELETE' })
}

// Catalog
export async function apiGetDatabases(instanceId) {
  return fetchWithAuth(`/api/postgres/${instanceId}/databases`)
}

export async function apiGetTables(instanceId, dbName) {
  return fetchWithAuth(`/api/postgres/${instanceId}/databases/${dbName}/tables`)
}

export async function apiGetTableColumns(instanceId, dbName, tableName) {
  return fetchWithAuth(`/api/postgres/${instanceId}/databases/${dbName}/tables/${tableName}`)
}

export async function apiGetTableStats(instanceId, dbName, tableName) {
  return fetchWithAuth(`/api/postgres/${instanceId}/databases/${dbName}/tables/${tableName}/stats`)
}

export async function apiGetTableSample(instanceId, dbName, tableName) {
  return fetchWithAuth(`/api/postgres/${instanceId}/databases/${dbName}/tables/${tableName}/sample`)
}

// n8n
export async function apiGetN8n() {
  return fetchWithAuth('/api/n8n')
}

export async function apiGetN8nInstance(id) {
  return fetchWithAuth(`/api/n8n/${id}`)
}

export async function apiCreateN8n(body) {
  return fetchWithAuth('/api/n8n', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function apiDeleteN8n(id) {
  return fetchWithAuth(`/api/n8n/${id}`, { method: 'DELETE' })
}

// Users
export async function apiGetUsers() {
  return fetchWithAuth('/api/users')
}

export async function apiCreateUser(body) {
  return fetchWithAuth('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function apiDeleteUser(id) {
  return fetchWithAuth(`/api/users/${id}`, { method: 'DELETE' })
}

// Metabase
export async function apiGetMetabase() {
  return fetchWithAuth('/api/metabase')
}
export async function apiGetMetabaseInstance(id) {
  return fetchWithAuth(`/api/metabase/${id}`)
}
export async function apiCreateMetabase(body) {
  return fetchWithAuth('/api/metabase', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteMetabase(id) {
  return fetchWithAuth(`/api/metabase/${id}`, { method: 'DELETE' })
}

// Redis
export async function apiGetRedis() {
  return fetchWithAuth('/api/redis')
}
export async function apiGetRedisInstance(id) {
  return fetchWithAuth(`/api/redis/${id}`)
}
export async function apiCreateRedis(body) {
  return fetchWithAuth('/api/redis', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteRedis(id) {
  return fetchWithAuth(`/api/redis/${id}`, { method: 'DELETE' })
}

// PostgREST
export async function apiGetPostgREST() {
  return fetchWithAuth('/api/postgrest')
}
export async function apiGetPostgRESTInstance(id) {
  return fetchWithAuth(`/api/postgrest/${id}`)
}
export async function apiCreatePostgREST(body) {
  return fetchWithAuth('/api/postgrest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeletePostgREST(id) {
  return fetchWithAuth(`/api/postgrest/${id}`, { method: 'DELETE' })
}

// Mage
export async function apiGetMage() {
  return fetchWithAuth('/api/mage')
}
export async function apiGetMageInstance(id) {
  return fetchWithAuth(`/api/mage/${id}`)
}
export async function apiCreateMage(body) {
  return fetchWithAuth('/api/mage', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteMage(id) {
  return fetchWithAuth(`/api/mage/${id}`, { method: 'DELETE' })
}

// MinIO
export async function apiGetMinIO() {
  return fetchWithAuth('/api/minio')
}
export async function apiGetMinIOInstance(id) {
  return fetchWithAuth(`/api/minio/${id}`)
}
export async function apiCreateMinIO(body) {
  return fetchWithAuth('/api/minio', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteMinIO(id) {
  return fetchWithAuth(`/api/minio/${id}`, { method: 'DELETE' })
}

// Groups
export async function apiGetGroups() {
  return fetchWithAuth('/api/groups')
}

export async function apiCreateGroup(body) {
  return fetchWithAuth('/api/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function apiDeleteGroup(id) {
  return fetchWithAuth(`/api/groups/${id}`, { method: 'DELETE' })
}

export async function apiGetGroupMembers(groupId) {
  return fetchWithAuth(`/api/groups/${groupId}/members`)
}

export async function apiAddGroupMember(groupId, userId) {
  return fetchWithAuth(`/api/groups/${groupId}/members`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  })
}

export async function apiRemoveGroupMember(groupId, userId) {
  return fetchWithAuth(`/api/groups/${groupId}/members/${userId}`, { method: 'DELETE' })
}

export async function apiGetGroupPermissions(groupId) {
  return fetchWithAuth(`/api/groups/${groupId}/permissions`)
}

export async function apiAddGroupPermission(groupId, body) {
  return fetchWithAuth(`/api/groups/${groupId}/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function apiRemoveGroupPermission(groupId, permId) {
  return fetchWithAuth(`/api/groups/${groupId}/permissions/${permId}`, { method: 'DELETE' })
}

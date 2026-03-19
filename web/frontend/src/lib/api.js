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

export async function apiGetInternalPostgres() {
  return fetchWithAuth('/api/postgres?internal=true')
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

// MariaDB
export async function apiGetMariaDB() {
  return fetchWithAuth('/api/mariadb')
}
export async function apiGetMariaDBInstance(id) {
  return fetchWithAuth(`/api/mariadb/${id}`)
}
export async function apiCreateMariaDB(body) {
  return fetchWithAuth('/api/mariadb', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteMariaDB(id) {
  return fetchWithAuth(`/api/mariadb/${id}`, { method: 'DELETE' })
}

// Qdrant
export async function apiGetQdrant() {
  return fetchWithAuth('/api/qdrant')
}
export async function apiGetQdrantInstance(id) {
  return fetchWithAuth(`/api/qdrant/${id}`)
}
export async function apiCreateQdrant(body) {
  return fetchWithAuth('/api/qdrant', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteQdrant(id) {
  return fetchWithAuth(`/api/qdrant/${id}`, { method: 'DELETE' })
}

// ClickHouse
export async function apiGetClickHouse() {
  return fetchWithAuth('/api/clickhouse')
}
export async function apiGetClickHouseInstance(id) {
  return fetchWithAuth(`/api/clickhouse/${id}`)
}
export async function apiCreateClickHouse(body) {
  return fetchWithAuth('/api/clickhouse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteClickHouse(id) {
  return fetchWithAuth(`/api/clickhouse/${id}`, { method: 'DELETE' })
}

// Ollama
export async function apiGetOllama() {
  return fetchWithAuth('/api/ollama')
}
export async function apiGetOllamaInstance(id) {
  return fetchWithAuth(`/api/ollama/${id}`)
}
export async function apiCreateOllama(body) {
  return fetchWithAuth('/api/ollama', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteOllama(id) {
  return fetchWithAuth(`/api/ollama/${id}`, { method: 'DELETE' })
}
export async function apiOllamaListModels(id) {
  return fetchWithAuth(`/api/ollama/${id}/models`)
}
export async function apiOllamaPullModel(id, name) {
  return fetchWithAuth(`/api/ollama/${id}/models/pull`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }),
  })
}
export async function apiOllamaPullStatus(id) {
  return fetchWithAuth(`/api/ollama/${id}/models/pull-status`)
}
export async function apiOllamaDeleteModel(id, name) {
  return fetchWithAuth(`/api/ollama/${id}/models`, {
    method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }),
  })
}
export async function apiOllamaChat(id, model, messages) {
  return fetchWithAuth(`/api/ollama/${id}/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model, messages }),
  })
}

// Superset
export async function apiGetSuperset() {
  return fetchWithAuth('/api/superset')
}
export async function apiGetSupersetInstance(id) {
  return fetchWithAuth(`/api/superset/${id}`)
}
export async function apiCreateSuperset(body) {
  return fetchWithAuth('/api/superset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteSuperset(id) {
  return fetchWithAuth(`/api/superset/${id}`, { method: 'DELETE' })
}

// Airflow
export async function apiGetAirflow() {
  return fetchWithAuth('/api/airflow')
}
export async function apiGetAirflowInstance(id) {
  return fetchWithAuth(`/api/airflow/${id}`)
}
export async function apiCreateAirflow(body) {
  return fetchWithAuth('/api/airflow', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteAirflow(id) {
  return fetchWithAuth(`/api/airflow/${id}`, { method: 'DELETE' })
}

// Hasura
export async function apiGetHasura() {
  return fetchWithAuth('/api/hasura')
}
export async function apiGetHasuraInstance(id) {
  return fetchWithAuth(`/api/hasura/${id}`)
}
export async function apiCreateHasura(body) {
  return fetchWithAuth('/api/hasura', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export async function apiDeleteHasura(id) {
  return fetchWithAuth(`/api/hasura/${id}`, { method: 'DELETE' })
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

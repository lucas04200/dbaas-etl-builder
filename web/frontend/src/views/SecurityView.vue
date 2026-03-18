<template>
  <div>
    <div class="page-head">
      <div class="page-head-text">
        <h2>Sécurité</h2>
        <p>Gérez les accès à votre espace DataForge</p>
      </div>
    </div>

    <div class="tabs">
      <div :class="['tab', { active: activeTab === 'users' }]" @click="activeTab = 'users'">Utilisateurs</div>
      <div :class="['tab', { active: activeTab === 'groups' }]" @click="activeTab = 'groups'">Groupes &amp; Permissions</div>
    </div>

    <UsersTab v-if="activeTab === 'users'" />
    <GroupsTab v-else />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UsersTab from '../components/security/UsersTab.vue'
import GroupsTab from '../components/security/GroupsTab.vue'

const activeTab = ref('users')
</script>

@description('Name of the Microsoft Foundry (AIServices) account.')
param accountName string

@description('When true, treat accountName as an existing Foundry account and skip account/project creation.')
param useExistingFoundry bool = false

@description('Name of the Foundry project (child of the account).')
param projectName string

@description('Region for the account and project.')
param location string

@description('Principal ID receiving data-plane access.')
param principalId string

@allowed([ 'User', 'ServicePrincipal' ])
param principalType string

@description('If true, create role assignments for principalId on the account.')
param assignRolesToPrincipal bool = true

@description('Model deployments to create on the account.')
param modelDeployments array

resource accountNew 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = if (!useExistingFoundry) {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource accountExisting 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = if (useExistingFoundry) {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = if (!useExistingFoundry) {
  parent: accountNew
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// Model deployments — created sequentially to avoid Cognitive Services
// 'another operation in progress' conflicts.
@batchSize(1)
resource deploymentsOnNew 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = [for d in modelDeployments: if (!useExistingFoundry) {
  parent: accountNew
  name: d.name
  sku: {
    name: d.skuName
    capacity: d.skuCapacity
  }
  properties: {
    model: {
      format: d.format
      name: d.model
      version: d.version
    }
  }
}]

@batchSize(1)
resource deploymentsOnExisting 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview' = [for d in modelDeployments: if (useExistingFoundry) {
  parent: accountExisting
  name: d.name
  sku: {
    name: d.skuName
    capacity: d.skuCapacity
  }
  properties: {
    model: {
      format: d.format
      name: d.model
      version: d.version
    }
  }
}]

// Built-in Azure RBAC role GUIDs.
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
var roleDefinitions = {
  cognitiveServicesUser:        'a97b65f3-24c7-4388-baec-2e87135dc908'
  cognitiveServicesOpenAIUser:  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  azureAIDeveloper:             '64702f94-c441-49e6-a78b-ef80e0188fee'
}

resource roleCogUserOnNew 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingFoundry && assignRolesToPrincipal && !empty(principalId)) {
  name: guid(accountNew.id, principalId, roleDefinitions.cognitiveServicesUser)
  scope: accountNew
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
    principalId: principalId
    principalType: principalType
  }
}

resource roleOpenAIUserOnNew 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingFoundry && assignRolesToPrincipal && !empty(principalId)) {
  name: guid(accountNew.id, principalId, roleDefinitions.cognitiveServicesOpenAIUser)
  scope: accountNew
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
    principalId: principalId
    principalType: principalType
  }
}

resource roleAIDeveloperOnNew 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!useExistingFoundry && assignRolesToPrincipal && !empty(principalId)) {
  name: guid(accountNew.id, principalId, roleDefinitions.azureAIDeveloper)
  scope: accountNew
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.azureAIDeveloper)
    principalId: principalId
    principalType: principalType
  }
}

output accountName     string = accountName
output projectName     string = useExistingFoundry ? '' : project.name
output accountEndpoint string = 'https://${accountName}.services.ai.azure.com/'
output projectEndpoint string = useExistingFoundry ? '' : 'https://${accountName}.services.ai.azure.com/api/projects/${project.name}'
output modelDeployments array = [for (d, i) in modelDeployments: {
  name: d.name
  model: d.model
  version: d.version
  sku: d.skuName
  capacity: d.skuCapacity
}]

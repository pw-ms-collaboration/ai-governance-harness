metadata name = 'AI Governance Harness Hackathon MVP'
metadata description = 'Deploys the synthetic-data chat and MCP services behind Entra and APIM for a time-boxed demo.'

targetScope = 'resourceGroup'

@description('Short lowercase prefix for demo resource names.')
@minLength(3)
@maxLength(8)
param resourcePrefix string

@description('Azure region for the demo resources.')
@allowed([
  'australiaeast'
  'australiasoutheast'
])
param location string

@description('Name of the existing APIM service to reuse.')
param apimServiceName string

@description('APIM outbound IPv4 address in CIDR notation, for example 203.0.113.4/32.')
param apimOutboundIpv4Cidr string

@description('Existing Foundry Cognitive Services account name.')
param foundryAccountName string

@description('Existing Foundry project name under the account.')
param foundryProjectName string

@description('Foundry project endpoint used by the chat service.')
param foundryProjectEndpoint string

@description('Foundry model deployment name used by the chat service.')
param foundryModelDeploymentName string

@description('Name of the existing Foundry Prompt Agent invoked by the chat service.')
param foundryAgentName string

@description('Container image tag already pushed to the registry created by this template.')
param imageTag string

@description('Entra application client ID for the chat UI EasyAuth registration.')
param chatAuthClientId string

@description('Entra client secret for the chat UI EasyAuth registration.')
@secure()
param chatAuthClientSecret string

@description('Allowed token audience for the chat UI EasyAuth registration.')
param chatAuthAudience string

@description('Entra application client ID that represents the MCP API audience.')
param mcpApiClientId string

@description('Allowed token audience for the MCP API.')
param mcpApiAudience string

@description('Required application role expected by the MCP service.')
param mcpRequiredRole string

@description('Application role required to read MCP governance snapshots.')
param mcpSnapshotRole string = 'Mcp.Governance.Read'

@description('Foundry agent identity client ID allowed to call the MCP backend.')
param foundryAgentIdentityClientId string

@description('Application Insights connection string for privacy-filtered operational telemetry.')
@secure()
param appInsightsConnectionString string

@description('Set true only when the deployer is authorized to create the ACR pull and Foundry workload role assignments.')
param shouldCreateRoleAssignments bool

var normalizedPrefix = toLower(replace(resourcePrefix, '-', ''))
var registryName = take('${normalizedPrefix}${uniqueString(subscription().id, resourceGroup().id)}', 50)
var chatAppName = '${resourcePrefix}-chat-demo'
var mcpAppName = '${resourcePrefix}-mcp-demo'
var acaEnvironmentName = '${resourcePrefix}-aca-env'
var pullIdentityName = '${resourcePrefix}-acr-pull'
var foundryIdentityName = '${resourcePrefix}-foundry'
var apimApiName = '${resourcePrefix}-mcp'
var apimApiPath = '${resourcePrefix}-mcp'
var apimGovernanceApiName = '${resourcePrefix}-governance'
var tenantId = tenant().tenantId
var issuer = '${environment().authentication.loginEndpoint}${tenantId}/v2.0'
var apimMcpUrl = '${apim.properties.gatewayUrl}/${apimApiPath}/mcp'
var apimSnapshotUrl = '${apim.properties.gatewayUrl}/${apimGovernanceApiName}/governance/snapshot'
var image = '${registry.properties.loginServer}/ai-governance-harness:${imageTag}'
var tags = {
  application: 'ai-governance-harness'
  environment: 'hackathon'
  dataClass: 'synthetic'
}

module registryPullIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'registryPullIdentity'
  params: {
    name: pullIdentityName
    location: location
    enableTelemetry: false
    tags: tags
  }
}

module foundryWorkloadIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'foundryWorkloadIdentity'
  params: {
    name: foundryIdentityName
    location: location
    enableTelemetry: false
    tags: tags
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-06-01-preview' existing = {
  name: registryName
}

resource registryPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (shouldCreateRoleAssignments) {
  name: guid(registry.id, pullIdentityName, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
    principalId: registryPullIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

module managedEnvironment 'br/public:avm/res/app/managed-environment:0.16.0' = {
  name: 'containerAppsEnvironment'
  params: {
    name: acaEnvironmentName
    location: location
    internal: false
    publicNetworkAccess: 'Enabled'
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    zoneRedundant: false
    enableTelemetry: false
    tags: tags
  }
}

resource apim 'Microsoft.ApiManagement/service@2024-05-01' existing = {
  name: apimServiceName
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' existing = {
  parent: foundryAccount
  name: foundryProjectName
}

resource foundryWorkloadRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (shouldCreateRoleAssignments) {
  name: guid(foundryProject.id, foundryIdentityName, 'Cognitive Services User')
  scope: foundryProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
    principalId: foundryWorkloadIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

module mcpApp 'br/public:avm/res/app/container-app:0.23.0' = {
  name: 'mcpContainerApp'
  params: {
    name: mcpAppName
    location: location
    environmentResourceId: managedEnvironment.outputs.resourceId
    activeRevisionsMode: 'Single'
    ingressExternal: true
    ingressAllowInsecure: false
    ingressTargetPort: 8001
    ingressTransport: 'http'
    ipSecurityRestrictions: [
      {
        name: 'allow-apim-egress'
        description: 'Allow the existing APIM gateway only.'
        action: 'Allow'
        ipAddressRange: apimOutboundIpv4Cidr
      }
    ]
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 1
    }
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [registryPullIdentity.outputs.resourceId]
    }
    registries: [
      {
        server: registry.properties.loginServer
        identity: registryPullIdentity.outputs.resourceId
      }
    ]
    authConfig: {
      platform: {
        enabled: true
      }
      globalValidation: {
        unauthenticatedClientAction: 'Return401'
        excludedPaths: [
          '/health/live'
          '/health/ready'
          '/.well-known/oauth-protected-resource'
          '/.well-known/oauth-protected-resource/mcp'
        ]
      }
      httpSettings: {
        requireHttps: true
      }
      identityProviders: {
        azureActiveDirectory: {
          enabled: true
          registration: {
            clientId: mcpApiClientId
            openIdIssuer: issuer
          }
          validation: {
            allowedAudiences: [mcpApiAudience, mcpApiClientId]
            defaultAuthorizationPolicy: {
              allowedApplications: [foundryAgentIdentityClientId, foundryWorkloadIdentity.outputs.clientId]
            }
          }
        }
      }
    }
    secrets: [
      {
        name: 'appinsights-connection'
        value: appInsightsConnectionString
      }
    ]
    containers: [
      {
        name: 'mcp'
        image: image
        command: ['ai-governance-mcp']
        resources: {
          cpu: 1
          memory: '2Gi'
        }
        env: [
          { name: 'MCP_TRANSPORT', value: 'streamable-http' }
          { name: 'MCP_HOST', value: '0.0.0.0' }
          { name: 'MCP_PORT', value: '8001' }
          { name: 'MCP_PATH', value: '/mcp' }
          { name: 'MCP_HOSTED', value: 'true' }
          { name: 'MCP_ENVIRONMENT', value: 'production' }
          { name: 'AZURE_AI_PROJECT_REGION', value: location }
          { name: 'MCP_AUTH_TENANT_ID', value: tenantId }
          { name: 'MCP_AUTH_AUDIENCE', value: mcpApiAudience }
          { name: 'MCP_AUTH_AUDIENCES', value: '${mcpApiAudience},${mcpApiClientId}' }
          { name: 'MCP_AUTH_REQUIRED_ROLE', value: mcpRequiredRole }
          { name: 'MCP_HOSTED_TOOL_CLIENT_ID', value: foundryAgentIdentityClientId }
          { name: 'MCP_AUTH_SNAPSHOT_ROLE', value: mcpSnapshotRole }
          { name: 'MCP_RESOURCE_URL', value: apimMcpUrl }
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-connection' }
        ]
      }
    ]
    enableTelemetry: false
    tags: tags
  }
  dependsOn: shouldCreateRoleAssignments ? [registryPullRoleAssignment] : []
}

module chatApp 'br/public:avm/res/app/container-app:0.23.0' = {
  name: 'chatContainerApp'
  params: {
    name: chatAppName
    location: location
    environmentResourceId: managedEnvironment.outputs.resourceId
    activeRevisionsMode: 'Single'
    ingressExternal: true
    ingressAllowInsecure: false
    ingressTargetPort: 8080
    ingressTransport: 'http'
    scaleSettings: {
      minReplicas: 1
      maxReplicas: 1
    }
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: [
        registryPullIdentity.outputs.resourceId
        foundryWorkloadIdentity.outputs.resourceId
      ]
    }
    registries: [
      {
        server: registry.properties.loginServer
        identity: registryPullIdentity.outputs.resourceId
      }
    ]
    authConfig: {
      platform: {
        enabled: true
      }
      globalValidation: {
        unauthenticatedClientAction: 'RedirectToLoginPage'
        redirectToProvider: 'azureActiveDirectory'
        excludedPaths: [
          '/health/live'
          '/health/ready'
        ]
      }
      httpSettings: {
        requireHttps: true
      }
      login: {
        allowedExternalRedirectUrls: [
          'https://${chatAppName}.${managedEnvironment.outputs.defaultDomain}'
        ]
      }
      identityProviders: {
        azureActiveDirectory: {
          enabled: true
          registration: {
            clientId: chatAuthClientId
            clientSecretSettingName: 'chat-auth-secret'
            openIdIssuer: issuer
          }
          validation: {
            allowedAudiences: [chatAuthAudience]
          }
        }
      }
    }
    secrets: [
      {
        name: 'appinsights-connection'
        value: appInsightsConnectionString
      }
      {
        name: 'chat-auth-secret'
        value: chatAuthClientSecret
      }
    ]
    containers: [
      {
        name: 'chat'
        image: image
        command: ['ai-governance-chat']
        resources: {
          cpu: 1
          memory: '2Gi'
        }
        env: [
          { name: 'CHAT_HOST', value: '0.0.0.0' }
          { name: 'CHAT_PORT', value: '8080' }
          { name: 'CHAT_HOSTED', value: 'true' }
          { name: 'CHAT_AUTH_TENANT_ID', value: tenantId }
          { name: 'CHAT_AUTH_AUDIENCE', value: chatAuthAudience }
          { name: 'MOCK_IDENTITY_ENABLED', value: 'false' }
          { name: 'CHAT_ALLOWED_ORIGINS', value: 'https://${chatAppName}.${managedEnvironment.outputs.defaultDomain}' }
          { name: 'MCP_SERVER_URL', value: apimMcpUrl }
          { name: 'MCP_GOVERNANCE_SNAPSHOT_URL', value: apimSnapshotUrl }
          { name: 'MCP_GOVERNANCE_SNAPSHOT_AUDIENCE', value: mcpApiAudience }
          { name: 'CHAT_USE_PROMPT_AGENT', value: 'true' }
          { name: 'FOUNDRY_AGENT_NAME', value: foundryAgentName }
          { name: 'MCP_HOSTED', value: 'true' }
          { name: 'MCP_ENVIRONMENT', value: 'production' }
          { name: 'GOVERNANCE_ENABLED', value: 'true' }
          { name: 'GOVERNANCE_ENVIRONMENT', value: 'production' }
          { name: 'GOVERNANCE_SANDBOX_PROVIDER', value: 'none' }
          { name: 'AZURE_TENANT_ID', value: tenantId }
          { name: 'AZURE_CLIENT_ID', value: foundryWorkloadIdentity.outputs.clientId }
          { name: 'AZURE_CREDENTIAL_MODE', value: 'default' }
          { name: 'AZURE_AI_PROJECT_ENDPOINT', value: foundryProjectEndpoint }
          { name: 'AZURE_AI_PROJECT_REGION', value: location }
          { name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME', value: foundryModelDeploymentName }
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-connection' }
        ]
      }
    ]
    enableTelemetry: false
    tags: tags
  }
  dependsOn: shouldCreateRoleAssignments ? [registryPullRoleAssignment] : []
}

resource mcpApi 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: apimApiName
  properties: {
    type: 'mcp'
    displayName: 'AI Governance Harness MCP'
    description: 'Synthetic-data MCP tools for the hackathon demo.'
    path: apimApiPath
    protocols: ['https']
    serviceUrl: 'https://${mcpApp.outputs.fqdn}'
    subscriptionRequired: false
    mcpProperties: {
      transportType: 'streamable'
      endpoints: [
        {
          name: 'message'
          uriTemplate: '/mcp'
        }
      ]
    }
  }
}

resource mcpApiPolicy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = {
  parent: mcpApi
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: format('''<policies>
  <inbound>
    <base />
    <validate-jwt header-name="Authorization" require-scheme="Bearer" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">
      <openid-config url="{0}/.well-known/openid-configuration" />
      <audiences>
        <audience>{1}</audience>
        <audience>{2}</audience>
      </audiences>
      <required-claims>
        <claim name="roles" match="any"><value>{3}</value></claim>
      </required-claims>
    </validate-jwt>
    <rate-limit-by-key calls="120" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
  </inbound>
  <backend>
    <forward-request />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>''', issuer, mcpApiAudience, mcpApiClientId, mcpRequiredRole)
  }
}

module governanceApi 'apim-governance-api.bicep' = {
  name: 'governanceSnapshotApi'
  params: {
    apimServiceName: apimServiceName
    apimApiName: apimGovernanceApiName
    mcpAppFqdn: mcpApp.outputs.fqdn
    tenantId: tenantId
    mcpApiAudience: mcpApiAudience
    mcpApiClientId: mcpApiClientId
    snapshotRole: mcpSnapshotRole
  }
}

@description('ACR login server for image publication and Container Apps pull configuration.')
output registryLoginServer string = registry.properties.loginServer

@description('Public chat endpoint; Entra authentication is required.')
output chatEndpoint string = 'https://${chatApp.outputs.fqdn}'

@description('APIM MCP endpoint used by the Foundry agent.')
output mcpGatewayEndpoint string = apimMcpUrl

@description('MCP backend endpoint protected by APIM source IP and Entra token validation.')
output mcpBackendEndpoint string = 'https://${mcpApp.outputs.fqdn}/mcp'
metadata name = 'AI Governance Harness APIM MCP API'
metadata description = 'Creates the APIM MCP API and JWT policy for the already-deployed MCP Container App.'

targetScope = 'resourceGroup'

@description('Name of the existing API Management service.')
param apimServiceName string

@description('Name of the MCP API in API Management.')
param apimApiName string

@description('Public path of the MCP API in API Management.')
param apimApiPath string

@description('FQDN of the already-deployed MCP Container App.')
param mcpAppFqdn string

@description('Tenant ID used to validate bearer tokens.')
param tenantId string

@description('Allowed token audience for the MCP API.')
param mcpApiAudience string

@description('MCP API application client ID, also accepted as an Entra token audience.')
param mcpApiClientId string

resource apim 'Microsoft.ApiManagement/service@2024-05-01' existing = {
  name: apimServiceName
}

var issuer = '${environment().authentication.loginEndpoint}${tenantId}/v2.0'

resource mcpApi 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = {
  parent: apim
  name: apimApiName
  properties: {
    type: 'mcp'
    displayName: 'AI Governance Harness MCP'
    description: 'Synthetic-data MCP tools for the hackathon demo.'
    path: apimApiPath
    protocols: ['https']
    serviceUrl: 'https://${mcpAppFqdn}'
    subscriptionRequired: false
    mcpProperties: {
      transportType: 'streamable'
      endpoints: any({
        message: {
          name: 'message'
          uriTemplate: '/mcp'
        }
      })
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
</policies>''', issuer, mcpApiAudience, mcpApiClientId)
  }
}
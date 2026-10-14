metadata name = 'AI Governance Harness APIM Governance API'
metadata description = 'Publishes the authenticated, read-only MCP governance snapshot.'

targetScope = 'resourceGroup'

@description('Name of the existing API Management service.')
param apimServiceName string

@description('Name and public path of the governance API.')
param apimApiName string

@description('FQDN of the MCP Container App.')
param mcpAppFqdn string

@description('Tenant ID used to validate bearer tokens.')
param tenantId string

@description('Allowed token audience for the MCP API.')
param mcpApiAudience string

@description('MCP API client ID, also accepted as a token audience.')
param mcpApiClientId string

@description('Application role required to read governance snapshots.')
param snapshotRole string

resource apim 'Microsoft.ApiManagement/service@2024-05-01' existing = {
  name: apimServiceName
}

resource governanceApi 'Microsoft.ApiManagement/service/apis@2024-05-01' = {
  parent: apim
  name: apimApiName
  properties: {
    type: 'http'
    displayName: 'AI Governance Harness Observability'
    description: 'Authenticated read-only governance metadata; no member data.'
    path: apimApiName
    protocols: ['https']
    serviceUrl: 'https://${mcpAppFqdn}'
    subscriptionRequired: false
  }
}

resource snapshotOperation 'Microsoft.ApiManagement/service/apis/operations@2024-05-01' = {
  parent: governanceApi
  name: 'read-governance-snapshot'
  properties: {
    displayName: 'Read governance snapshot'
    method: 'GET'
    urlTemplate: '/governance/snapshot'
    responses: [
      { statusCode: 200 }
    ]
  }
}

var issuer = '${environment().authentication.loginEndpoint}${tenantId}/v2.0'

resource governancePolicy 'Microsoft.ApiManagement/service/apis/policies@2024-05-01' = {
  parent: governanceApi
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
  <backend><forward-request /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>''', issuer, mcpApiAudience, mcpApiClientId, snapshotRole)
  }
}
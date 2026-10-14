metadata name = 'AI Governance Harness ACR Bootstrap'
metadata description = 'Creates the container registry required to push the application image before deploying the full hackathon MVP.'

targetScope = 'resourceGroup'

@description('Short lowercase prefix matching the full deployment.')
@minLength(3)
@maxLength(8)
param resourcePrefix string

@description('Azure region for the container registry.')
@allowed([
  'australiaeast'
  'australiasoutheast'
])
param location string

var normalizedPrefix = toLower(replace(resourcePrefix, '-', ''))
var registryName = take('${normalizedPrefix}${uniqueString(subscription().id, resourceGroup().id)}', 50)
var tags = {
  application: 'ai-governance-harness'
  environment: 'hackathon'
  dataClass: 'synthetic'
}

module registry 'br/public:avm/res/container-registry/registry:0.13.1' = {
  name: 'containerRegistryBootstrap'
  params: {
    name: registryName
    location: location
    acrSku: 'Basic'
    acrAdminUserEnabled: false
    enableTelemetry: false
    tags: tags
  }
}

output registryName string = registryName
output loginServer string = registry.outputs.loginServer
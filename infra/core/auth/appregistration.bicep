extension microsoftGraphV1

@description('Specifies the name of cloud environment to run this deployment in.')
param cloudEnvironment string = environment().name

@description('The unique name for the application registration (used for idempotency)')
param appUniqueName string

// NOTE: Microsoft Graph Bicep file deployment is only supported in Public Cloud
@description('Audience uris for public and national clouds')
param audiences object = {
  AzureCloud: {
    uri: 'api://AzureADTokenExchange'
  }
  AzureUSGovernment: {
    uri: 'api://AzureADTokenExchangeUSGov'
  }
  USNat: {
    uri: 'api://AzureADTokenExchangeUSNat'
  }
  USSec: {
    uri: 'api://AzureADTokenExchangeUSSec'
  }
  AzureChinaCloud: {
    uri: 'api://AzureADTokenExchangeChina'
  }
}

@description('Specifies the ID of the user-assigned managed identity.')
param webAppIdentityId string

@description('Specifies the unique name for the client application.')
param clientAppName string

@description('Specifies the display name for the client application')
param clientAppDisplayName string

@description('Existing Entra ID application (client) ID to reuse for authentication. Leave empty to create a new app registration.')
param existingClientAppId string = ''

@description('Existing Entra ID identifier URI to reuse for authentication. Leave empty to default to api://<clientId>.')
param existingIdentifierUri string = ''

param serviceManagementReference string = ''

param issuer string

param webAppEndpoint string

// Combine default scope with custom scopes
var defaultScopeValue = 'user_impersonation'
var defaultScopeId = guid(appUniqueName, 'default-scope', defaultScopeValue)

var userImpersonationScope = {
    adminConsentDescription: 'Allow the application to access the API on behalf of the signed-in user'
    adminConsentDisplayName: 'Access application as user'
    id: defaultScopeId
    isEnabled: true
    type: 'User'
    userConsentDescription: 'Allow the application to access the API on behalf of the signed-in user'
    userConsentDisplayName: 'Access application as user'
    value: defaultScopeValue
}

var allScopes = [
  userImpersonationScope
]

var useExistingApp = !empty(existingClientAppId)
var generatedIdentifierUri = 'api://${appUniqueName}-${uniqueString(subscription().id, resourceGroup().id, appUniqueName)}'
var fallbackIdentifierUri = !empty(existingIdentifierUri) ? existingIdentifierUri : (!empty(existingClientAppId) ? 'api://${existingClientAppId}' : '')
var identifierUri = useExistingApp ? fallbackIdentifierUri : generatedIdentifierUri

resource appRegistration 'Microsoft.Graph/applications@v1.0' = if (!useExistingApp) {
  uniqueName: clientAppName
  displayName: clientAppDisplayName
  signInAudience: 'AzureADMyOrg'
  serviceManagementReference: empty(serviceManagementReference) ? null : serviceManagementReference
  identifierUris: [identifierUri]
  api: {
    oauth2PermissionScopes: allScopes
    requestedAccessTokenVersion: 2
    // Not doing preauthorized apps
  }
  web: {
    redirectUris: [
      '${webAppEndpoint}/.auth/login/aad/callback'
    ]
    implicitGrantSettings: { enableIdTokenIssuance: true }
  }
  requiredResourceAccess: [
  {
      // Microsoft Graph permissions
      resourceAppId: '00000003-0000-0000-c000-000000000000'
      resourceAccess: [
        {
          // User.Read delegated permission
          id: 'e1fe6dd8-ba31-4d61-89e7-88639da4683d'
          type: 'Scope'
        }
      ]
    }
  ]

}

resource appServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = if (!useExistingApp) {
  appId: appRegistration.appId
}

resource federatedIdentityCredential 'Microsoft.Graph/applications/federatedIdentityCredentials@v1.0' = if (!useExistingApp) {
  name: '${appRegistration.uniqueName}/miAsFic'
  audiences: [
    audiences[cloudEnvironment].uri
  ]
  issuer: issuer
  subject: webAppIdentityId
}

output clientAppId string = useExistingApp ? existingClientAppId : appRegistration.appId
output clientSpId string = useExistingApp ? '' : appServicePrincipal.id

@description('The identifier URI of the application - returns the actual URI that was set')
output identifierUri string = identifierUri

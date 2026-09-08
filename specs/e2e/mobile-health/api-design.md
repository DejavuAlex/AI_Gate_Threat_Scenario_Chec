# Mobile Clinical Companion API Design

## Link resolution

`POST /v1/mobile/links/resolve` accepts only allowlisted route names and opaque identifiers, then performs server-side tenant and object authorization.

## Offline synchronization

`POST /v1/mobile/sync` returns the minimum assigned data with an expiry timestamp. The client reports secure-purge completion after logout.

## Step-up authentication

`POST /v1/mobile/step-up` exchanges a recent strong platform-biometric assertion for a short-lived server token. High-risk write APIs require this token.

# Mobile Clinical Companion Data Model

## OfflineClinicalRecord

- opaque patient and assignment identifiers
- encrypted clinical payload
- authorization scope and expiry
- synchronization version
- purge-required flag

## MobileSession

- device-bound key reference
- biometric policy level
- server session expiry
- step-up token expiry

Raw biometric templates and plaintext clinical values are never stored.

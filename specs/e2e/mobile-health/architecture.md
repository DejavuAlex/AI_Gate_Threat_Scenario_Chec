# Mobile Clinical Companion Architecture

## Link routing

G1-MOBILE-001 is implemented with apple-app-site-association and assetlinks.json. Android uses an intent filter autoVerify rule, and the universal link router applies a deep-link route allowlist before backend authorization.

## Offline storage

G1-MOBILE-002 uses Android Keystore or iOS Keychain to wrap the encrypted SQLite key. Every cache file has a backup exclusion flag and sensitive views use screen capture protection.

## Biometric enforcement

G1-MOBILE-003 uses BiometricPrompt BIOMETRIC_STRONG on Android and a LocalAuthentication policy on iOS. Biometric key invalidation and a server step-up token protect high-risk actions.

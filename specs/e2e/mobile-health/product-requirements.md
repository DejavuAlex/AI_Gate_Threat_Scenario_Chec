# Mobile Clinical Companion Product Requirements

## Scope

Clinicians receive a clinical deep link that opens an authorized patient workflow in the mobile application. The application supports offline clinical data so a clinician can view assigned records during a network interruption.

系统支持用户通过 clinical deep link 和 universal link 打开已授权的患者页面。

A clinician may use biometric sign-in and Face ID login to unlock the application after initial server authentication.

系统支持用户通过 biometric sign-in、Face ID login 或 fingerprint unlock 解锁会话。

## Success criteria

- External links open only the intended, authorized clinical route.
- Offline records remain protected on a lost device.
- Biometric convenience does not weaken server-side session controls.

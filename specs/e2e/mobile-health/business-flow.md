# Mobile Clinical Companion Business Flow

1. The notification service sends an approved app link for an assigned clinical task.
2. The mobile application authorizes the route and patient identifier with the backend.
3. The application writes an encrypted patient data cache for approved offline use.
4. The user later performs biometric sign-in to unlock the device-bound session.
5. Logout purges cached records and invalidates local and server credentials.

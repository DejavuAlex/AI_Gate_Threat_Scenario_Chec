# Cloud Collaboration SaaS Data Model

## StoredObject

- `object_id`: opaque identifier
- `tenant_id`: mandatory authorization partition
- `bucket_name`: server-owned private bucket
- `object_key`: random server-generated key
- `scan_status`: quarantined, clean, or rejected
- `sha256`: immutable upload checksum
- `created_by`: authenticated principal

No cloud credential is stored with a business object.

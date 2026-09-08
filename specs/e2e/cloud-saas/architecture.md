# Cloud Collaboration SaaS Architecture

## Object storage boundary

The implementation of G1-CLOUD-SAMPLE-001 uses an S3 object-storage bucket. Public access is blocked, object ACL changes are denied, and the API generates a presigned URL only after authorization.

## Cloud identity boundary

The implementation of G1-CLOUD-SAMPLE-002 uses a least-privilege IAM role. Workers exchange workload identity for STS credentials, and sensitive configuration is held in Vault with KMS protection.

# Cloud Collaboration SaaS API Design

## Upload API

`POST /v1/workspaces/{workspaceId}/objects` initiates multipart upload to a private bucket. The endpoint validates authorization, declared MIME type, file size, and object ownership.

## Download API

`POST /v1/objects/{objectId}/signed-url` returns a signed URL with a five-minute expiry only after tenant authorization and malware-scan completion.

## Cloud API client

The worker uses its IAM role and short-lived STS credential. Static access key and secret key values are forbidden.

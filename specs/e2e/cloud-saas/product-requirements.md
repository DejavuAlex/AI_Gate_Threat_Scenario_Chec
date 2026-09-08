# Cloud Collaboration SaaS Product Requirements

## Scope

The SaaS product allows each customer to upload documents to cloud object storage. Every uploaded file is stored in a private S3 bucket and later downloaded through the application.

系统支持客户执行 file upload 并将文件保存到 cloud storage 和 object storage。

The backend also calls a cloud API using a short-lived access token and a scoped service credential so that it can process stored objects.

系统调用 cloud API 时使用 access token 和 service credential。

## Success criteria

- A customer can complete a file upload and retrieve the resulting object.
- Cloud API operations remain attributable to one tenant and one service identity.

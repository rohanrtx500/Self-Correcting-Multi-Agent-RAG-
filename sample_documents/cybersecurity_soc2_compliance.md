# Enterprise Cybersecurity & SOC2 Compliance Handbook

## 1. Data Encryption Standards
- **Data at Rest**: Encrypted using AES-256-GCM across all database volumes and S3 storage buckets.
- **Data in Transit**: Mandatory TLS 1.3 encryption for all external and intra-service gRPC/REST communication.
- **Key Management**: Keys rotated every 90 days via AWS KMS with automatic key rotation enabled.

## 2. Access Control & IAM Policies
- **Authentication**: Multi-Factor Authentication (MFA) required for all internal systems via Okta SSO with hardware security key (YubiKey) enforcement.
- **Principle of Least Privilege**: Access roles reviewed quarterly by the Security Control Board.
- **Password Policy**: Minimum 16 characters, enforced expiration every 180 days.

## 3. Incident Response & Response SLAs
- **Critical Vulnerability Remediation (P1)**: Response SLA < 1 hour; Fix deployment SLA < 12 hours.
- **High Vulnerability Remediation (P2)**: Fix deployment SLA < 72 hours.
- **Chief Information Security Officer (CISO)**: David K. Stern (`security@company.com`).

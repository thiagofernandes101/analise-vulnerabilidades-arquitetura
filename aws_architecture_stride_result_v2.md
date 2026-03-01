# AWS SEI/SIP Architecture
## Overview
Users access the SEI/SIP application through AWS CloudFront and WAF, protected by AWS Shield. The application is deployed across multiple Availability Zones within a Virtual Private Cloud, utilizing Elastic Load Balancers, Auto Scaling Groups, and various AWS services for data storage and caching.

## Components & Threat Analysis

| Component | Provider | Service | Role | STRIDE Threats | Overall Risk |
|---|---|---|---|---|---|
| Usuários SEI |  |  | End users | Spoofing: Phishing attacks · Tampering: Malicious code injection | High |
| AWS Shield | AWS | Security | DDoS protection | None | Low |
| Amazon CloudFront | AWS | CDN | Content delivery | Spoofing: Cache poisoning · Tampering: Malicious content injection | High |
| AWS WAF | AWS | Firewall | Web application firewall | Tampering: SQL injection · Spoofing: Cross-site scripting | High |
| AWS CloudTrail | AWS | Logging | Audit logging | Tampering: Log deletion · Spoofing: Log forgery | Medium |
| AWS Key Management Service | AWS | Encryption | Key management | Tampering: Key compromise · Spoofing: Unauthorized key usage | High |
| AWS Backup | AWS | Backup | Data backup | Tampering: Backup deletion · Spoofing: Unauthorized backup restoration | Medium |
| Amazon CloudWatch | AWS | Monitoring | Performance and security monitoring | Tampering: Alarm manipulation · Spoofing: False metric reporting | Medium |
| Amazon Simple Email Service (SES) | AWS | Email | Email notifications | Spoofing: Phishing emails · Tampering: Email content modification | High |
| Virtual Private Cloud | AWS | Networking | Network isolation | Spoofing: Unauthorized network access · Tampering: Network configuration changes | High |
| Availability Zone A | AWS | Compute | High availability | None | Low |
| Availability Zone B | AWS | Compute | High availability | None | Low |
| Availability Zone C | AWS | Compute | High availability | None | Low |
| Public Subnet | AWS | Networking | Public network access | Spoofing: Unauthorized access · Tampering: Network traffic redirection | High |
| Application Load Balancer | AWS | Load Balancing | Traffic distribution | Spoofing: Session hijacking · Tampering: Malicious traffic routing | High |
| Private Subnet | AWS | Networking | Private network access | Spoofing: Unauthorized access · Tampering: Network configuration changes | Medium |
| SEI / SIP | AWS | Compute | Application servers | Spoofing: Unauthorized access · Tampering: Code injection | High |
| Auto Scaling (API Server) | AWS | Compute | Scalable application servers | Spoofing: Unauthorized access · Tampering: Code injection | High |
| Amazon Elastic File System (NFS) Multi-AZ | AWS | Storage | Shared file storage | Tampering: Data modification · Spoofing: Unauthorized data access | High |
| Amazon RDS (Primary) | AWS | Database | Primary database | Tampering: Data corruption · Spoofing: Unauthorized data access | High |
| Amazon RDS (Secondary) | AWS | Database | Secondary database | Tampering: Data corruption · Spoofing: Unauthorized data access | High |
| Amazon ElastiCache (memcached) Multi-AZ | AWS | Caching | In-memory caching | Tampering: Cache poisoning · Spoofing: Unauthorized cache access | High |
| Solr | AWS | Search | Search functionality | Tampering: Data manipulation · Spoofing: Unauthorized search access | High |
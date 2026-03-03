# Azure API Management and Logic Apps Architecture

## Overview
This architecture depicts a system where external clients interact with backend services through Azure API Management. Clients authenticate with Microsoft Entra ID, send HTTP requests to the API gateway, which routes them to Logic Apps for workflow orchestration. Logic Apps then interact with various backend systems like Azure services, SaaS, and web services. The developer portal provides API documentation to consumers. The primary internet-facing entry point is the API gateway.

## Components & Threat Analysis

| Component | Provider | Service | Role | STRIDE Threats | Overall Risk |
|---|---|---|---|---|---|
| Microsoft Entra | Microsoft | Identity and Access Management | Authentication | Unauthorised access possible — enable Entra ID MFA. · Account enumeration possible — configure sign-in logs. | High |
| API gateway | Microsoft | API Management | Entry point and traffic management | Unauthorised access possible — configure API policies. · Data leakage possible — implement request/response transformations. · Spoofing possible — use JWT validation. | High |
| Logic Apps | Microsoft | Workflow and Orchestration | Business logic execution | Unauthorised access possible — restrict access to Logic Apps. · Data leakage possible — encrypt sensitive data. · Tampering possible — use run history auditing. | Medium |
| Developer portal | Microsoft | API Management | API documentation and discovery | Unauthorised access possible — restrict portal access. · Information disclosure possible — limit published API details. | Medium |
| Azure services | Microsoft | Cloud Services | Backend data and functionality | Unauthorised access possible — implement Azure RBAC. · Data leakage possible — configure network security groups. | Medium |
| SaaS services | Third-party | Cloud Services | Backend data and functionality | Unauthorised access possible — use secure SaaS connectors. · Data leakage possible — review SaaS security settings. | Medium |
| Web services (REST) | Third-party | Cloud Services | Backend data and functionality | Unauthorised access possible — implement API key authentication. · Data leakage possible — use HTTPS for transport. | Medium |
| Web services (SOAP) | Third-party | Cloud Services | Backend data and functionality | Unauthorised access possible — implement WS-Security. · Data leakage possible — use HTTPS for transport. | Medium |
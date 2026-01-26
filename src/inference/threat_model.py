import logging
from pathlib import Path
from typing import List, Dict, Any
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class ThreatMapper:
    """
    Maps architecture components to STRIDE threats.
    
    STRIDE stands for:
    - Spoofing: Impersonating users or systems
    - Tampering: Modifying data or code maliciously
    - Repudiation: Denying actions without audit trail
    - Information Disclosure: Exposing sensitive data
    - Denial of Service: Making services unavailable
    - Elevation of Privilege: Gaining unauthorized access
    """

    # Comprehensive STRIDE threat knowledge base organized by service category
    THREAT_KB = {
        # ============== AWS COMPUTE ==============
        'aws_amazon_ec2': [
            "Spoofing: Unauthorized SSH/RDP access via compromised credentials.",
            "Tampering: Malware infection or unauthorized software installation.",
            "Denial of Service: Instance resource exhaustion attacks.",
            "Elevation of Privilege: Misconfigured IAM instance profile."
        ],
        'aws_ec2_instance': [
            "Spoofing: Unauthorized SSH/RDP access via compromised credentials.",
            "Tampering: Malware infection or unauthorized software installation.",
            "Denial of Service: Instance resource exhaustion attacks.",
            "Elevation of Privilege: Misconfigured IAM instance profile."
        ],
        'aws_ec2_instances': [
            "Spoofing: Unauthorized SSH/RDP access via compromised credentials.",
            "Tampering: Malware infection or unauthorized software installation.",
            "Denial of Service: Instance resource exhaustion attacks.",
            "Elevation of Privilege: Misconfigured IAM instance profile."
        ],
        'aws_lambda': [
            "Tampering: Malicious code injection via dependencies.",
            "Denial of Service: Concurrency limit exhaustion.",
            "Elevation of Privilege: Over-permissive IAM execution role.",
            "Information Disclosure: Sensitive data in environment variables."
        ],
        'aws_lambda_lambda_function': [
            "Tampering: Malicious code injection via dependencies.",
            "Denial of Service: Concurrency limit exhaustion.",
            "Elevation of Privilege: Over-permissive IAM execution role.",
            "Information Disclosure: Sensitive data in environment variables."
        ],
        'aws_amazon_ec2_auto_scaling': [
            "Denial of Service: Scaling policy manipulation causing over/under-provisioning.",
            "Tampering: Unauthorized modification of launch configurations.",
            "Elevation of Privilege: EC2 instances launched with excessive permissions."
        ],
        'aws_auto_scaling': [
            "Denial of Service: Scaling policy manipulation causing over/under-provisioning.",
            "Tampering: Unauthorized modification of launch configurations."
        ],
        'aws_autoscaling': [
            "Denial of Service: Scaling policy manipulation causing over/under-provisioning.",
            "Tampering: Unauthorized modification of launch configurations."
        ],
        
        # ============== AWS STORAGE ==============
        'aws_amazon_simple_storage_service': [
            "Information Disclosure: Publicly accessible S3 bucket.",
            "Tampering: Unauthorized object modification or deletion.",
            "Repudiation: Disabled access logging prevents audit.",
            "Denial of Service: Excessive request costs (S3 request pricing)."
        ],
        'aws_simple_storage_service_bucket': [
            "Information Disclosure: Publicly accessible S3 bucket.",
            "Tampering: Unauthorized object modification or deletion.",
            "Repudiation: Disabled access logging prevents audit."
        ],
        'aws_simple_storage_service_bucket_with_objects': [
            "Information Disclosure: Publicly accessible S3 bucket.",
            "Tampering: Unauthorized object modification or deletion.",
            "Repudiation: Disabled access logging prevents audit."
        ],
        'aws_simple_storage_service_object': [
            "Information Disclosure: Unencrypted object at rest.",
            "Tampering: Object versioning disabled allows permanent deletion."
        ],
        'aws_simple_storage_service_s3_standard': [
            "Information Disclosure: Publicly accessible S3 bucket.",
            "Tampering: Unauthorized object modification or deletion."
        ],
        'aws_amazon_elastic_block_store': [
            "Information Disclosure: Unencrypted EBS volumes.",
            "Tampering: Snapshot modification or deletion.",
            "Denial of Service: Volume detachment attacks."
        ],
        'aws_elastic_block_store_volume': [
            "Information Disclosure: Unencrypted EBS volumes.",
            "Tampering: Snapshot modification or deletion."
        ],
        'aws_elactic_file_system(nfs)_multi-az': [
            "Information Disclosure: Unencrypted data in transit.",
            "Tampering: Unauthorized file system modification.",
            "Denial of Service: IOPS throttling attacks."
        ],
        
        # ============== AWS DATABASE ==============
        'aws_amazon_rds': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted database connections.",
            "Denial of Service: Connection pool exhaustion.",
            "Repudiation: Disabled audit logging."
        ],
        'aws_rds': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted database connections.",
            "Denial of Service: Connection pool exhaustion."
        ],
        'aws_aurora_amazon_rds_instance': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted database connections.",
            "Denial of Service: Connection pool exhaustion."
        ],
        'aws_amazon_dynamodb': [
            "Tampering: NoSQL injection attacks.",
            "Information Disclosure: Over-permissive IAM policies.",
            "Denial of Service: Capacity unit exhaustion.",
            "Repudiation: Disabled DynamoDB Streams for audit."
        ],
        'aws_dynamodb_table': [
            "Tampering: NoSQL injection attacks.",
            "Information Disclosure: Over-permissive IAM policies.",
            "Denial of Service: Capacity unit exhaustion."
        ],
        'aws_amazon_redshift': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted data warehouse.",
            "Denial of Service: Query resource exhaustion."
        ],
        'aws_amazon_elasticache': [
            "Spoofing: Unauthenticated Redis/Memcached access.",
            "Information Disclosure: In-memory data exposure.",
            "Denial of Service: Cache eviction attacks."
        ],
        'aws_elasticache': [
            "Spoofing: Unauthenticated Redis/Memcached access.",
            "Information Disclosure: In-memory data exposure."
        ],
        
        # ============== AWS NETWORKING ==============
        'aws_amazon_virtual_private_cloud': [
            "Spoofing: VPC peering with untrusted accounts.",
            "Information Disclosure: Overly permissive security groups.",
            "Denial of Service: Network ACL misconfiguration."
        ],
        'aws_virtual_private_cloud': [
            "Spoofing: VPC peering with untrusted accounts.",
            "Information Disclosure: Overly permissive security groups."
        ],
        'aws_vpc_virtual_private_cloud_vpc': [
            "Spoofing: VPC peering with untrusted accounts.",
            "Information Disclosure: Overly permissive security groups."
        ],
        'aws_private_subnet': [
            "Information Disclosure: Unintended internet gateway routing.",
            "Tampering: Route table modification."
        ],
        'aws_public_subnet': [
            "Spoofing: Exposed instances without proper security groups.",
            "Denial of Service: Direct internet-facing attack surface."
        ],
        'aws_amazon_api_gateway': [
            "Spoofing: Unidentified API calls without authentication.",
            "Denial of Service: API rate limit exhaustion.",
            "Information Disclosure: Unencrypted API responses.",
            "Tampering: Injection attacks via API parameters."
        ],
        'aws_application_load_balancer': [
            "Denial of Service: Layer 7 DDoS attacks.",
            "Spoofing: SSL/TLS certificate spoofing.",
            "Information Disclosure: Unencrypted backend connections."
        ],
        'aws_elastic_load_balancing': [
            "Denial of Service: Layer 4/7 DDoS attacks.",
            "Information Disclosure: Health check endpoint exposure."
        ],
        'aws_elastic_load_balancing_application_load_balancer': [
            "Denial of Service: Layer 7 DDoS attacks.",
            "Spoofing: SSL/TLS certificate spoofing."
        ],
        'aws_elastic_load_balancing_network_load_balancer': [
            "Denial of Service: Layer 4 DDoS attacks.",
            "Information Disclosure: Client IP exposure."
        ],
        'aws_amazon_cloudfront': [
            "Denial of Service: Cache poisoning attacks.",
            "Spoofing: Origin access identity misconfiguration.",
            "Information Disclosure: Cached sensitive data."
        ],
        'aws_cloudfront': [
            "Denial of Service: Cache poisoning attacks.",
            "Spoofing: Origin access identity misconfiguration."
        ],
        'aws_amazon_route_53': [
            "Spoofing: DNS hijacking or cache poisoning.",
            "Denial of Service: DNS amplification attacks.",
            "Information Disclosure: Zone transfer exposure."
        ],
        'aws_route_53_hosted_zone': [
            "Spoofing: DNS hijacking or cache poisoning.",
            "Denial of Service: DNS amplification attacks."
        ],
        'aws_waf': [
            "Tampering: WAF rule bypass techniques.",
            "Denial of Service: Rule processing exhaustion."
        ],
        
        # ============== AWS IDENTITY & SECURITY ==============
        'aws_identity_and_access_management': [
            "Spoofing: Credential theft or session hijacking.",
            "Elevation of Privilege: Over-permissive IAM policies.",
            "Repudiation: Disabled CloudTrail logging.",
            "Tampering: Policy modification by compromised admin."
        ],
        'aws_identity_access_management_role': [
            "Elevation of Privilege: Trust policy allows unintended principals.",
            "Spoofing: Role assumption from unexpected sources."
        ],
        'aws_key_management_service': [
            "Information Disclosure: Key policy allows unauthorized access.",
            "Tampering: Key deletion or rotation attacks.",
            "Denial of Service: API throttling under high encryption demand."
        ],
        'aws_cloud_trail': [
            "Repudiation: CloudTrail logging disabled.",
            "Tampering: Log file deletion or modification.",
            "Information Disclosure: Logs stored in public bucket."
        ],
        
        # ============== AWS MONITORING ==============
        'aws_amazon_cloudwatch': [
            "Repudiation: Insufficient log retention.",
            "Information Disclosure: Logs contain sensitive data.",
            "Tampering: Alarm suppression or modification."
        ],
        'aws_cloudwatch': [
            "Repudiation: Insufficient log retention.",
            "Information Disclosure: Logs contain sensitive data."
        ],
        
        # ============== AWS MESSAGING ==============
        'aws_amazon_simple_notification_service': [
            "Spoofing: Unauthorized topic subscription.",
            "Information Disclosure: Messages in transit unencrypted.",
            "Denial of Service: Subscription flooding."
        ],
        'aws_simple_notification_service_topic': [
            "Spoofing: Unauthorized topic subscription.",
            "Information Disclosure: Messages in transit unencrypted."
        ],
        'aws_amazon_simple_queue_service': [
            "Tampering: Message modification in queue.",
            "Information Disclosure: Unencrypted messages.",
            "Denial of Service: Queue flooding attacks."
        ],
        'aws_simple_queue_service_queue': [
            "Tampering: Message modification in queue.",
            "Information Disclosure: Unencrypted messages."
        ],
        'aws_simple_email_service': [
            "Spoofing: Email spoofing without SPF/DKIM.",
            "Information Disclosure: Email content exposure.",
            "Repudiation: Missing email sending logs."
        ],
        
        # ============== AWS CONTAINERS ==============
        'aws_amazon_elastic_container_service': [
            "Tampering: Container image tampering.",
            "Elevation of Privilege: Container escape vulnerabilities.",
            "Information Disclosure: Secrets in environment variables."
        ],
        'aws_elastic_container_service_container_2': [
            "Tampering: Container image tampering.",
            "Elevation of Privilege: Container escape vulnerabilities."
        ],
        'aws_elastic_container_service_service': [
            "Denial of Service: Task definition resource exhaustion.",
            "Elevation of Privilege: Task role over-permissions."
        ],
        'aws_amazon_elastic_kubernetes_service': [
            "Tampering: Kubernetes pod tampering.",
            "Elevation of Privilege: RBAC misconfiguration.",
            "Information Disclosure: Secrets stored in etcd unencrypted.",
            "Denial of Service: Pod resource exhaustion."
        ],
        
        # ============== AWS INFRASTRUCTURE AS CODE ==============
        'aws_cloudformation': [
            "Tampering: Template injection attacks.",
            "Elevation of Privilege: Stack created with admin permissions.",
            "Repudiation: Stack event logging disabled."
        ],
        'aws_cloudformation_template': [
            "Tampering: Template injection attacks.",
            "Elevation of Privilege: Stack created with admin permissions."
        ],
        'aws_backup': [
            "Information Disclosure: Unencrypted backups.",
            "Tampering: Backup deletion or modification.",
            "Denial of Service: Backup vault lock attacks."
        ],
        'aws_cloud': [
            "Spoofing: Cross-account access misconfiguration.",
            "Information Disclosure: Publicly exposed resources."
        ],
        'aws_region': [
            "Denial of Service: Regional service outage exploitation.",
            "Information Disclosure: Cross-region data replication exposure."
        ],
        
        # ============== AZURE COMPUTE ==============
        'azure_virtual_machine': [
            "Spoofing: Unauthorized RDP/SSH access.",
            "Tampering: Malware infection.",
            "Denial of Service: VM resource exhaustion.",
            "Elevation of Privilege: Managed identity over-permissions."
        ],
        'azure_vm_scale_sets': [
            "Denial of Service: Scale set manipulation.",
            "Tampering: Unauthorized instance modification."
        ],
        'azure_function_apps': [
            "Tampering: Function code injection.",
            "Denial of Service: Consumption plan exhaustion.",
            "Elevation of Privilege: Over-permissive function identity."
        ],
        'azure_container_instances': [
            "Tampering: Container image tampering.",
            "Elevation of Privilege: Container escape vulnerabilities.",
            "Information Disclosure: Secrets in environment variables."
        ],
        'azure_kubernetes_services': [
            "Tampering: Kubernetes pod tampering.",
            "Elevation of Privilege: RBAC misconfiguration.",
            "Information Disclosure: Secrets stored unencrypted.",
            "Denial of Service: Pod resource exhaustion."
        ],
        'azure_app_services': [
            "Tampering: Web application vulnerabilities (XSS, CSRF).",
            "Information Disclosure: Debug mode enabled in production.",
            "Denial of Service: App service plan exhaustion."
        ],
        
        # ============== AZURE STORAGE ==============
        'azure_storage_accounts': [
            "Information Disclosure: Publicly accessible blob containers.",
            "Tampering: Unauthorized blob modification.",
            "Repudiation: Disabled storage analytics."
        ],
        
        # ============== AZURE DATABASE ==============
        'azure_sql': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted connections.",
            "Denial of Service: Connection pool exhaustion."
        ],
        'azure_sql_database': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted connections.",
            "Repudiation: Disabled auditing."
        ],
        'azure_sql_server': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Data leakage from unencrypted storage.",
            "Denial of Service: Database connection saturation.",
            "Repudiation: Insufficient audit logs."
        ],
        'azure_sql_managed_instance': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: VNet misconfiguration exposure."
        ],
        'azure_cosmos_db': [
            "Tampering: NoSQL injection attacks.",
            "Information Disclosure: Over-permissive access keys.",
            "Denial of Service: RU exhaustion."
        ],
        'azure_synapse_analytics': [
            "Information Disclosure: Data warehouse exposure.",
            "Tampering: SQL injection in Synapse SQL pools."
        ],
        
        # ============== AZURE NETWORKING ==============
        'azure_virtual_networks': [
            "Spoofing: VNet peering with untrusted networks.",
            "Information Disclosure: Overly permissive NSG rules.",
            "Denial of Service: Network misconfiguration."
        ],
        'azure_network_security_groups': [
            "Information Disclosure: Overly permissive inbound rules.",
            "Denial of Service: Rule processing overhead."
        ],
        'azure_load_balancers': [
            "Denial of Service: Layer 4 DDoS attacks.",
            "Information Disclosure: Health probe exposure."
        ],
        'azure_firewalls': [
            "Tampering: Firewall rule bypass.",
            "Denial of Service: Firewall throughput exhaustion."
        ],
        'azure_api_management_services': [
            "Spoofing: Unauthenticated API access.",
            "Denial of Service: API rate limit exhaustion.",
            "Tampering: API policy manipulation."
        ],
        
        # ============== AZURE IDENTITY ==============
        'microsoft_entra': [
            "Spoofing: Credential theft or phishing.",
            "Elevation of Privilege: Excessive directory role assignments.",
            "Repudiation: Disabled sign-in logs."
        ],
        'azure_key_vaults': [
            "Information Disclosure: Secret exposure via misconfigured access policies.",
            "Tampering: Key or secret deletion.",
            "Denial of Service: API throttling."
        ],
        
        # ============== AZURE MONITORING ==============
        'azure_monitor': [
            "Repudiation: Insufficient log retention.",
            "Information Disclosure: Logs contain sensitive data."
        ],
        'azure_application_insights': [
            "Information Disclosure: Telemetry data exposure.",
            "Repudiation: Disabled application logging."
        ],
        
        # ============== AZURE MESSAGING ==============
        'azure_event_hubs': [
            "Tampering: Event data modification.",
            "Information Disclosure: Unencrypted event data.",
            "Denial of Service: Throughput unit exhaustion."
        ],
        'azure_logic_apps': [
            "Tampering: Workflow manipulation.",
            "Elevation of Privilege: Connector over-permissions.",
            "Information Disclosure: Sensitive data in workflow history."
        ],
        'logic_apps': [
            "Tampering: Workflow manipulation.",
            "Elevation of Privilege: Connector over-permissions."
        ],
        
        # ============== AZURE DATA & AI ==============
        'azure_data_factories': [
            "Tampering: Pipeline manipulation.",
            "Information Disclosure: Connection string exposure.",
            "Elevation of Privilege: Linked service over-permissions."
        ],
        'azure_databricks': [
            "Information Disclosure: Notebook data exposure.",
            "Elevation of Privilege: Cluster IAM over-permissions.",
            "Tampering: Code injection in notebooks."
        ],
        'azure_machine_learning': [
            "Tampering: Model poisoning attacks.",
            "Information Disclosure: Training data exposure.",
            "Elevation of Privilege: Compute instance over-permissions."
        ],
        'azure_machine_learning_studio_workspaces': [
            "Tampering: Model poisoning attacks.",
            "Information Disclosure: Training data exposure."
        ],
        'azure_openai': [
            "Tampering: Prompt injection attacks.",
            "Information Disclosure: PII in prompts or responses.",
            "Denial of Service: Token quota exhaustion."
        ],
        
        # ============== AZURE DEVOPS ==============
        'azure_devops': [
            "Tampering: Pipeline poisoning (supply chain attack).",
            "Elevation of Privilege: Service connection over-permissions.",
            "Information Disclosure: Secrets in pipeline logs."
        ],
        'azure_resource_groups': [
            "Elevation of Privilege: Resource group RBAC misconfiguration.",
            "Tampering: Unauthorized resource modification."
        ],
        'azure_services': [
            "Spoofing: Service principal impersonation.",
            "Information Disclosure: Misconfigured service access."
        ],
        
        # ============== GCP COMPUTE ==============
        'gcp_compute_engine': [
            "Spoofing: Unauthorized SSH access.",
            "Tampering: Instance metadata manipulation.",
            "Denial of Service: VM resource exhaustion.",
            "Elevation of Privilege: Service account over-permissions."
        ],
        'gcp_cloud_functions': [
            "Tampering: Function code injection.",
            "Denial of Service: Invocation quota exhaustion.",
            "Elevation of Privilege: Function service account over-permissions."
        ],
        'gcp_cloud_run': [
            "Tampering: Container image tampering.",
            "Denial of Service: Concurrent request limit.",
            "Elevation of Privilege: Service account over-permissions."
        ],
        'gcp_google_kubernetes_engine': [
            "Tampering: Kubernetes pod tampering.",
            "Elevation of Privilege: RBAC misconfiguration.",
            "Information Disclosure: Secrets in etcd.",
            "Denial of Service: Pod resource exhaustion."
        ],
        
        # ============== GCP STORAGE ==============
        'gcp_cloud_storage': [
            "Information Disclosure: Publicly accessible bucket.",
            "Tampering: Unauthorized file modification.",
            "Denial of Service: Excessive request costs."
        ],
        
        # ============== GCP DATABASE ==============
        'gcp_cloud_sql': [
            "Tampering: SQL Injection attacks.",
            "Information Disclosure: Unencrypted connections.",
            "Denial of Service: Connection limit exhaustion."
        ],
        'gcp_bigquery': [
            "Information Disclosure: Dataset permissions too broad.",
            "Tampering: Unauthorized data modification.",
            "Denial of Service: Query slot exhaustion."
        ],
        
        # ============== GCP NETWORKING ==============
        'gcp_virtual_private_cloud': [
            "Spoofing: VPC peering with untrusted networks.",
            "Information Disclosure: Firewall rule misconfiguration."
        ],
        'gcp_cloud_load_balancing': [
            "Denial of Service: Layer 7 DDoS attacks.",
            "Information Disclosure: Backend exposure."
        ],
        
        # ============== GCP IDENTITY ==============
        'gcp_identity_and_access_management': [
            "Spoofing: Service account key theft.",
            "Elevation of Privilege: Over-permissive IAM bindings.",
            "Repudiation: Disabled audit logging."
        ],
        
        # ============== GCP MESSAGING ==============
        'gcp_pubsub': [
            "Tampering: Message modification.",
            "Information Disclosure: Unencrypted message data.",
            "Denial of Service: Quota exhaustion."
        ],
        
        # ============== GCP AI/ML ==============
        'gcp_vertex_ai': [
            "Tampering: Model poisoning attacks.",
            "Information Disclosure: Training data exposure.",
            "Denial of Service: Quota exhaustion."
        ],
        
        # ============== GENERIC/OTHER ==============
        'api': [
            "Spoofing: Unauthenticated API access.",
            "Tampering: API parameter injection.",
            "Information Disclosure: Verbose error messages.",
            "Denial of Service: Rate limit exhaustion."
        ],
        'user': [
            "Spoofing: Account impersonation or phishing.",
            "Repudiation: User actions without audit trail.",
            "Elevation of Privilege: Role escalation."
        ],
        'developer_portal': [
            "Spoofing: Developer account compromise.",
            "Tampering: API key theft.",
            "Information Disclosure: Exposed API documentation."
        ],
        'sass_services': [
            "Information Disclosure: Data exposure via misconfigured SaaS.",
            "Spoofing: OAuth token theft.",
            "Tampering: Integration manipulation."
        ],
        'solr': [
            "Tampering: Solr query injection.",
            "Information Disclosure: Unprotected admin interface.",
            "Denial of Service: Index corruption."
        ],
        'sei/sip': [
            "Spoofing: Session hijacking.",
            "Tampering: Protocol manipulation.",
            "Information Disclosure: Unencrypted signaling data.",
            "Denial of Service: Flood attacks."
        ],
        'resource_group': [
            "Elevation of Privilege: Overly permissive RBAC.",
            "Tampering: Unauthorized resource modification."
        ],
        
        # Fallback for unknown components
        'default': [
            "Spoofing: Verify authentication mechanisms are properly implemented.",
            "Tampering: Ensure input validation and integrity checks.",
            "Repudiation: Implement comprehensive audit logging.",
            "Information Disclosure: Encrypt data at rest and in transit.",
            "Denial of Service: Implement rate limiting and resource quotas.",
            "Elevation of Privilege: Apply principle of least privilege."
        ]
    }

    @staticmethod
    def get_threats(component: str) -> List[str]:
        """
        Retrieves threats for a specific component.

        Args:
            component (str): The class name of the component (e.g., aws_amazon_api_gateway).

        Returns:
            List[str]: List of potential threats.
        """
        threats = ThreatMapper.THREAT_KB.get(component)
        if not threats:
            # Try to match partial keys or return default
            for key, val in ThreatMapper.THREAT_KB.items():
                if key in component:
                    return val
            return ThreatMapper.THREAT_KB['default']
        return threats


class ThreatModeler:
    """
    Orchestrates the threat modeling process using YOLO inference.
    """

    def __init__(self, model_path: Path):
        """
        Args:
            model_path (Path): Path to the trained .pt model file.
        """
        self.model_path = model_path
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        self.model = YOLO(self.model_path)

    def analyze_image(self, image_path: Path, conf_threshold: float = 0.25, imgsz: int = 640) -> List[Dict[str, Any]]:
        """
        Runs inference on an image and maps results to threats.

        Args:
            image_path (Path): Path to the image file.
            conf_threshold (float): Confidence threshold for detections.
            imgsz (int): Image size for inference (larger = better for small icons).

        Returns:
            List[Dict[str, Any]]: List of detected objects with their threats.
        """
        results = self.model.predict(
            source=str(image_path), 
            conf=conf_threshold, 
            imgsz=imgsz,
            iou=0.45,           # NMS IoU threshold
            agnostic_nms=True   # NMS across all classes
        )
        
        analysis_report = []
        
        for result in results:
            for box in result.boxes:
                # Get class ID and Confidence
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                # Get class name
                class_name = self.model.names[cls_id]
                
                # Map to threats
                threats = ThreatMapper.get_threats(class_name)
                
                analysis_report.append({
                    "component": class_name,
                    "confidence": confidence,
                    "threats": threats,
                    "bbox": box.xywh.tolist() # x, y, w, h
                })
        
        # Filter hallucinations while supporting multi-cloud
        analysis_report = self._filter_hallucinations(analysis_report)
        
        return analysis_report

    def _filter_hallucinations(
        self, 
        detections: List[Dict[str, Any]],
        base_conf_threshold: float = 0.25,
        dominance_threshold: float = 0.60,
        minority_high_conf: float = 0.70
    ) -> List[Dict[str, Any]]:
        """
        Filter likely hallucinations while supporting multi-cloud architectures.
        
        Strategy:
        - Calculate provider dominance based on weighted confidence
        - If a provider is dominant (>60% of total confidence):
          - Keep all dominant provider detections
          - Only keep minority provider if confidence >= 0.70 (high confidence)
        - If no clear dominant provider (balanced multi-cloud):
          - Keep all detections >= base_conf_threshold
        
        Args:
            detections: List of detection dicts
            base_conf_threshold: Min confidence for balanced multi-cloud
            dominance_threshold: Ratio for a provider to be "dominant" (0.60 = 60%)
            minority_high_conf: Min confidence for minority provider detections
        
        Returns:
            Filtered detections list
        """
        if not detections:
            return detections
        
        # Group detections by provider
        by_provider = {'aws': [], 'azure': [], 'gcp': [], 'other': []}
        provider_weights = {'aws': 0.0, 'azure': 0.0, 'gcp': 0.0}
        
        for d in detections:
            comp = d['component'].lower()
            conf = d['confidence']
            if comp.startswith('aws_'):
                by_provider['aws'].append(d)
                provider_weights['aws'] += conf
            elif comp.startswith('azure_'):
                by_provider['azure'].append(d)
                provider_weights['azure'] += conf
            elif comp.startswith('gcp_'):
                by_provider['gcp'].append(d)
                provider_weights['gcp'] += conf
            else:
                by_provider['other'].append(d)
        
        # Calculate dominance
        total_weight = sum(provider_weights.values())
        if total_weight == 0:
            return detections
        
        dominant_provider = max(provider_weights, key=provider_weights.get)
        dominance_ratio = provider_weights[dominant_provider] / total_weight
        
        filtered = []
        
        # Always keep 'other' (non-cloud) items
        filtered.extend(by_provider['other'])
        
        if dominance_ratio >= dominance_threshold:
            # Clear dominant provider - filter minority aggressively
            for provider in ['aws', 'azure', 'gcp']:
                items = by_provider[provider]
                for d in items:
                    if provider == dominant_provider:
                        # Keep all from dominant provider
                        filtered.append(d)
                    elif d['confidence'] >= minority_high_conf:
                        # Only keep high-confidence minority (could be valid hybrid)
                        filtered.append(d)
                    else:
                        logger.info(
                            f"Filtered hallucination: {d['component']} "
                            f"(conf={d['confidence']:.2f}, dominant={dominant_provider})"
                        )
        else:
            # Balanced multi-cloud - use normal threshold
            for provider in ['aws', 'azure', 'gcp']:
                items = by_provider[provider]
                for d in items:
                    if d['confidence'] >= base_conf_threshold:
                        filtered.append(d)
                    else:
                        logger.info(
                            f"Filtered low confidence: {d['component']} "
                            f"(conf={d['confidence']:.2f})"
                        )
        
        return filtered

    def generate_report(self, analysis: List[Dict[str, Any]], output_path: Path) -> None:
        """
        Generates a readable Markdown report.

        Args:
            analysis (List[Dict[str, Any]]): The analysis results.
            output_path (Path): Path where the report will be saved.
        """
        with open(output_path, 'w') as f:
            f.write("# Automated Threat Model Report\n\n")
            f.write("Generated by STRIDE-YOLO System\n\n")
            
            if not analysis:
                f.write("No components detected.\n")
                return

            for item in analysis:
                f.write(f"## Component: **{item['component']}**\n")
                f.write(f"- **Confidence**: {item['confidence']:.2f}\n")
                f.write("- **Potential Threats (STRIDE)**:\n")
                for threat in item['threats']:
                    f.write(f"  - {threat}\n")
                f.write("\n---\n")
        logger.info(f"Report report saved to {output_path}")

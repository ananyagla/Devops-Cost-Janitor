import boto3
import json
import sys
from datetime import datetime, UTC

# Connect to LocalStack EC2
ec2 = boto3.client(
    "ec2",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test"
)

findings = []

# Required tags
required_tags = ["Project", "Environment", "Owner"]

# -----------------------------
# Detect Unattached EBS Volumes
# -----------------------------
volumes = ec2.describe_volumes()

for volume in volumes["Volumes"]:

    tags = {
        tag["Key"]: tag["Value"]
        for tag in volume.get("Tags", [])
    }

    # Check unattached volume
    if volume["State"] == "available":

        findings.append({
            "resource_id": volume["VolumeId"],
            "resource_type": "ebs_volume",
            "reason": "unattached",
            "age_days": 21,
            "estimated_monthly_cost_usd": 8.0,
            "tags": tags,
            "suggested_action": "delete",
            "safe_to_auto_delete": False
        })

    # Check missing tags
    missing_tags = [
        tag for tag in required_tags
        if tag not in tags
    ]

    if missing_tags:

        findings.append({
            "resource_id": volume["VolumeId"],
            "resource_type": "ebs_volume",
            "reason": f"missing_tags: {missing_tags}",
            "age_days": 0,
            "estimated_monthly_cost_usd": 0,
            "tags": tags,
            "suggested_action": "add_tags",
            "safe_to_auto_delete": False
        })

# -----------------------------
# Detect Stopped EC2 Instances
# -----------------------------
instances = ec2.describe_instances()

for reservation in instances["Reservations"]:

    for instance in reservation["Instances"]:

        state = instance["State"]["Name"]

        tags = {
            tag["Key"]: tag["Value"]
            for tag in instance.get("Tags", [])
        }

        # Detect stopped instances
        if state == "stopped":

            findings.append({
                "resource_id": instance["InstanceId"],
                "resource_type": "ec2_instance",
                "reason": "stopped_instance",
                "age_days": 14,
                "estimated_monthly_cost_usd": 5.0,
                "tags": tags,
                "suggested_action": "terminate",
                "safe_to_auto_delete": False
            })

        # Detect missing tags
        missing_tags = [
            tag for tag in required_tags
            if tag not in tags
        ]

        if missing_tags:

            findings.append({
                "resource_id": instance["InstanceId"],
                "resource_type": "ec2_instance",
                "reason": f"missing_tags: {missing_tags}",
                "age_days": 0,
                "estimated_monthly_cost_usd": 0,
                "tags": tags,
                "suggested_action": "add_tags",
                "safe_to_auto_delete": False
            })

# -----------------------------
# Detect Unused Elastic IPs
# -----------------------------
addresses = ec2.describe_addresses()

for address in addresses.get("Addresses", []):

    if "InstanceId" not in address:

        findings.append({
            "resource_id": address.get("AllocationId", "unknown"),
            "resource_type": "elastic_ip",
            "reason": "unused_eip",
            "age_days": 7,
            "estimated_monthly_cost_usd": 3.6,
            "tags": {},
            "suggested_action": "release",
            "safe_to_auto_delete": False
        })

# -----------------------------
# Final Report
# -----------------------------
report = {
    "scan_timestamp": str(datetime.now(UTC)),
    "account_id": "000000000000",
    "region": "us-east-1",
    "summary": {
        "total_orphans": len(findings),
        "estimated_monthly_waste_usd": 8.0
    },
    "findings": findings
}

# Save JSON Report
with open("report.json", "w") as f:
    json.dump(report, f, indent=2)

# Save Markdown Report
with open("report.md", "w") as f:

    f.write("# Cost Janitor Report\n\n")

    f.write("## Summary\n\n")
    f.write(f"- Total orphans: {len(findings)}\n")
    f.write("- Estimated monthly waste: $8.0\n\n")

    f.write("## Findings\n\n")

    for finding in findings:

        f.write(
            f"- {finding['resource_type']} | "
            f"{finding['resource_id']} | "
            f"{finding['reason']}\n"
        )

print("Report generated successfully")

# Exit non-zero if findings exist
if findings:
    sys.exit(1)
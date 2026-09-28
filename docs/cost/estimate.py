#!/usr/bin/env python3
"""Monthly cost model for the virtualization-lab EC2 deployment.

Reads unit prices from aws-prices-us-east-1.csv (extracted from the AWS Price
List API) and computes the monthly cost of each workload scenario, line by
line, exactly as it is entered in the AWS Pricing Calculator.

Usage:
    python3 docs/cost/estimate.py            # prints Markdown tables
    python3 docs/cost/estimate.py --csv      # also rewrites cost-estimate.csv
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).parent
HOURS_PER_MONTH = 730  # the convention used by the AWS Pricing Calculator

# Traffic profile. Measured with curl against the running container: a request
# is 96-387 bytes and a response is 127-174 bytes (headers + "Hello, <name>!").
# The model rounds up generously to leave room for TCP/TLS overhead and for the
# API to grow beyond a one-line greeting.
REQUEST_KB = 1
RESPONSE_KB = 2

SCENARIOS = [
    {
        "name": "Small workload",
        "requests": 10_000,
        "instance": "t3.micro",
        "instances": 1,
        "hours": HOURS_PER_MONTH,
        "ebs_gb": 8,
        "public_ipv4": 1,
        "alb": False,
        "schedule": "Continuous (24/7)",
        "high_availability": "No",
    },
    {
        "name": "Medium workload",
        "requests": 100_000,
        "instance": "t3.small",
        "instances": 1,
        "hours": HOURS_PER_MONTH,
        "ebs_gb": 20,
        "public_ipv4": 1,
        "alb": False,
        "schedule": "Continuous (24/7)",
        "high_availability": "No",
    },
    {
        "name": "Large workload",
        "requests": 1_000_000,
        "instance": "t3.small",
        "instances": 2,
        "hours": HOURS_PER_MONTH,
        "ebs_gb": 20,
        # One address per instance (to pull images without a NAT gateway) and
        # one per ALB node (the ALB spans two Availability Zones).
        "public_ipv4": 4,
        "alb": True,
        "alb_lcu": 0.1,
        "schedule": "Continuous (24/7)",
        "high_availability": "Yes: 2 AZs behind an ALB",
    },
]

SENSITIVITY = [
    dict(SCENARIOS[0], name="Small, office hours only (12 h x 22 days)",
         hours=12 * 22, schedule="Scheduled: 264 h/month"),
    dict(SCENARIOS[2], name="Large, single instance (no HA)",
         instances=1, public_ipv4=1, alb=False, high_availability="No"),
]

# Serverless alternative for the small workload: API Gateway HTTP API + Lambda.
LAMBDA_MEMORY_GB = 1.0
LAMBDA_AVG_BILLED_SECONDS_SPARSE = 1.5  # ~half of the requests pay a ~3 s cold start
LAMBDA_AVG_BILLED_SECONDS_WARM = 0.1
ECR_IMAGE_GB = 0.3


def load_prices():
    with open(HERE / "aws-prices-us-east-1.csv", newline="") as f:
        return {row["key"]: float(row["price_usd"]) for row in csv.DictReader(f)}


def outbound_gb(requests):
    return requests * RESPONSE_KB / 1024 / 1024


def line_items(s, p):
    instance_price = p[f"ec2_{s['instance'].replace('.', '_')}_hour"]
    items = [
        ("EC2 compute",
         f"{s['instances']} x {s['instance']} x {s['hours']} h x ${instance_price}/h",
         s["instances"] * s["hours"] * instance_price),
        ("EBS storage",
         f"{s['instances']} x {s['ebs_gb']} GB gp3 x ${p['ebs_gp3_gb_month']}/GB-month",
         s["instances"] * s["ebs_gb"] * p["ebs_gp3_gb_month"]),
        ("Data transfer out",
         f"{outbound_gb(s['requests']):.3f} GB x ${p['data_out_internet_gb']}/GB",
         outbound_gb(s["requests"]) * p["data_out_internet_gb"]),
        # An auto-assigned public IPv4 address is released while the instance
        # is stopped, so it is billed for the same hours as the instance.
        ("Public IPv4",
         f"{s['public_ipv4']} address(es) x {s['hours']} h x ${p['public_ipv4_hour']}/h",
         s["public_ipv4"] * s["hours"] * p["public_ipv4_hour"]),
    ]
    if s["alb"]:
        items.append((
            "Application Load Balancer",
            f"{HOURS_PER_MONTH} h x ${p['alb_hour']}/h + {s['alb_lcu']} LCU x {HOURS_PER_MONTH} h x ${p['alb_lcu_hour']}",
            HOURS_PER_MONTH * (p["alb_hour"] + s["alb_lcu"] * p["alb_lcu_hour"])))
    return items


def serverless_small(p, requests, billed_seconds):
    return (requests * p["apigw_http_request"]
            + requests * p["lambda_request"]
            + requests * billed_seconds * LAMBDA_MEMORY_GB * p["lambda_gb_second"]
            + ECR_IMAGE_GB * p["ecr_storage_gb_month"]
            + outbound_gb(requests) * p["data_out_internet_gb"])


def main():
    p = load_prices()
    rows = []

    print("## Scenario results\n")
    print("| Scenario | Monthly requests | Monthly infrastructure cost | Estimated cost per request | Cost per 1,000 requests |")
    print("|---|---:|---:|---:|---:|")
    for s in SCENARIOS + SENSITIVITY:
        items = line_items(s, p)
        total = sum(cost for _, _, cost in items)
        s["total"] = total
        print(f"| {s['name']} | {s['requests']:,} | USD {total:,.2f} | USD {total / s['requests']:.7f} "
              f"| USD {1000 * total / s['requests']:.3f} |")
        for item, formula, cost in items:
            rows.append([s["name"], s["requests"], item, formula, f"{cost:.4f}", f"{100 * cost / total:.1f}"])
        rows.append([s["name"], s["requests"], "TOTAL", "", f"{total:.4f}", "100.0"])

    print("\n## Line items\n")
    print("| Scenario | Item | Calculation | USD / month | Share |")
    print("|---|---|---|---:|---:|")
    for name, _, item, formula, cost, share in rows:
        print(f"| {name} | {item} | {formula} | {float(cost):,.2f} | {share}% |")

    small = SCENARIOS[0]
    sparse = serverless_small(p, small["requests"], LAMBDA_AVG_BILLED_SECONDS_SPARSE)
    per_request_warm = (p["apigw_http_request"] + p["lambda_request"]
                        + LAMBDA_AVG_BILLED_SECONDS_WARM * LAMBDA_MEMORY_GB * p["lambda_gb_second"]
                        + RESPONSE_KB / 1024 / 1024 * p["data_out_internet_gb"])
    break_even = (small["total"] - ECR_IMAGE_GB * p["ecr_storage_gb_month"]) / per_request_warm
    print("\n## Serverless comparison (small workload)\n")
    print(f"- API Gateway HTTP API + Lambda ({LAMBDA_MEMORY_GB:g} GB, {LAMBDA_AVG_BILLED_SECONDS_SPARSE} s avg billed): "
          f"USD {sparse:.2f}/month vs USD {small['total']:.2f} on EC2 (free tier not applied)")
    print(f"- Warm serverless cost per 1,000 requests: USD {1000 * per_request_warm:.4f}")
    print(f"- Break-even with the small EC2 deployment: {break_even:,.0f} requests/month")
    for s in SCENARIOS[1:]:
        warm = s["requests"] * per_request_warm + ECR_IMAGE_GB * p["ecr_storage_gb_month"]
        print(f"- {s['name']} ({s['requests']:,} requests) on serverless, warm: USD {warm:.2f}/month "
              f"vs USD {s['total']:.2f} on EC2")

    fixed_single = SENSITIVITY[1]["total"] - outbound_gb(1_000_000) * p["data_out_internet_gb"]
    variable = RESPONSE_KB / 1024 / 1024 * p["data_out_internet_gb"]
    print("\n## Fixed vs variable cost\n")
    print(f"- Variable (data transfer) cost per request: USD {variable:.9f}")
    print(f"- Fixed cost of one t3.small: USD {fixed_single:.2f}/month; "
          f"variable cost equals it at {fixed_single / variable:,.0f} requests/month")

    if "--csv" in sys.argv:
        with open(HERE / "cost-estimate.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["scenario", "monthly_requests", "item", "calculation", "usd_per_month", "share_percent"])
            writer.writerows(rows)


if __name__ == "__main__":
    main()

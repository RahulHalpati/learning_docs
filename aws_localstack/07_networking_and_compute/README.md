# 07 · Networking & compute

IAM controls **who can call the API**. The VPC controls **what can reach what on the
network**. They're the two halves of AWS access control, and a real system needs both —
an `AccessDenied` and a connection timeout are different failures with different fixes.

This is also the half that shows up in almost every AWS job description ("VPC, subnets,
security groups") and in almost every system-design interview, because it's where
least-privilege stops being a JSON document and becomes a topology.

| # | Module | Services | You'll be able to… |
|---|---|---|---|
| 07-1 | [VPC, subnets & security groups](01_vpc_subnets_security_groups.md) | EC2 (VPC APIs) | Design a public/private subnet layout and write tiered security-group rules |
| 07-2 | [EC2 & putting a service in a VPC](02_ec2_and_service_in_a_vpc.md) | EC2, Lambda, IAM | Launch an instance into a subnet + SG, and attach networking to other services |

**Honest note:** Floci **creates** VPCs, subnets, security groups and
EC2 instances with the same CLI/Terraform as real AWS — but it does **not** emulate
real networking: security-group rules are stored and never enforced, subnets aren't
isolated, and instances are Docker containers, not VMs. So you can verify your
**topology**; enforcement must be verified on real AWS. Same create-vs-enforce gap as
IAM — details in each lesson.

**Next → [07-1 · VPC, subnets & security groups](01_vpc_subnets_security_groups.md)**

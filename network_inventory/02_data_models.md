# 02: Network Inventory Data Models - Resource & Service

> **Level:** Beginner/Intermediate  
> **Prerequisites:** Module 01  
> **Time:** 45 minutes  
> **What You'll Learn:** How to structure inventory data using Resource and Service models, and why graph databases are the perfect fit.

## Introduction
**What:** Creating a blueprint (schema) for how inventory data is stored and connected.  
**Why:** Telecom networks are highly interconnected. Traditional rows and columns (Relational DBs) struggle with "A connects to B which connects to C."  
**Example:** Modeling a network is like modeling a family tree or a social network. Graph models work best.

## Core Concepts

### Concept 1: The Resource Model
- **What:** Represents the actual network infrastructure (the "How").
- **Why:** Network engineers need to manage the physical boxes and logical network constructs.
- **Components:**
  - `Equipment` (Cards, Chassis)
  - `LogicalResource` (IP addresses, VLANs)
  - `TopologicalLink` (Cables connecting locations)

### Concept 2: The Service Model
- **What:** Represents what the customer buys (the "What").
- **Why:** Customer support doesn't care about the specific router chassis; they care if the "Premium Internet Service" is active.
- **Components:**
  - `CustomerFacingService (CFS)`: E.g., "500Mbps Home Fiber".
  - `ResourceFacingService (RFS)`: How the service translates to the network.

### Concept 3: The CFS-RFS-Resource Link
- **What:** Tying it all together. A CFS depends on an RFS, which depends on Resources.
- **Why:** This chain allows "Impact Analysis." If a Resource (cable) breaks, you trace the links up to find which Customer Services (CFS) are down.

## Practical Example

**Building:** A simplified Python model of the CFS-RFS-Resource chain.  
**Why:** Demonstrates how data is structured hierarchically.

```python
# STANDARD LIBRARY
from typing import List

class Resource:
    """What: Physical/Logical network element | Why: Bottom layer of the network"""
    def __init__(self, name: str, is_active: bool) -> None:
        self.name = name          # e.g., 'Router-Port-5'
        self.is_active = is_active

class ResourceFacingService:
    """What: Network-level service | Why: Bridges customer service to actual resources"""
    def __init__(self, name: str) -> None:
        self.name = name
        # A service depends on one or more resources
        self.dependent_resources: List[Resource] = []

class CustomerFacingService:
    """What: The product the customer bought | Why: Top layer, what we bill for"""
    def __init__(self, customer_id: str, service_type: str) -> None:
        self.customer_id = customer_id
        # A customer service depends on network services
        self.underlying_rfs: List[ResourceFacingService] = []

    def check_health(self) -> bool:
        """
        Check if the customer service is working.
        
        What: Traverses down to the resources to check status.
        Why: Allows automated troubleshooting.
        Returns: bool - True if all underlying resources are active.
        """
        for rfs in self.underlying_rfs:
            for resource in rfs.dependent_resources:
                if not resource.is_active:
                    return False # If any resource is down, the service is down
        return True
```

## Best Practices

**✅ DO:**
- **Use Graph Databases (Neo4j, Amazon Neptune)** - Why: Networks are graphs. Queries like "Find all services relying on Router X" take milliseconds in a Graph DB, but minutes in a Relational DB.
- **Separate Service from Resource** - Why: You can swap out a physical router (Resource) without changing the customer's Service definition.

**❌ DON'T:**
- **Hardcode Customer Data into Network Devices** - Why bad: Mixing billing data with network router data causes huge security and maintenance issues. | Fix: Keep them in separate models linked by IDs.

## Practice Exercises

**Exercise 1:** Impact Analysis Trace
- Requirements: Imagine a fiber cable (`Resource`) gets cut. It is linked to an `Optical Link` (`RFS`), which provides `Enterprise Internet` (`CFS`) to "Corp Inc." What is the status of Corp Inc.'s internet?
- Hint: Follow the chain from bottom to top.

<details>
<summary>Solution</summary>

Corp Inc.'s `Enterprise Internet` is DOWN. 
**Why it works:** The failure propagates upward. Resource (Cut) -> RFS (Fails) -> CFS (Fails). This is exactly how automated alerting systems work in telecoms!
</details>

## What's Next
**Learned:** ✅ Resource vs Service models, ✅ CFS and RFS concepts, ✅ Impact analysis logic.  
**Next:** Module 03: TMF Standards - will cover how the industry agrees on naming and structuring these models!  
**Check:** Can you explain the difference between a CFS and an RFS?

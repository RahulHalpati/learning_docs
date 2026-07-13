# 03: TMF Standards (TMF 633, 634, 638, 639)

> **Level:** Intermediate  
> **Prerequisites:** Module 02  
> **Time:** 45 minutes  
> **What You'll Learn:** What TM Forum Open APIs are and how they standardize inventory management.

## Introduction
**What:** TMF (TeleManagement Forum) Open APIs are standard blueprints for telecom software.  
**Why:** If AT&T buys a new inventory system from Oracle, and a billing system from Amdocs, they need them to speak the same language. TMF provides that language.  
**Example:** TMF is like the USB standard. Because everyone agrees on the shape of a USB plug, any mouse works with any computer.

## Core Concepts

### TMF 639: Resource Inventory Management API
- **What:** The standard API for managing physical and logical resources.
- **Why:** Used to create, read, update, and delete network devices in the database.
- **Key entities:** `Resource`, `LogicalResource`, `PhysicalResource`.

### TMF 638: Service Inventory Management API
- **What:** The standard API for managing customer and resource-facing services.
- **Why:** Used by the CRM or Order Management system to see what services a customer has.
- **Key entities:** `Service`.

### TMF 633: Service Catalog API
- **What:** Defines the "menu" of services you can sell.
- **Why:** Before you can create a Service Inventory record (TMF 638), the service must exist in the catalog. It's the blueprint.
- **Key entities:** `ServiceSpecification`.

### TMF 634: Resource Catalog API
- **What:** Defines the "catalog" of hardware and logical templates you can use.
- **Why:** Defines that a "Cisco Router Model X" has exactly 4 ports. TMF 639 then creates specific instances of that router.
- **Key entities:** `ResourceSpecification`.

## Practical Example

**Building:** Simulating a TMF 639 Resource creation payload.  
**Why:** Shows exactly what the standardized data looks like in the real world.

```python
# THIRD-PARTY (simulated API framework)
import json # What: JSON parser | Why: APIs communicate using JSON

def create_tmf639_resource() -> str:
    """
    Generate a standard TMF639 JSON payload.
    
    What: Creates a standardized representation of a router.
    Why: This exact format can be understood by any TMF-compliant system.
    Returns: str - JSON formatted string
    """
    
    # TMF standards dictate specific field names like '@type', 'name', 'resourceStatus'
    tmf_payload = {
        "name": "NYC-CORE-RTR-01",
        "@type": "LogicalResource",      # TMF standard classification
        "resourceStatus": "operating",   # TMF standard lifecycle state
        "category": "Router",
        "resourceCharacteristic": [      # Custom attributes go here
            {
                "name": "IP_Address",
                "value": "192.168.1.1"
            }
        ]
    }
    
    return json.dumps(tmf_payload, indent=2)

# Expected Output: A clean JSON object following TMF 639 rules
print(create_tmf639_resource())
```

## Best Practices

**✅ DO:**
- **Extend, Don't Break** - Why: TMF allows you to add custom fields inside `resourceCharacteristic`. Use this instead of changing the core fields, so you remain compliant.
- **Use API Gateways** - Why: Expose these APIs through a gateway to handle security and rate limiting.

**❌ DON'T:**
- **Reinvent the Wheel** - Why bad: Don't create your own custom JSON structure for a Router. | Fix: Use TMF 639. It covers 99% of use cases and saves months of design time.

## Common Mistakes

**Mistake:** Confusing Catalog (633/634) with Inventory (638/639).
**Why:** It's easy to mix up the template (Catalog) with the actual deployed item (Inventory).
**Fix:** 
- Catalog = "We sell a 1Gbps service" or "A Cisco router has 4 ports".
- Inventory = "John Doe currently has the 1Gbps service" or "Router #123 is installed in Rack 4".

## Practice Exercises

**Exercise 1:** API Routing
- Requirements: Which TMF API (633, 634, 638, 639) would you call to: 
  1. Find out if the link between LA and NY is broken?
  2. See if a customer has paid for "Premium Tech Support" service?
  3. Add a new type of Nokia 5G Antenna to the list of approved equipment?

<details>
<summary>Solution</summary>

1. Link broken: **TMF 639 (Resource Inventory)**
2. Customer service: **TMF 638 (Service Inventory)**
3. New approved equipment type: **TMF 634 (Resource Catalog)**

**Why it works:** Physical/Logical state is 639. Customer instantiated services are 638. Blueprints/templates for equipment are 634.
</details>

## What's Next
**Learned:** ✅ TMF Open APIs, ✅ Catalogs (633/634) vs Inventory (638/639).  
**Next:** Module 04: Practical Project - Let's build a mini inventory system!  
**Check:** Can you name the API standard used for Resource Inventory?

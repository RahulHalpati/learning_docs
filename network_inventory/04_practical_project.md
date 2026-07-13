# 04: Practical Project - Network Inventory Graph Builder

> **Difficulty:** Intermediate  
> **Time:** 2 hours  
> **Prerequisites:** Modules 00-03

## Overview
**Building:** A Python script that builds a small in-memory Graph Database simulating a telecom network.  
**Why:** Combines Resource modeling, Service modeling, and Impact Analysis in a practical, executable way.  
**Outcome:** A working script that can trace a cut cable all the way up to the impacted customer services.

## Requirements
| Feature | Module Ref |
|---------|------------|
| Physical/Logical Resources | Module 01 & 02 |
| Service to Resource Mapping | Module 02 |
| Data Structure (Graph logic) | Module 02 & 03 |

## Project Structure
```text
network_inventory_project/
└── inventory_graph.py
```

## Build Steps

**Phase 1: Setup Models**
We will create Python classes that act as nodes in our graph.

```python
# inventory_graph.py

# STANDARD LIBRARY
from typing import List

class GraphNode:
    """What: Base class for our graph | Why: Allows linking any entity to any entity"""
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name
        self.status = "operating" # TMF style status
        self.depends_on: List['GraphNode'] = [] # Links pointing downward

    def add_dependency(self, node: 'GraphNode') -> None:
        """What: Creates a directed edge | Why: Builds the graph hierarchy"""
        self.depends_on.append(node)
        
    def is_healthy(self) -> bool:
        """
        Recursively check health.
        
        What: Traverses down the graph.
        Why: Impact analysis.
        Returns: bool - False if this node or ANY dependency is 'faulty'
        """
        if self.status == "faulty":
            return False
            
        # Check all dependencies
        for dep in self.depends_on:
            if not dep.is_healthy():
                return False
                
        return True

# Specialized Nodes (TMF Concepts)
class Resource(GraphNode):
    pass

class ResourceFacingService(GraphNode):
    pass

class CustomerFacingService(GraphNode):
    pass
```

**Phase 2: Testing & Execution**
Let's build a mini network and simulate a failure.

```python
# --- Build the Network Graph ---

# 1. Create Resources (TMF 639 style)
fiber_cable = Resource("RES-001", "NYC-LA-Fiber")
router = Resource("RES-002", "LA-Core-Router")

# 2. Create Services (TMF 638 style)
vpn_rfs = ResourceFacingService("RFS-001", "Backbone VPN")
customer_internet = CustomerFacingService("CFS-001", "Acme Corp Internet")

# 3. Link them up (Build the Graph)
# Customer Internet depends on VPN
customer_internet.add_dependency(vpn_rfs)

# VPN depends on the Router AND the Fiber Cable
vpn_rfs.add_dependency(router)
vpn_rfs.add_dependency(fiber_cable)

# --- Simulate and Test ---
print("--- Initial State ---")
print(f"Customer Service Health: {customer_internet.is_healthy()}") # Expected: True

print("\\n--- Disaster Strikes: Fiber cut by backhoe ---")
fiber_cable.status = "faulty"

print(f"Customer Service Health: {customer_internet.is_healthy()}") # Expected: False
```

## Complete Code
The above code snippets combine into a single, fully functional `inventory_graph.py` file. You can run it directly in Python!

## Extend It
- **Add Customers** - Difficulty: Easy - Learn: Add a `Customer` class that links to multiple `CustomerFacingService` objects.
- **Implement Neo4j/Cypher** - Difficulty: Hard - Learn: Replace the Python in-memory graph with a real Graph Database and write Cypher queries for impact analysis.

## Congratulations! 🎉
**Completed:** 
- Modeled Resources and Services
- Understood TMF standard structures
- Built a functional Impact Analysis engine using Graph concepts!

**Next:** Deep dive into Graph Databases (Neo4j, Amazon Neptune) and Graph Query Languages (Cypher) to scale this to millions of nodes!

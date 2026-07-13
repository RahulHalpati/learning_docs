# 04: Migration to Graph Databases & Graph Modeling

> **Level:** Advanced  
> **Prerequisites:** Module 01  
> **Time:** 60 minutes  
> **What You'll Learn:** Why telecom moves from SQL to Graph (Neo4j, Neptune), and how to model data as Nodes and Edges.

## Introduction
**What:** Shifting the database architecture from Tables (Relational) to Nodes and Edges (Graph).  
**Why:** Relational databases are terrible at querying deeply connected data. Asking SQL "Find all customers affected by a broken router 5 layers deep" requires massive, slow `JOIN` operations. Graph databases solve this in milliseconds.  
**Example:** Moving from a spreadsheet mentality to a mind-map mentality.

## Core Concepts

### Concept 1: The Graph Database Ecosystem
- **Neo4j:** The market leader. Uses Cypher query language. Excellent visualization tools.
- **Amazon Neptune:** AWS's managed graph database. Supports both Gremlin and SPARQL.
- **Others:** JanusGraph (scalable, open-source), NebulaGraph (high performance distributed).

### Concept 2: Graph Modeling Basics
- **Nodes (Vertices):** The entities (nouns). E.g., Router, Port, Customer.
- **Edges (Relationships):** The connections (verbs). E.g., `CONNECTS_TO`, `DEPENDS_ON`, `OWNS`.
- **Properties:** Key-value pairs stored on BOTH Nodes and Edges. E.g., Node Property: `IP=10.0.0.1`, Edge Property: `bandwidth=1Gbps`.

### Concept 3: The Migration Strategy
- **Why:** You don't just dump SQL into a Graph. You have to reshape it.
- **Table to Node:** A `Routers` table becomes `(:Router)` nodes.
- **Foreign Key to Edge:** A `router_id` in the `Ports` table becomes a `[:HAS_PORT]` relationship between the Router node and the Port node.

## Practical Example

**Building:** Modeling a network connection in SQL vs Graph.  
**Why:** Visually demonstrates the paradigm shift.

**The Scenario:** A Customer owns a Service. The Service runs on a Port. The Port belongs to a Router.

**1. Relational Model (Mental Model)**
```text
Table: Customers (id)
Table: Services (id, customer_id)
Table: Service_Port_Mapping (service_id, port_id)
Table: Ports (id, router_id)
Table: Routers (id)
```
*To find the router for a customer, you need 4 JOINs!*

**2. Graph Model (Mental Model)**
```text
(Customer)-[:OWNS]->(Service)-[:RUNS_ON]->(Port)-[:BELONGS_TO]->(Router)
```
*To find the router, you just follow the path.*

**Python Migration Script Snippet:**
```python
# Pseudo-code for migrating Data from SQL to Graph

def migrate_router_to_neo4j(sql_data: dict, neo4j_session) -> None:
    """
    Takes a row from SQL and creates a Node in Neo4j.
    
    What: Data translation.
    Why: Step 1 of migration.
    """
    
    # In Cypher: CREATE (r:Router {id: $id, hostname: $hostname})
    cypher_query = """
    MERGE (r:Router {id: $id})
    SET r.hostname = $hostname, r.status = $status
    """
    
    neo4j_session.run(cypher_query, 
                      id=sql_data['id'], 
                      hostname=sql_data['hostname'], 
                      status=sql_data['status'])
```

## Best Practices

**✅ DO:**
- **Use Specific Relationship Names** - Why: `[:CONNECTED_TO_FIBER]` is much better than a generic `[:LINK]`. It makes queries faster and easier to read.
- **Store Weights on Edges** - Why: If a link is 100km long, store `distance=100` on the relationship itself, useful for shortest-path algorithms.

**❌ DON'T:**
- **Create Supernodes** - Why bad: If one node (like an "Internet" node) has 10 million relationships, it will slow down traversal. | Fix: Break it up or rethink the model.

## Common Mistakes

**Mistake:** Making properties into nodes when they shouldn't be.
**Why:** Creating a node for "Active Status" and linking every active router to it creates a massive supernode.
**Fix:** Keep simple attributes (status, IP address, creation date) as properties on the node itself.

## Practice Exercises

**Exercise 1:** SQL to Graph Translation
- Requirements: You have a SQL table `Employees` with a column `manager_id`. How would you model this in a Graph Database? Define the Nodes and the Relationship.
- Hint: The nodes are of the same type.

<details>
<summary>Solution</summary>

- **Nodes:** `(:Employee)`
- **Relationship:** `(Employee)-[:REPORTS_TO]->(Employee)`

**Why it works:** In a graph, relationships can point back to nodes of the same label. This creates a beautiful, traversable corporate hierarchy tree, whereas SQL would require a complex Recursive CTE query.
</details>

## What's Next
**Learned:** ✅ Graph Database Ecosystem, ✅ Node/Edge/Property modeling, ✅ Migration concepts.  
**Next:** Module 05: Graph Queries - How to actually write the code to traverse this new graph!  
**Check:** What is the Graph equivalent of a SQL Foreign Key?

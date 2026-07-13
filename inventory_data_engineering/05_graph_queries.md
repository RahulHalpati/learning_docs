# 05: Graph Queries and Optimization (Cypher & GraphQL)

> **Level:** Intermediate/Advanced  
> **Prerequisites:** Module 04  
> **Time:** 60 minutes  
> **What You'll Learn:** How to write code to traverse a graph using Cypher and GraphQL, and how to make those queries lightning fast.

## Introduction
**What:** Writing queries to ask the graph database questions.  
**Why:** You've modeled the data as a graph; now you need to extract value from it.  
**Example:** Asking "Which 5 customers will lose internet if Router X goes offline?"

## Core Concepts

### Concept 1: Cypher Query Language
- **What:** The standard query language for Neo4j (and supported by Amazon Neptune).
- **Why:** It uses ASCII-art to draw the pattern you want to find.
- **Syntax:** `(node)-[relationship]->(node)`

### Concept 2: GraphQL for Graph Databases
- **What:** An API query language. Neo4j has a library (`@neo4j/graphql`) that automatically turns GraphQL queries into Cypher queries.
- **Why:** Front-end developers love GraphQL. It allows them to ask for exactly the data they need without writing Cypher.

### Concept 3: Query Optimization
- **What:** Making queries run in milliseconds instead of seconds.
- **Why:** A bad graph query can accidentally scan the entire database, locking up the server.

## Practical Example

**Building:** Impact analysis queries using Cypher.  
**Why:** It is the most common use case in telecom graph databases.

**Scenario:** We want to find all Customer Services impacted by a specific broken Router.

```cypher
// --- 1. Basic Cypher Query (Find the Router) ---
// What: Finds a router by its hostname
MATCH (r:Router {hostname: 'NYC-RTR-01'})
RETURN r;

// --- 2. Traversal Query (Impact Analysis) ---
// What: Finds all paths from the Router up to the Customer Service
// Syntax breakdown:
// (r) = The Router
// <-[:RUNS_ON*1..3]- = Traverse backward up to 3 hops through RUNS_ON relationships
// (c) = The target CustomerService node
MATCH (r:Router {hostname: 'NYC-RTR-01'})<-[:RUNS_ON*1..3]-(c:CustomerService)
RETURN c.service_id, c.customer_name;
```

**GraphQL Equivalent (Using Neo4j GraphQL Library):**
```graphql
# Front-end request
query {
  routers(where: { hostname: "NYC-RTR-01" }) {
    hostname
    status
    servicesRunningHere {
      service_id
      customer_name
    }
  }
}
```

## Best Practices

**✅ DO:**
- **Use Labels and Indexes** - Why: `MATCH (r:Router {name: 'A'})` is 1000x faster than `MATCH (n {name: 'A'})`. Always specify the label (`:Router`) and put an index on the `name` property.
- **Limit Variable Length Paths** - Why: Using `*` (infinite hops) can cause a memory explosion. Always put an upper limit like `*1..5`.

**❌ DON'T:**
- **Return Entire Nodes When Not Needed** - Why bad: `RETURN r` sends all properties of the node over the network. | Fix: Return only what you need: `RETURN r.hostname, r.status`.

## Common Mistakes

**Mistake:** Creating a Cartesian Product.
**Why:** If you use two `MATCH` statements without connecting them, Cypher will multiply every result of the first match by every result of the second match. (e.g., 100 routers * 100 customers = 10,000 results).
**Fix:** Always ensure your `MATCH` statements share a variable or are explicitly linked.

## Practice Exercises

**Exercise 1:** Write a Cypher Query
- Requirements: Write a query to find all `Port` nodes that are `[:CONNECTED_TO]` a `Router` with the hostname 'LA-CORE-01'. Return the `port_number`.
- Hint: Draw the pattern: `(router)-[rel]->(port)`.

<details>
<summary>Solution</summary>

```cypher
MATCH (r:Router {hostname: 'LA-CORE-01'})-[:CONNECTED_TO]->(p:Port)
RETURN p.port_number;
```
**Why it works:** It matches the starting node by an indexed property, traverses the specific relationship type, and returns only the necessary property from the connected node.
</details>

## What's Next
**Learned:** ✅ Cypher syntax, ✅ GraphQL integration, ✅ Query optimization techniques.  
**Next:** Module 06: ML Pipelines & Graph Analytics - Using advanced math on the graph to predict the future!  
**Check:** What does the `*1..3` syntax mean in a Cypher relationship?

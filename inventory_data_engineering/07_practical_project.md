# 07: Practical Project - Inventory Data Pipeline

> **Difficulty:** Advanced  
> **Time:** 3 hours  
> **Prerequisites:** Modules 00-06

## Overview
**Building:** An automated Python pipeline that Extracts mock SQL data, Transforms it, Loads it into a Neo4j Graph Database, and Exposes it via a FastAPI endpoint.  
**Why:** This proves you can move data from legacy systems into modern, intelligent graph architectures and serve it to front-end applications.  
**Outcome:** A complete, runnable end-to-end data engineering architecture.

## Requirements
| Feature | Module Ref |
|---------|------------|
| Data Extraction (ETL) | Module 03 |
| Graph Migration (Neo4j) | Module 04 & 05 |
| API Serving (FastAPI) | Module 02 |

## Project Structure
```text
inventory_pipeline/
├── data/
│   └── mock_sql_dump.csv
├── etl.py
└── api.py
```

## Build Steps

**Phase 1: The Mock Data (mock_sql_dump.csv)**
Create a file simulating data from an old SQL system.
```csv
router_id,hostname,port_id,port_speed
1,RTR-NYC-1,101,10G
1,RTR-NYC-1,102,10G
2,RTR-LA-2,201,100G
```

**Phase 2: The ETL Script (etl.py)**
Requires Neo4j database (can use Neo4j Desktop or Sandbox).

```python
# etl.py
import pandas as pd
from neo4j import GraphDatabase # pip install neo4j pandas

# Configuration
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")

def load_to_graph(tx, router_id, hostname, port_id, speed):
    """What: Cypher query to build the graph | Why: Migrates SQL logic to Nodes/Edges"""
    query = """
    MERGE (r:Router {id: $router_id})
    SET r.hostname = $hostname
    
    MERGE (p:Port {id: $port_id})
    SET p.speed = $speed
    
    MERGE (r)-[:HAS_PORT]->(p)
    """
    tx.run(query, router_id=router_id, hostname=hostname, port_id=port_id, speed=speed)

def main():
    print("1. Extracting...")
    df = pd.read_csv("data/mock_sql_dump.csv")
    
    print("2. Transforming...")
    df['hostname'] = df['hostname'].str.upper() # Clean data
    
    print("3. Loading to Neo4j...")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        with driver.session() as session:
            for index, row in df.iterrows():
                session.execute_write(load_to_graph, 
                                      row['router_id'], 
                                      row['hostname'], 
                                      row['port_id'], 
                                      row['port_speed'])
    print("Pipeline Complete!")

if __name__ == "__main__":
    main()
```

**Phase 3: The API Server (api.py)**
Expose the graph data securely.

```python
# api.py
from fastapi import FastAPI # pip install fastapi uvicorn
from neo4j import GraphDatabase

app = FastAPI()
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")
driver = GraphDatabase.driver(URI, auth=AUTH)

def get_router_ports(tx, router_id: int):
    """What: Executes Cypher read query | Why: Fetches joined data instantly"""
    query = """
    MATCH (r:Router {id: $router_id})-[:HAS_PORT]->(p:Port)
    RETURN r.hostname AS hostname, collect(p.speed) AS ports
    """
    result = tx.run(query, router_id=router_id)
    record = result.single()
    if record:
        return {"hostname": record["hostname"], "ports": record["ports"]}
    return None

@app.get("/api/routers/{router_id}")
def read_router(router_id: int):
    """What: REST Endpoint | Why: Safe access for front-end apps"""
    with driver.session() as session:
        data = session.execute_read(get_router_ports, router_id)
        if data:
            return data
        return {"error": "Router not found"}

# Run with: uvicorn api:app --reload
```

## Complete Execution
1. Create the CSV.
2. Run `python etl.py` to populate Neo4j.
3. Run `uvicorn api:app --reload`.
4. Open your browser to `http://localhost:8000/api/routers/1`.

## Extend It
- **Add GraphQL** - Difficulty: Hard - Learn: Replace FastAPI with an Apollo GraphQL server using `@neo4j/graphql`.
- **Add ML Prediction** - Difficulty: Hard - Learn: Write a script to calculate PageRank in Neo4j and return the router's "importance score" in the API.

## Congratulations! 🎉
**Completed:** 
- Extracted and cleaned relational data.
- Modeled and loaded data into a Graph Database using Cypher.
- Built a REST API to serve Graph data safely.

**Next:** You are now ready to tackle enterprise-grade Inventory Data Architecture! Keep exploring Graph Data Science and advanced ML pipelines.

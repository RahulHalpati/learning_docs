# 01: Relational Schema Design, SQL, and ER Modeling

> **Level:** Beginner/Intermediate  
> **Prerequisites:** Module 00  
> **Time:** 45 minutes  
> **What You'll Learn:** How to design a traditional relational database for inventory and use ER diagrams.

## Introduction
**What:** Designing the tables and relationships for a SQL database.  
**Why:** Relational databases (like PostgreSQL, MySQL) are still the backbone of most enterprise applications. You must understand them before you can migrate away from them.  
**Example:** Creating a structure of rows and columns to hold `Routers`, `Ports`, and `Customers`.

## Core Concepts

### Concept 1: ER (Entity-Relationship) Modeling
- **What:** A visual way to design your database.
- **Why:** Before writing code, you need a blueprint. ER diagrams show Entities (tables), Attributes (columns), and Relationships (how tables connect).
- **Tools:** Draw.io, Lucidchart, MySQL Workbench.

### Concept 2: Relational Schema Design (Normalization)
- **What:** Structuring tables to reduce duplicate data.
- **Why:** If a customer changes their phone number, you only want to update it in one place, not 100 places.

### Concept 3: SQL for Inventory
- **What:** Structured Query Language. The code used to talk to the database.
- **Why:** To insert, update, and retrieve inventory data.

## Practical Example

**Building:** A relational schema for a simple Router and Port inventory.  
**Why:** Shows how physical devices map to SQL tables.

```python
# We will use SQLAlchemy (a Python ORM) to demonstrate the schema
# ORMs allow us to write Python instead of raw SQL strings.

# STANDARD LIBRARY
from datetime import datetime

# THIRD-PARTY (pip install sqlalchemy)
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Router(Base):
    """What: Represents the physical router chassis | Why: Main equipment table"""
    __tablename__ = 'routers'
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String(50), unique=True, nullable=False)
    # What: Router name. Why: unique=True ensures no duplicates.
    
    status = Column(String(20), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to Ports (One-to-Many)
    ports = relationship("Port", back_populates="router")

class Port(Base):
    """What: Represents a plug on the router | Why: Tracks interfaces and connections"""
    __tablename__ = 'ports'
    
    id = Column(Integer, primary_key=True)
    port_number = Column(String(10), nullable=False)
    
    # Foreign Key linking to the Router table
    router_id = Column(Integer, ForeignKey('routers.id'))
    # What: Points to the router this port belongs to. Why: Establishes the relationship.
    
    router = relationship("Router", back_populates="ports")
```

**Equivalent SQL created by the ORM:**
```sql
CREATE TABLE routers (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP
);

CREATE TABLE ports (
    id SERIAL PRIMARY KEY,
    port_number VARCHAR(10) NOT NULL,
    router_id INTEGER REFERENCES routers(id)
);
```

## Best Practices

**✅ DO:**
- **Use Foreign Keys** - Why: It enforces "Referential Integrity". You cannot delete a Router if Ports are still assigned to it.
- **Index Frequently Searched Columns** - Why: If you always search by `hostname`, adding an index makes the query lightning fast.

**❌ DON'T:**
- **Use "SELECT *" in Production** - Why bad: Pulling all columns wastes memory and network bandwidth. | Fix: Select only the columns you need, e.g., `SELECT hostname FROM routers;`.

## Common Mistakes

**Mistake:** Many-to-Many relationships without a Join Table.
**Why:** You cannot easily model a scenario where "One Service uses Many Routers AND One Router supports Many Services" in standard SQL tables directly.
**Fix:** Create a third table (e.g., `Service_Router_Mapping`) that contains foreign keys to both.

## Practice Exercises

**Exercise 1:** Write a JOIN query
- Requirements: Write a SQL query to get the `hostname` of a router and the `port_number` of all its ports.
- Hint: Use `JOIN` on `router_id`.

<details>
<summary>Solution</summary>

```sql
SELECT routers.hostname, ports.port_number
FROM routers
JOIN ports ON routers.id = ports.router_id;
```
**Why it works:** The `JOIN` matches rows in both tables where the IDs align, creating a combined result set.
</details>

## What's Next
**Learned:** ✅ ER Modeling, ✅ Normalization, ✅ ORM and SQL definitions.  
**Next:** Module 02: API Design - How to safely let other systems access this data!  
**Check:** What is the purpose of a Foreign Key?

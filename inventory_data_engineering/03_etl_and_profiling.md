# 03: ETL Pipelines and Data Profiling

> **Level:** Intermediate  
> **Prerequisites:** Module 01 & 02  
> **Time:** 60 minutes  
> **What You'll Learn:** How to build robust pipelines to move data and how to measure data quality.

## Introduction
**What:** **E**xtract, **T**ransform, **L**oad (ETL) is the automated process of moving data. Data Profiling is checking the health of that data.  
**Why:** Network data is messy. You extract it from 5 different vendor systems (Cisco, Juniper, Nokia), transform it to match your central schema, and load it into your database. If you don't profile it, you load garbage.  
**Example:** A script runs every night at 2 AM, downloads a CSV of new router installations, changes the date format to match your database, and saves it.

## Core Concepts

### Concept 1: The ETL Pipeline
- **Extract:** Pull data from an API, FTP server, or database.
- **Transform:** Clean strings, convert timezones, join datasets, apply business rules.
- **Load:** Insert the clean data into the target database (often using bulk inserts for speed).

### Concept 2: Data Profiling
- **What:** Analyzing the data statistically to understand its quality.
- **Why:** To catch errors before they ruin your inventory system.
- **Metrics to Profile:**
  - **Completeness:** Are 20% of the MAC addresses missing?
  - **Uniqueness:** Are there duplicate IP addresses?
  - **Validity:** Do the dates actually exist, or is it "2024-13-45"?

### Concept 3: Idempotency
- **What:** An operation that produces the same result regardless of how many times it is run.
- **Why:** If your ETL script fails halfway and you run it again, it shouldn't duplicate the first half of the data.

## Practical Example

**Building:** A simple Pandas ETL pipeline with Data Profiling.  
**Why:** Pandas is the industry standard Python library for data manipulation.

```python
# STANDARD LIBRARY
import logging

# THIRD-PARTY (pip install pandas)
import pandas as pd

logging.basicConfig(level=logging.INFO)

def run_etl_pipeline(csv_path: str) -> None:
    """
    Extract, profile, transform, and load network data.
    
    What: An end-to-end data pipeline.
    Why: Standard pattern for ingesting raw data.
    """
    
    # --- 1. EXTRACT ---
    logging.info("Extracting data...")
    # Read raw data from a vendor CSV file
    df = pd.read_csv(csv_path)
    
    # --- 2. DATA PROFILING (Pre-transformation) ---
    logging.info("Profiling data...")
    total_rows = len(df)
    missing_hostnames = df['hostname'].isna().sum()
    
    print(f"Total Records: {total_rows}")
    print(f"Missing Hostnames: {missing_hostnames} ({(missing_hostnames/total_rows)*100}%)")
    
    # --- 3. TRANSFORM ---
    logging.info("Transforming data...")
    # Rule 1: Drop rows with no hostname (Data Cleansing)
    df = df.dropna(subset=['hostname'])
    
    # Rule 2: Standardize status to lowercase
    df['status'] = df['status'].str.lower()
    
    # Rule 3: Add a processed timestamp
    df['processed_at'] = pd.Timestamp.now()
    
    # --- 4. LOAD ---
    logging.info("Loading data (Simulated)...")
    # In reality, df.to_sql('routers', con=database_connection)
    print(df.head())
    logging.info("Pipeline Complete!")

# Example usage (assuming 'raw_inventory.csv' exists)
# run_etl_pipeline('raw_inventory.csv')
```

## Best Practices

**✅ DO:**
- **Log Everything** - Why: When a pipeline fails at 3 AM, the logs are the only way to know if it failed during Extract or Load.
- **Fail Fast** - Why: If your data profiling detects that 90% of the data is missing, stop the pipeline immediately. Do not load bad data!

**❌ DON'T:**
- **Process Row-by-Row (For Loops)** - Why bad: Python for-loops are incredibly slow for millions of rows. | Fix: Use vectorized operations in Pandas or Spark.

## Common Mistakes

**Mistake:** Hardcoding file paths or database credentials in the script.
**Why:** Makes the script impossible to run in different environments (Dev vs Prod) and is a massive security risk.
**Fix:** Use Environment Variables (`os.environ.get('DB_URL')`).

## Practice Exercises

**Exercise 1:** Transformation Logic
- Requirements: You have a DataFrame `df` with a column `ip_address`. Some IP addresses have accidental whitespace padding (e.g., `" 192.168.1.1 "`). Write the Pandas code to strip the whitespace.
- Hint: Use `.str.strip()`.

<details>
<summary>Solution</summary>

```python
df['ip_address'] = df['ip_address'].str.strip()
```
**Why it works:** The `.str` accessor allows you to apply string methods to an entire column instantly without a for-loop.
</details>

## What's Next
**Learned:** ✅ ETL Phases, ✅ Data Profiling metrics, ✅ Vectorized transformations.  
**Next:** Module 04: Graph Migration - What happens when our relational database can't handle the complexity anymore?  
**Check:** What does "Idempotent" mean in the context of a data pipeline?

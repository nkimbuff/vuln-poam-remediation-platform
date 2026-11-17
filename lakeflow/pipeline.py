# Lakeflow Declarative Pipeline: scan files -> Bronze -> Silver -> Gold
import dlt
from pyspark.sql import functions as F

VOL = "/Volumes/serverless_stable_seg9n6_catalog/vuln_poam/raw_scans"

# Column descriptions, applied to every table that carries the column (Delta column comments).
COLS = {
 "finding_key": "Natural key of a finding: hostname|cve_id. Same value across weekly scans.",
 "finding_id": "Stable 12-char surrogate id for a finding (sha256 of finding_key). Join key to Lakebase and ML scores.",
 "hostname": "Synthetic host name where the vulnerability was detected. Masked for non-ISSO users in the secure view.",
 "ip_address": "Synthetic IPv4 address of the host. Masked for non-ISSO users in the secure view.",
 "system_id": "Identifier of the owning information system (SYS-nnn). Joins to system reference data.",
 "system_name": "Display name of the owning information system.",
 "criticality": "Mission criticality of the system: MISSION_CRITICAL, HIGH or MODERATE.",
 "owner_team": "Team responsible for remediation on the system.",
 "issm_email": "Synthetic ISSM contact for the system.",
 "cve_id": "CVE identifier of the vulnerability (CVE-YYYY-NNNN).",
 "severity": "Scanner severity: CRITICAL, HIGH, MEDIUM or LOW. Drives the remediation SLA.",
 "cvss": "CVSS base score, 0-10. In silver/gold the highest score seen across scans.",
 "exploit_available": "True if a public exploit is known for the CVE.",
 "scan_date": "Date of the scan that reported the row.",
 "first_seen": "Date of the earliest scan that reported the finding.",
 "last_seen": "Date of the latest scan that reported the finding.",
 "scans_seen": "Number of distinct scans in which the finding appeared.",
 "sla_days": "Remediation SLA in days by severity: CRITICAL 15, HIGH 30, MEDIUM 90, LOW 180.",
 "age_days": "Days from first_seen to the latest scan date in the data (reference date).",
 "sla_due_date": "first_seen plus sla_days: the date remediation is due.",
 "is_overdue": "True when age_days exceeds sla_days.",
 "open_findings": "Count of findings for the system.",
 "overdue_findings": "Count of findings past their SLA due date.",
 "critical_findings": "Count of findings with severity CRITICAL.",
 "avg_age_days": "Average age in days of the system's findings.",
 "_source_file": "Path of the landed scan file the row came from.",
 "_ingested_at": "Timestamp Auto Loader ingested the row.",
 "_rescued_data": "Auto Loader rescue column for unparsed or schema-mismatched data.",
}

TYPES = {  # ordered column -> type per table (must match the DataFrame each table function returns)
 "bronze_scans": "finding_key string, hostname string, ip_address string, system_id string, cve_id string, severity string, cvss string, exploit_available string, scan_date string, _rescued_data string, _source_file string, _ingested_at timestamp",
 "bronze_systems": "system_id string, system_name string, criticality string, owner_team string, issm_email string",
 "gold_findings": "system_id string, finding_key string, hostname string, ip_address string, cve_id string, severity string, cvss double, exploit_available boolean, first_seen date, last_seen date, scans_seen bigint, system_name string, criticality string, owner_team string, sla_days int, age_days int, sla_due_date date, is_overdue boolean, finding_id string",
 "gold_system_risk": "system_id string, system_name string, criticality string, owner_team string, open_findings bigint, overdue_findings bigint, critical_findings bigint, avg_age_days double",
 "silver_findings": "finding_key string, hostname string, ip_address string, system_id string, cve_id string, severity string, cvss double, exploit_available boolean, first_seen date, last_seen date, scans_seen bigint",
 "silver_quarantine": "_source_file string, finding_key string, hostname string, cve_id string, severity string, cvss string, scan_date string",
 "silver_scan_rows": "finding_key string, hostname string, ip_address string, system_id string, cve_id string, severity string, cvss double, exploit_available boolean, scan_date date, _rescued_data string, _source_file string, _ingested_at timestamp",
}

def schema_of(table):
    """DDL schema string with COMMENTs, so descriptions are part of the table definition and survive refreshes."""
    out = []
    for part in TYPES[table].split(", "):
        name, typ = part.split(" ", 1)
        c = COLS.get(name, "").replace("'", "\\'")
        out.append(f"{name} {typ}" + (f" COMMENT '{c}'" if c else ""))
    return ", ".join(out)

@dlt.table(comment="Raw scan rows, ingested incrementally with Auto Loader", schema=schema_of("bronze_scans"))
def bronze_scans():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv").option("header", "true")
            .option("cloudFiles.inferColumnTypes", "false")
            .load(f"{VOL}/scans")
            .withColumn("_source_file", F.col("_metadata.file_path"))
            .withColumn("_ingested_at", F.current_timestamp()))

@dlt.table(comment="System reference data (criticality, owning team)", schema=schema_of("bronze_systems"))
def bronze_systems():
    return spark.read.option("header", "true").csv(f"{VOL}/reference/systems.csv")

@dlt.table(comment="Row-level typed scan rows that pass validation", schema=schema_of("silver_scan_rows"))
@dlt.expect_or_drop("valid_severity", "severity IN ('CRITICAL','HIGH','MEDIUM','LOW')")
@dlt.expect_or_drop("valid_cvss", "cvss IS NOT NULL AND cvss BETWEEN 0 AND 10")
@dlt.expect_or_drop("cve_present", "cve_id LIKE 'CVE-%'")
@dlt.expect_or_drop("known_system", "system_id IS NOT NULL AND system_id != ''")
def silver_scan_rows():
    return (dlt.read("bronze_scans")
            .withColumn("cvss", F.expr("try_cast(cvss AS DOUBLE)"))
            .withColumn("scan_date", F.to_date("scan_date"))
            .withColumn("exploit_available", F.col("exploit_available") == "true"))

VALID = ("severity IN ('CRITICAL','HIGH','MEDIUM','LOW') AND try_cast(cvss AS DOUBLE) BETWEEN 0 AND 10 "
         "AND cve_id LIKE 'CVE-%' AND system_id IS NOT NULL AND system_id != ''")

@dlt.table(comment="Quarantine: scan rows rejected by validation, kept for ISSO review", schema=schema_of("silver_quarantine"))
def silver_quarantine():
    return (dlt.read("bronze_scans").where(F.expr(f"NOT coalesce(({VALID}), false)"))
            .select("_source_file", "finding_key", "hostname", "cve_id", "severity", "cvss", "scan_date"))

@dlt.table(comment="De-duplicated findings (one row per host+CVE) with first/last seen", schema=schema_of("silver_findings"))
def silver_findings():
    return (dlt.read("silver_scan_rows").groupBy("finding_key")
            .agg(F.first("hostname").alias("hostname"), F.first("ip_address").alias("ip_address"),
                 F.first("system_id").alias("system_id"), F.first("cve_id").alias("cve_id"),
                 F.first("severity").alias("severity"), F.max("cvss").alias("cvss"),
                 F.max("exploit_available").alias("exploit_available"),
                 F.min("scan_date").alias("first_seen"), F.max("scan_date").alias("last_seen"),
                 F.countDistinct("scan_date").alias("scans_seen")))

@dlt.table(comment="Gold: findings enriched with system criticality, SLA and age", schema=schema_of("gold_findings"))
def gold_findings():
    sla = F.when(F.col("severity") == "CRITICAL", 15).when(F.col("severity") == "HIGH", 30) \
           .when(F.col("severity") == "MEDIUM", 90).otherwise(180)
    f = dlt.read("silver_findings")
    s = dlt.read("bronze_systems")
    ref = f.agg(F.max("last_seen").alias("ref_date"))
    return (f.join(s, "system_id", "left").crossJoin(ref)
            .withColumn("sla_days", sla)
            .withColumn("age_days", F.datediff("ref_date", "first_seen"))
            .withColumn("sla_due_date", F.date_add("first_seen", sla))
            .withColumn("is_overdue", F.col("age_days") > sla)
            .withColumn("finding_id", F.sha2("finding_key", 256).substr(1, 12))
            .drop("ref_date", "issm_email").select("*"))

@dlt.table(comment="Gold: per-system risk rollup for ISSO review", schema=schema_of("gold_system_risk"))
def gold_system_risk():
    g = dlt.read("gold_findings")
    return (g.groupBy("system_id", "system_name", "criticality", "owner_team")
            .agg(F.count("*").alias("open_findings"),
                 F.sum(F.col("is_overdue").cast("int")).alias("overdue_findings"),
                 F.sum((F.col("severity") == "CRITICAL").cast("int")).alias("critical_findings"),
                 F.round(F.avg("age_days"), 1).alias("avg_age_days")))

# Lakeflow Declarative Pipeline: scan files -> Bronze -> Silver -> Gold
import dlt
from pyspark.sql import functions as F

VOL = "/Volumes/serverless_stable_seg9n6_catalog/vuln_poam/raw_scans"

@dlt.table(comment="Raw scan rows, ingested incrementally with Auto Loader")
def bronze_scans():
    return (spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv").option("header", "true")
            .option("cloudFiles.inferColumnTypes", "false")
            .load(f"{VOL}/scans")
            .withColumn("_source_file", F.col("_metadata.file_path"))
            .withColumn("_ingested_at", F.current_timestamp()))

@dlt.table(comment="System reference data (criticality, owning team)")
def bronze_systems():
    return spark.read.option("header", "true").csv(f"{VOL}/reference/systems.csv")

@dlt.table(comment="Row-level typed scan rows that pass validation")
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

@dlt.table(comment="Quarantine: scan rows rejected by validation, kept for ISSO review")
def silver_quarantine():
    return (dlt.read("bronze_scans").where(F.expr(f"NOT coalesce(({VALID}), false)"))
            .select("_source_file", "finding_key", "hostname", "cve_id", "severity", "cvss", "scan_date"))

@dlt.table(comment="De-duplicated findings (one row per host+CVE) with first/last seen")
def silver_findings():
    return (dlt.read("silver_scan_rows").groupBy("finding_key")
            .agg(F.first("hostname").alias("hostname"), F.first("ip_address").alias("ip_address"),
                 F.first("system_id").alias("system_id"), F.first("cve_id").alias("cve_id"),
                 F.first("severity").alias("severity"), F.max("cvss").alias("cvss"),
                 F.max("exploit_available").alias("exploit_available"),
                 F.min("scan_date").alias("first_seen"), F.max("scan_date").alias("last_seen"),
                 F.countDistinct("scan_date").alias("scans_seen")))

@dlt.table(comment="Gold: findings enriched with system criticality, SLA and age")
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

@dlt.table(comment="Gold: per-system risk rollup for ISSO review")
def gold_system_risk():
    g = dlt.read("gold_findings")
    return (g.groupBy("system_id", "system_name", "criticality", "owner_team")
            .agg(F.count("*").alias("open_findings"),
                 F.sum(F.col("is_overdue").cast("int")).alias("overdue_findings"),
                 F.sum((F.col("severity") == "CRITICAL").cast("int")).alias("critical_findings"),
                 F.round(F.avg("age_days"), 1).alias("avg_age_days")))

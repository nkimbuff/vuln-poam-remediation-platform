# Databricks notebook source
# Scale-test generator (synthetic). Builds ~300k unique findings persisting 1-6 weekly scans each (~1M scan rows),
# 200 systems, 30k hosts. Weeks 0-9 go to scans/; week 10 goes to staging/ for an incremental-update test.
# Seeded by construction (all values derive from hash(id)), so reruns produce the same data.
from pyspark.sql import functions as F
CAT, SCH = "serverless_stable_seg9n6_catalog", "vuln_poam_scale"
V = f"/Volumes/{CAT}/{SCH}/raw_scans"
N_SYSTEMS, N_HOSTS, N_CVES, N_FINDINGS, WEEKS = 200, 30000, 2000, 300000, 10

pool = (spark.range(N_FINDINGS)
  .select(F.pmod(F.hash("id", F.lit(1)), N_HOSTS).alias("h"), F.pmod(F.hash("id", F.lit(2)), N_CVES).alias("c"),
          F.pmod(F.hash("id", F.lit(3)), WEEKS + 1).alias("first_week"), (1 + F.pmod(F.hash("id", F.lit(4)), 6)).alias("life"),
          F.pmod(F.hash("id", F.lit(12)), 200).alias("dirty"))
  .withColumn("hostname", F.concat(F.lit("host-"), F.lpad(F.col("h").cast("string"), 5, "0"), F.lit(".example.internal")))
  .withColumn("ip_address", F.concat_ws(".", F.lit("10"), F.pmod(F.hash("h", F.lit(5)), 256).cast("string"),
                                         F.pmod(F.hash("h", F.lit(6)), 256).cast("string"), (1 + F.pmod(F.hash("h", F.lit(7)), 254)).cast("string")))
  .withColumn("system_id", F.concat(F.lit("SYS-"), F.lpad((F.pmod(F.hash("h", F.lit(8)), N_SYSTEMS) + 1).cast("string"), 3, "0")))
  .withColumn("cve_id", F.concat(F.lit("CVE-2025-"), F.lpad((1000 + F.col("c")).cast("string"), 4, "0")))
  .withColumn("sev_n", F.pmod(F.hash("c", F.lit(9)), 10))
  .withColumn("severity", F.when(F.col("sev_n") == 0, "CRITICAL").when(F.col("sev_n") <= 2, "HIGH").when(F.col("sev_n") <= 6, "MEDIUM").otherwise("LOW"))
  .withColumn("cvss", F.round(2 + F.pmod(F.hash("c", F.lit(10)), 80) / 10.0, 1))
  .withColumn("exploit_available", F.pmod(F.hash("c", F.lit(11)), 100) < 15)
  .withColumn("finding_key", F.concat_ws("|", "hostname", "cve_id"))
  .dropDuplicates(["finding_key"]))

rows = (pool.withColumn("week", F.explode(F.sequence("first_week", F.least(F.col("first_week") + F.col("life") - 1, F.lit(WEEKS)))))
  .withColumn("scan_date", F.date_add(F.lit("2026-09-07").cast("date"), 7 * F.col("week")))
  .withColumn("severity", F.when(F.col("dirty") == 0, F.lit("UNKNOWN")).otherwise(F.col("severity")))   # ~0.5% dirty rows
  .select("finding_key", "hostname", "ip_address", "system_id", "cve_id", "severity", "cvss",
          F.col("exploit_available").cast("string").alias("exploit_available"), F.col("scan_date").cast("string").alias("scan_date"), "week"))

rows.filter("week < 10").drop("week").repartition(40).write.mode("overwrite").option("header", True).csv(f"{V}/scans")
rows.filter("week = 10").drop("week").repartition(4).write.mode("overwrite").option("header", True).csv(f"{V}/staging")

teams = F.array(*[F.lit(t) for t in ["Platform Ops", "App Dev", "Network Eng", "Database Admin", "End User Computing"]])
(spark.range(N_SYSTEMS).select(F.concat(F.lit("SYS-"), F.lpad((F.col("id") + 1).cast("string"), 3, "0")).alias("system_id"))
  .withColumn("system_name", F.concat(F.lit("Synthetic System "), F.substring("system_id", 5, 3)))
  .withColumn("criticality", F.element_at(F.array(F.lit("MISSION_CRITICAL"), F.lit("HIGH"), F.lit("MODERATE")), (F.pmod(F.hash("system_id"), 3) + 1).cast("int")))
  .withColumn("owner_team", F.element_at(teams, (F.pmod(F.hash("system_id", F.lit(1)), 5) + 1).cast("int")))
  .withColumn("issm_email", F.concat(F.lit("issm."), F.substring("system_id", 5, 3), F.lit("@example.gov")))
  .coalesce(1).write.mode("overwrite").option("header", True).csv(f"{V}/reference/systems.csv"))

out = {"unique_findings": pool.count(), "scan_rows_weeks_0_9": spark.read.option("header", True).csv(f"{V}/scans").count(),
       "scan_rows_week_10_staged": spark.read.option("header", True).csv(f"{V}/staging").count()}
print(out); dbutils.notebook.exit(str(out))

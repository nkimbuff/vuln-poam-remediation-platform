-- Unity Catalog governance for vuln_poam (run statement by statement)
CREATE OR REPLACE FUNCTION serverless_stable_seg9n6_catalog.vuln_poam.mask_host(v STRING)
  RETURN CASE WHEN is_account_group_member('isso_analysts') OR is_member('admins') THEN v
              ELSE concat(substr(v, 1, 5), '****') END;
ALTER TABLE serverless_stable_seg9n6_catalog.vuln_poam.gold_findings SET TAGS ('sensitivity'='internal', 'data_marking'='cui');
ALTER TABLE serverless_stable_seg9n6_catalog.vuln_poam.bronze_scans SET TAGS ('sensitivity'='internal', 'data_marking'='cui', 'layer'='bronze');
ALTER TABLE serverless_stable_seg9n6_catalog.vuln_poam.gold_system_risk SET TAGS ('sensitivity'='internal', 'layer'='gold');
ALTER TABLE serverless_stable_seg9n6_catalog.vuln_poam.gold_findings ALTER COLUMN hostname SET TAGS ('pii_like'='asset_identifier');
ALTER TABLE serverless_stable_seg9n6_catalog.vuln_poam.gold_findings ALTER COLUMN ip_address SET TAGS ('pii_like'='asset_identifier');
CREATE OR REPLACE VIEW serverless_stable_seg9n6_catalog.vuln_poam.gold_findings_secure AS
  SELECT finding_id, system_id, system_name, criticality, owner_team,
         serverless_stable_seg9n6_catalog.vuln_poam.mask_host(hostname) AS hostname,
         serverless_stable_seg9n6_catalog.vuln_poam.mask_host(ip_address) AS ip_address,
         cve_id, severity, cvss, exploit_available, first_seen, last_seen, scans_seen,
         sla_days, age_days, sla_due_date, is_overdue
  FROM serverless_stable_seg9n6_catalog.vuln_poam.gold_findings;
GRANT USE SCHEMA ON SCHEMA serverless_stable_seg9n6_catalog.vuln_poam TO `account users`;
GRANT SELECT ON VIEW serverless_stable_seg9n6_catalog.vuln_poam.gold_findings_secure TO `account users`;

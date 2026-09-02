# P01 Wu-comparable aggregate export
#
# Purpose
#   Rebuild the simple annual open-cohort analysis directly from the live
#   MarketScan analytic files. A woman may contribute one eligible record in
#   each study year and may requalify after the prior-surgery washout, matching
#   the counting convention used for the Wu-comparable analysis.
#
# Data governance
#   This script runs only on the Yale MarketScan server. It writes aggregate
#   CSV files to ~/p01_wu_out. No person-level data are exported.

library(duckdb)
library(DBI)

ROOT <- "/data/MarketScan_data/cohort/analytic"
OUT <- path.expand("~/p01_wu_out")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
dir.create(path.expand("~/duckdb_tmp"), showWarnings = FALSE, recursive = TRUE)

con <- dbConnect(duckdb(shared_home = FALSE))
dbExecute(con, "SET memory_limit='4GB'")
dbExecute(con, "SET threads=2")
dbExecute(con, sprintf("SET temp_directory='%s'", path.expand("~/duckdb_tmp")))

BAND <- paste(
  "CASE",
  "WHEN age_at_index < 30 THEN '18-29'",
  "WHEN age_at_index < 40 THEN '30-39'",
  "WHEN age_at_index < 50 THEN '40-49'",
  "WHEN age_at_index < 60 THEN '50-59'",
  "WHEN age_at_index < 70 THEN '60-69'",
  "WHEN age_at_index < 80 THEN '70-79'",
  "ELSE '80-89' END"
)

for (db in c("CCAE", "MDCR")) {
  fa <- sprintf("read_parquet('%s/%s_final_analysis.parquet')", ROOT, db)
  where <- "study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89"

  age <- dbGetQuery(con, sprintf("
    SELECT age_at_index AS age,
           COUNT(*) AS person_years,
           SUM(incident_sui) AS sui_operations,
           SUM(incident_pop) AS pop_operations,
           SUM(CASE WHEN incident_sui=1 OR incident_pop=1 THEN 1 ELSE 0 END) AS any_operations,
           SUM(CASE WHEN incident_sui=1 AND incident_pop=1 THEN 1 ELSE 0 END) AS both_same_year
    FROM %s WHERE %s
    GROUP BY 1 ORDER BY 1", fa, where))
  write.csv(age, file.path(OUT, sprintf("%s_wu_by_age.csv", db)), row.names = FALSE)

  year_age <- dbGetQuery(con, sprintf("
    SELECT study_year, age_at_index AS age,
           COUNT(*) AS person_years,
           SUM(incident_sui) AS sui_operations,
           SUM(incident_pop) AS pop_operations,
           SUM(CASE WHEN incident_sui=1 OR incident_pop=1 THEN 1 ELSE 0 END) AS any_operations,
           SUM(CASE WHEN incident_sui=1 AND incident_pop=1 THEN 1 ELSE 0 END) AS both_same_year
    FROM %s WHERE %s
    GROUP BY 1,2 ORDER BY 1,2", fa, where))
  write.csv(year_age, file.path(OUT, sprintf("%s_wu_by_year_age.csv", db)), row.names = FALSE)

  band <- dbGetQuery(con, sprintf("
    SELECT %s AS age_band,
           COUNT(*) AS person_years,
           COUNT(DISTINCT ENROLID) AS contributing_women,
           SUM(incident_sui) AS sui_operations,
           SUM(incident_pop) AS pop_operations,
           SUM(CASE WHEN incident_sui=1 OR incident_pop=1 THEN 1 ELSE 0 END) AS any_operations,
           SUM(CASE WHEN incident_sui=1 AND incident_pop=1 THEN 1 ELSE 0 END) AS both_same_year
    FROM %s WHERE %s
    GROUP BY 1 ORDER BY 1", BAND, fa, where))
  write.csv(band, file.path(OUT, sprintf("%s_wu_by_band.csv", db)), row.names = FALSE)

  totals <- dbGetQuery(con, sprintf("
    SELECT '%s' AS database,
           COUNT(*) AS person_years,
           COUNT(DISTINCT ENROLID) AS contributing_women,
           COUNT(DISTINCT CASE WHEN incident_sui=1 OR incident_pop=1 THEN ENROLID END) AS unique_operated_women,
           SUM(incident_sui) AS sui_operations,
           SUM(incident_pop) AS pop_operations,
           SUM(CASE WHEN incident_sui=1 OR incident_pop=1 THEN 1 ELSE 0 END) AS any_operations,
           SUM(CASE WHEN incident_sui=1 AND incident_pop=1 THEN 1 ELSE 0 END) AS both_same_year
    FROM %s WHERE %s", db, fa, where))
  write.csv(totals, file.path(OUT, sprintf("%s_wu_totals.csv", db)), row.names = FALSE)
}

totals <- do.call(rbind, lapply(c("CCAE", "MDCR"), function(db) {
  read.csv(file.path(OUT, sprintf("%s_wu_totals.csv", db)))
}))

# ENROLID is stable across MarketScan products. Some women transition from
# CCAE to MDCR in different years, so pooled distinct-person counts must be
# calculated across the union rather than summed across database-specific
# counts. Woman-years and operation-person-years remain additive because the
# verified 2014-2024 risk sets contain no same-person, same-year overlap.
pooled_distinct <- dbGetQuery(con, sprintf("
  WITH pooled AS (
    SELECT ENROLID, study_year, incident_sui, incident_pop
    FROM read_parquet('%s/CCAE_final_analysis.parquet')
    WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
    UNION ALL
    SELECT ENROLID, study_year, incident_sui, incident_pop
    FROM read_parquet('%s/MDCR_final_analysis.parquet')
    WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
  )
  SELECT COUNT(DISTINCT ENROLID) AS contributing_women,
         COUNT(DISTINCT CASE WHEN incident_sui=1 OR incident_pop=1 THEN ENROLID END)
           AS unique_operated_women,
         COUNT(*) - COUNT(DISTINCT (ENROLID, study_year)) AS duplicate_woman_years
  FROM pooled", ROOT, ROOT))

pooled <- data.frame(
  database = "Pooled",
  person_years = sum(totals$person_years),
  contributing_women = pooled_distinct$contributing_women,
  unique_operated_women = pooled_distinct$unique_operated_women,
  sui_operations = sum(totals$sui_operations),
  pop_operations = sum(totals$pop_operations),
  any_operations = sum(totals$any_operations),
  both_same_year = sum(totals$both_same_year)
)
write.csv(rbind(totals, pooled), file.path(OUT, "P01_wu_totals.csv"), row.names = FALSE)

# Structural reconciliation. Study-specific expected totals are kept in the
# governed internal validation record, not in the external code repository.
stopifnot(pooled$person_years > 0)
stopifnot(pooled$any_operations >= pooled$unique_operated_women)
stopifnot(pooled_distinct$duplicate_woman_years == 0)

writeLines(c(
  sprintf("Run time UTC: %s", format(Sys.time(), tz = "UTC")),
  sprintf("Person-years: %s", format(pooled$person_years, big.mark = ",", scientific = FALSE)),
  sprintf("Qualifying operation-person-years: %s", format(pooled$any_operations, big.mark = ",", scientific = FALSE)),
  sprintf("Unique operated women: %s", format(pooled$unique_operated_women, big.mark = ",", scientific = FALSE)),
  sprintf("Repeat qualifying woman-years: %s", pooled$any_operations - pooled$unique_operated_women),
  "All structural count checks passed."
), file.path(OUT, "P01_wu_run_log.txt"))

dbDisconnect(con, shutdown = TRUE)
cat("P01 Wu-comparable aggregate export complete.\n")

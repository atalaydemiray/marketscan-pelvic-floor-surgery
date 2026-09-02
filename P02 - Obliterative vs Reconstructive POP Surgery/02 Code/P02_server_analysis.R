# P02 server-side aggregate analysis
#
# Governance: Atalay confirmed on 1 September 2026 that this follow-up scope
# had already been cleared with DataMed/Yujia. Row-level data remain on server.

library(duckdb)
library(DBI)

ROOT <- "/data/MarketScan_data/cohort/analytic"
OUT <- path.expand("~/p02_aggregate_out")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
dir.create(path.expand("~/duckdb_tmp"), showWarnings = FALSE, recursive = TRUE)

con <- dbConnect(duckdb(shared_home = FALSE))
on.exit(dbDisconnect(con, shutdown = TRUE), add = TRUE)
dbExecute(con, "SET memory_limit='4GB'")
dbExecute(con, "SET threads=2")
dbExecute(con, sprintf("SET temp_directory='%s'", path.expand("~/duckdb_tmp")))

OBLITERATIVE <- c("57106", "57110", "57120", "58275", "58280")
RECONSTRUCTIVE <- c(
  "56810", "57107", "57109", "57111", "57112", "57200", "57210", "57230",
  "57240", "57250", "57260", "57265", "57267", "57268", "57270", "57280",
  "57282", "57283", "57284", "57285", "57423", "57425", "58400"
)
QUALIFYING <- c(OBLITERATIVE, RECONSTRUCTIVE)

sql_list <- function(x) paste(sprintf("'%s'", x), collapse = ", ")
has_any <- function(x, field = "codes") paste(sprintf("list_contains(%s, '%s')", field, x), collapse = " OR ")

AGE5 <- paste(
  "CASE",
  "WHEN age_at_index BETWEEN 18 AND 24 THEN '18-24'",
  "WHEN age_at_index BETWEEN 25 AND 84 THEN",
  "  printf('%02d-%02d', CAST(5 * floor(age_at_index / 5) AS INTEGER), CAST(5 * floor(age_at_index / 5) + 4 AS INTEGER))",
  "WHEN age_at_index BETWEEN 85 AND 89 THEN '85-89'",
  "END"
)

BROAD_AGE <- paste(
  "CASE",
  "WHEN age_at_index < 65 THEN '<65'",
  "WHEN age_at_index < 75 THEN '65-74'",
  "WHEN age_at_index < 85 THEN '75-84'",
  "ELSE '85-89' END"
)

fa_ccae <- sprintf("read_parquet('%s/CCAE_final_analysis.parquet')", ROOT)
fa_mdcr <- sprintf("read_parquet('%s/MDCR_final_analysis.parquet')", ROOT)
se_ccae <- sprintf("read_parquet('%s/CCAE_surgery_events.parquet')", ROOT)
se_mdcr <- sprintf("read_parquet('%s/MDCR_surgery_events.parquet')", ROOT)

# Preserve the locked Wu-style pooled person-year denominator. A second view
# resolves one key per woman-year for event joins and prevents join expansion.
dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW eligible_rows AS
  SELECT *, %s AS age5, %s AS broad_age FROM (
    SELECT 'CCAE' AS database, ENROLID, study_year, index_date, age_at_index
    FROM %s WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
    UNION ALL
    SELECT 'MDCR' AS database, ENROLID, study_year, index_date, age_at_index
    FROM %s WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
  )", AGE5, BROAD_AGE, fa_ccae, fa_mdcr))

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW eligible_keys AS
  SELECT *, %s AS age5, %s AS broad_age FROM (
    SELECT ENROLID, study_year, MIN(index_date) AS index_date,
           MIN(age_at_index) AS age_at_index
    FROM eligible_rows GROUP BY ENROLID, study_year
  )", AGE5, BROAD_AGE))

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW surgery_all AS
  SELECT 'CCAE' AS database, * FROM %s
  UNION ALL
  SELECT 'MDCR' AS database, * FROM %s", se_ccae, se_mdcr))

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW p02_episodes AS
  WITH dates AS (
    SELECT s.ENROLID, CAST(s.svcdate AS DATE) AS svcdate,
           MIN(e.study_year) AS study_year, MIN(e.age_at_index) AS age_at_index,
           MIN(e.age5) AS age5, MIN(e.broad_age) AS broad_age,
           CASE WHEN COUNT(DISTINCT s.database)=1 THEN MIN(s.database) ELSE 'BOTH' END AS event_database,
           MAX(CASE WHEN %s THEN 1 ELSE 0 END) AS has_obliterative,
           MAX(CASE WHEN %s THEN 1 ELSE 0 END) AS has_reconstructive
    FROM surgery_all s
    INNER JOIN eligible_keys e
      ON s.ENROLID=e.ENROLID AND CAST(s.YEAR AS INTEGER)=e.study_year
    GROUP BY s.ENROLID, CAST(s.svcdate AS DATE)
    HAVING MAX(CASE WHEN %s THEN 1 ELSE 0 END)=1
  )
  SELECT *,
         CASE WHEN has_obliterative=1 THEN 'Obliterative' ELSE 'Reconstructive' END AS procedure_group,
         CASE WHEN has_obliterative=1 AND has_reconstructive=1 THEN 1 ELSE 0 END AS mixed_code_date
  FROM dates",
  has_any(OBLITERATIVE), has_any(RECONSTRUCTIVE), has_any(QUALIFYING)))

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p02_first AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM p02_episodes
  ) WHERE rn=1")

outputs <- list(
  denominators = "SELECT study_year, age5, broad_age, COUNT(*) AS woman_years
                  FROM eligible_rows GROUP BY 1,2,3 ORDER BY 1,2",
  first_by_year_age = "SELECT study_year, age5, procedure_group,
                              COUNT(*) AS women, SUM(mixed_code_date) AS mixed_code_dates
                       FROM p02_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_by_year = "SELECT study_year, procedure_group, COUNT(*) AS women,
                          SUM(mixed_code_date) AS mixed_code_dates
                   FROM p02_first GROUP BY 1,2 ORDER BY 1,2",
  first_by_age = "SELECT age5, procedure_group, COUNT(*) AS women,
                         SUM(mixed_code_date) AS mixed_code_dates
                  FROM p02_first GROUP BY 1,2 ORDER BY 1,2",
  first_by_year_broad_age = "SELECT study_year, broad_age, procedure_group,
                                    COUNT(*) AS women, SUM(mixed_code_date) AS mixed_code_dates
                             FROM p02_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_by_broad_age = "SELECT broad_age, procedure_group, COUNT(*) AS women,
                               SUM(mixed_code_date) AS mixed_code_dates
                        FROM p02_first GROUP BY 1,2 ORDER BY 1,2",
  first_by_database = "SELECT event_database, procedure_group, COUNT(*) AS women,
                              SUM(mixed_code_date) AS mixed_code_dates
                       FROM p02_first GROUP BY 1,2 ORDER BY 1,2",
  total_burden = "SELECT study_year, age5, procedure_group,
                         COUNT(*) AS operation_dates, SUM(mixed_code_date) AS mixed_code_dates
                  FROM p02_episodes GROUP BY 1,2,3 ORDER BY 1,2,3",
  total_burden_by_year = "SELECT study_year, procedure_group,
                                 COUNT(*) AS operation_dates, SUM(mixed_code_date) AS mixed_code_dates
                          FROM p02_episodes GROUP BY 1,2 ORDER BY 1,2",
  totals = "SELECT COUNT(*) AS first_observed_women,
                   SUM(CASE WHEN procedure_group='Obliterative' THEN 1 ELSE 0 END) AS obliterative,
                   SUM(CASE WHEN procedure_group='Reconstructive' THEN 1 ELSE 0 END) AS reconstructive,
                   SUM(mixed_code_date) AS mixed_code_dates
            FROM p02_first"
)

for (name in names(outputs)) {
  write.csv(dbGetQuery(con, outputs[[name]]),
            file.path(OUT, sprintf("pooled_%s_server_aggregate.csv", name)), row.names = FALSE)
}

code_sql <- sprintf("WITH expanded AS (
    SELECT s.ENROLID, CAST(s.svcdate AS DATE) AS svcdate, u.code
    FROM surgery_all s
    INNER JOIN eligible_keys e
      ON s.ENROLID=e.ENROLID AND CAST(s.YEAR AS INTEGER)=e.study_year,
    UNNEST(s.codes) AS u(code)
    WHERE u.code IN (%s)
  )
  SELECT code, COUNT(*) AS claim_rows,
         COUNT(DISTINCT CONCAT(CAST(ENROLID AS VARCHAR), '|', CAST(svcdate AS VARCHAR))) AS operation_dates
  FROM expanded GROUP BY 1 ORDER BY 1", sql_list(QUALIFYING))
write.csv(dbGetQuery(con, code_sql),
          file.path(OUT, "pooled_code_contribution_server_aggregate.csv"), row.names = FALSE)

denominator_total <- dbGetQuery(con, "SELECT COUNT(*) AS n FROM eligible_rows")$n
stopifnot(denominator_total > 0)

writeLines(c(
  sprintf("Run time UTC: %s", format(Sys.time(), tz = "UTC")),
  "P02 server-side aggregation completed within the confirmed follow-up scope.",
  "First observed procedure was resolved globally across CCAE and MDCR.",
  sprintf("Pooled person-year denominator is nonzero: %s.", format(denominator_total, big.mark=",", scientific=FALSE)),
  "Review all cells for disclosure safety before transferring aggregate files."
), file.path(OUT, "P02_run_log.txt"))

cat("P02 aggregate analysis complete. Outputs remain on the Yale server.\n")

# P03 server-side aggregate analysis
#
# Governance: Atalay confirmed on 1 September 2026 that this follow-up scope
# had already been cleared with DataMed/Yujia. Row-level data remain on server.

library(duckdb)
library(DBI)

ROOT <- "/data/MarketScan_data/cohort/analytic"
OUT <- path.expand("~/p03_aggregate_out")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
dir.create(path.expand("~/duckdb_tmp"), showWarnings = FALSE, recursive = TRUE)

con <- dbConnect(duckdb(shared_home = FALSE))
on.exit(dbDisconnect(con, shutdown = TRUE), add = TRUE)
dbExecute(con, "SET memory_limit='4GB'")
dbExecute(con, "SET threads=2")
dbExecute(con, sprintf("SET temp_directory='%s'", path.expand("~/duckdb_tmp")))

AGE5 <- paste(
  "CASE",
  "WHEN age_at_index BETWEEN 18 AND 24 THEN '18-24'",
  "WHEN age_at_index BETWEEN 25 AND 84 THEN",
  "  printf('%02d-%02d', CAST(5 * floor(age_at_index / 5) AS INTEGER), CAST(5 * floor(age_at_index / 5) + 4 AS INTEGER))",
  "WHEN age_at_index BETWEEN 85 AND 89 THEN '85-89'",
  "END"
)

fa_ccae <- sprintf("read_parquet('%s/CCAE_final_analysis.parquet')", ROOT)
fa_mdcr <- sprintf("read_parquet('%s/MDCR_final_analysis.parquet')", ROOT)
se_ccae <- sprintf("read_parquet('%s/CCAE_surgery_events.parquet')", ROOT)
se_mdcr <- sprintf("read_parquet('%s/MDCR_surgery_events.parquet')", ROOT)

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW eligible_rows AS
  SELECT *, %s AS age5 FROM (
    SELECT 'CCAE' AS database, ENROLID, study_year, index_date, age_at_index
    FROM %s WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
    UNION ALL
    SELECT 'MDCR' AS database, ENROLID, study_year, index_date, age_at_index
    FROM %s WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
  )", AGE5, fa_ccae, fa_mdcr))

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW eligible_keys AS
  SELECT *, %s AS age5 FROM (
    SELECT ENROLID, study_year, MIN(index_date) AS index_date,
           MIN(age_at_index) AS age_at_index
    FROM eligible_rows GROUP BY ENROLID, study_year
  )", AGE5))

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW surgery_all AS
  SELECT 'CCAE' AS database, * FROM %s
  UNION ALL
  SELECT 'MDCR' AS database, * FROM %s", se_ccae, se_mdcr))

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_episodes AS
  WITH dates AS (
    SELECT s.ENROLID, CAST(s.svcdate AS DATE) AS svcdate,
           MIN(e.study_year) AS study_year, MIN(e.age_at_index) AS age_at_index,
           MIN(e.age5) AS age5,
           CASE WHEN COUNT(DISTINCT s.database)=1 THEN MIN(s.database) ELSE 'BOTH' END AS event_database,
           MAX(CASE WHEN list_contains(s.codes, '57288') THEN 1 ELSE 0 END) AS has_sling,
           MAX(CASE WHEN list_contains(s.codes, '51715') THEN 1 ELSE 0 END) AS has_bulking,
           MAX(CASE WHEN s.is_pop_surgery=1 THEN 1 ELSE 0 END) AS pop_same_day
    FROM surgery_all s
    INNER JOIN eligible_keys e
      ON s.ENROLID=e.ENROLID AND CAST(s.YEAR AS INTEGER)=e.study_year
    GROUP BY s.ENROLID, CAST(s.svcdate AS DATE)
    HAVING MAX(CASE WHEN list_contains(s.codes, '57288') OR list_contains(s.codes, '51715')
                    THEN 1 ELSE 0 END)=1
  )
  SELECT *,
         CASE WHEN has_sling=1 AND has_bulking=1 THEN 'Hybrid'
              WHEN has_sling=1 THEN 'Sling' ELSE 'Bulking' END AS procedure_category,
         CASE WHEN pop_same_day=1 THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context,
         CASE WHEN study_year <= 2019 THEN '2014-2019' ELSE '2020-2024' END AS study_period
  FROM dates")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_first AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM p03_episodes
  ) WHERE rn=1")

make_burden <- function(window_days) {
  view_name <- sprintf("p03_burden_%03d", window_days)
  dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW %s AS
    WITH bulking_lag AS (
      SELECT *, LAG(svcdate) OVER (PARTITION BY ENROLID ORDER BY svcdate) AS prior_bulking_date
      FROM p03_episodes WHERE procedure_category='Bulking'
    ),
    bulking_marked AS (
      SELECT *, CASE WHEN prior_bulking_date IS NULL
                          OR DATE_DIFF('day', prior_bulking_date, svcdate) > %d
                     THEN 1 ELSE 0 END AS new_course
      FROM bulking_lag
    ),
    bulking_numbered AS (
      SELECT *, SUM(new_course) OVER (
        PARTITION BY ENROLID ORDER BY svcdate ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      ) AS course_id
      FROM bulking_marked
    ),
    bulking_courses AS (
      SELECT ENROLID, MIN(svcdate) AS svcdate,
             ARG_MIN(study_year, svcdate) AS study_year,
             ARG_MIN(age_at_index, svcdate) AS age_at_index,
             ARG_MIN(age5, svcdate) AS age5,
             CASE WHEN MAX(pop_same_day)=1 THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context,
             'Bulking course' AS burden_category,
             COUNT(*) AS injections_in_course
      FROM bulking_numbered GROUP BY ENROLID, course_id
    ),
    nonbulking AS (
      SELECT ENROLID, svcdate, study_year, age_at_index, age5, pop_context,
             CASE WHEN procedure_category='Sling' THEN 'Sling episode' ELSE 'Hybrid episode' END AS burden_category,
             1 AS injections_in_course
      FROM p03_episodes WHERE procedure_category IN ('Sling', 'Hybrid')
    )
    SELECT * FROM bulking_courses UNION ALL SELECT * FROM nonbulking",
    view_name, window_days))
  view_name
}

outputs <- list(
  denominators = "SELECT study_year, age5, COUNT(*) AS woman_years
                  FROM eligible_rows GROUP BY 1,2 ORDER BY 1,2",
  first_by_year = "SELECT study_year, pop_context, procedure_category, COUNT(*) AS women
                   FROM p03_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_by_year_age = "SELECT study_year, age5, pop_context, procedure_category, COUNT(*) AS women
                       FROM p03_first GROUP BY 1,2,3,4 ORDER BY 1,2,3,4",
  first_by_period_age = "SELECT study_period, age5, pop_context, procedure_category, COUNT(*) AS women
                         FROM p03_first GROUP BY 1,2,3,4 ORDER BY 1,2,3,4",
  first_by_period = "SELECT study_period, pop_context, procedure_category, COUNT(*) AS women
                     FROM p03_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_by_database = "SELECT event_database, pop_context, procedure_category, COUNT(*) AS women
                       FROM p03_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_totals = "SELECT pop_context, procedure_category, COUNT(*) AS women
                  FROM p03_first GROUP BY 1,2 ORDER BY 1,2"
)

for (name in names(outputs)) {
  write.csv(dbGetQuery(con, outputs[[name]]),
            file.path(OUT, sprintf("pooled_%s_server_aggregate.csv", name)), row.names = FALSE)
}

for (window_days in c(90L, 180L)) {
  burden_view <- make_burden(window_days)
  burden_sql <- sprintf("SELECT study_year, age5, pop_context, burden_category,
                                COUNT(*) AS treatment_units,
                                SUM(injections_in_course) AS contributing_injection_dates
                         FROM %s GROUP BY 1,2,3,4 ORDER BY 1,2,3,4", burden_view)
  write.csv(dbGetQuery(con, burden_sql),
            file.path(OUT, sprintf("pooled_total_burden_%03dd_server_aggregate.csv", window_days)), row.names = FALSE)

  burden_year_sql <- sprintf("SELECT study_year, pop_context, burden_category,
                                     COUNT(*) AS treatment_units,
                                     SUM(injections_in_course) AS contributing_injection_dates
                              FROM %s GROUP BY 1,2,3 ORDER BY 1,2,3", burden_view)
  write.csv(dbGetQuery(con, burden_year_sql),
            file.path(OUT, sprintf("pooled_total_burden_%03dd_by_year_server_aggregate.csv", window_days)), row.names = FALSE)

  burden_totals_sql <- sprintf("SELECT pop_context, burden_category,
                                       COUNT(*) AS treatment_units,
                                       SUM(injections_in_course) AS contributing_injection_dates
                                FROM %s GROUP BY 1,2 ORDER BY 1,2", burden_view)
  write.csv(dbGetQuery(con, burden_totals_sql),
            file.path(OUT, sprintf("pooled_total_burden_%03dd_totals_server_aggregate.csv", window_days)), row.names = FALSE)
}

denominator_total <- dbGetQuery(con, "SELECT COUNT(*) AS n FROM eligible_rows")$n
stopifnot(denominator_total > 0)

writeLines(c(
  sprintf("Run time UTC: %s", format(Sys.time(), tz = "UTC")),
  "P03 server-side aggregation completed within the confirmed follow-up scope.",
  "First observed procedure and bulking courses were resolved globally across CCAE and MDCR.",
  sprintf("Pooled person-year denominator is nonzero: %s.", format(denominator_total, big.mark=",", scientific=FALSE)),
  "Primary bulking-course window: 90 days; sensitivity: 180 days.",
  "Review all cells for disclosure safety before transferring aggregate files."
), file.path(OUT, "P03_run_log.txt"))

cat("P03 aggregate analysis complete. Outputs remain on the Yale server.\n")

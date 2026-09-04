# P03 server-side aggregate analysis
#
# Row-level data remain on the licensed Yale server. Only disclosure-screened
# aggregate outputs may be transferred.

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

dbExecute(con, "CREATE OR REPLACE TEMP VIEW surgery_dedup AS
  SELECT ENROLID, CAST(svcdate AS DATE) AS svcdate,
         YEAR(CAST(svcdate AS DATE)) AS svc_year,
         CASE WHEN COUNT(DISTINCT database)=1 THEN MIN(database) ELSE 'BOTH' END AS event_database,
         list_distinct(flatten(list(codes))) AS codes,
         MAX(is_pop_surgery) AS is_pop_surgery
  FROM surgery_all
  GROUP BY ENROLID, CAST(svcdate AS DATE)")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_episodes AS
  WITH dates AS (
    SELECT s.ENROLID, s.svcdate, e.study_year, e.age_at_index, e.age5,
           s.event_database,
           MAX(CASE WHEN list_contains(s.codes, '57288') THEN 1 ELSE 0 END) AS has_sling,
           MAX(CASE WHEN list_contains(s.codes, '51715') THEN 1 ELSE 0 END) AS has_bulking,
           MAX(CASE WHEN s.is_pop_surgery=1 THEN 1 ELSE 0 END) AS pop_same_day
    FROM surgery_dedup s
    INNER JOIN eligible_keys e
      ON s.ENROLID=e.ENROLID AND s.svc_year=e.study_year
    GROUP BY s.ENROLID,s.svcdate,e.study_year,e.age_at_index,e.age5,s.event_database
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

# The secondary burden estimand follows all 2014-2024 sling/bulking dates
# visible for women who contributed at least one eligible woman-year. It is not
# restricted to eligible years and is therefore reported as counts/shares, not
# as a rate over the parent woman-year denominator.
dbExecute(con, "CREATE OR REPLACE TEMP VIEW ever_eligible AS
  SELECT ENROLID, MIN(age_at_index-study_year) AS birth_offset
  FROM eligible_keys GROUP BY ENROLID")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_period_episodes AS
  SELECT s.ENROLID,s.svcdate,s.svc_year AS study_year,
         s.svc_year + e.birth_offset AS age_at_index,
         CASE WHEN s.svc_year + e.birth_offset<30 THEN '18-29'
              WHEN s.svc_year + e.birth_offset<35 THEN '30-34'
              WHEN s.svc_year + e.birth_offset<40 THEN '35-39'
              WHEN s.svc_year + e.birth_offset<45 THEN '40-44'
              WHEN s.svc_year + e.birth_offset<50 THEN '45-49'
              WHEN s.svc_year + e.birth_offset<55 THEN '50-54'
              WHEN s.svc_year + e.birth_offset<60 THEN '55-59'
              WHEN s.svc_year + e.birth_offset<65 THEN '60-64'
              WHEN s.svc_year + e.birth_offset<70 THEN '65-69'
              WHEN s.svc_year + e.birth_offset<75 THEN '70-74'
              WHEN s.svc_year + e.birth_offset<80 THEN '75-79'
              WHEN s.svc_year + e.birth_offset<85 THEN '80-84' ELSE '85-89' END AS age_publication,
         CASE WHEN list_contains(s.codes,'57288') AND list_contains(s.codes,'51715') THEN 'Hybrid'
              WHEN list_contains(s.codes,'57288') THEN 'Sling' ELSE 'Bulking' END AS procedure_category,
         CASE WHEN s.is_pop_surgery=1 THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context
  FROM surgery_dedup s INNER JOIN ever_eligible e USING (ENROLID)
  WHERE s.svc_year BETWEEN 2014 AND 2024
    AND s.svc_year + e.birth_offset BETWEEN 18 AND 89
    AND (list_contains(s.codes,'57288') OR list_contains(s.codes,'51715'))")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_first_period AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM p03_period_episodes
  ) WHERE rn=1")

make_burden <- function(window_days) {
  view_name <- sprintf("p03_burden_%03d", window_days)
  dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW %s AS
    WITH bulking_lag AS (
      SELECT *, LAG(svcdate) OVER (PARTITION BY ENROLID ORDER BY svcdate) AS prior_bulking_date
      FROM p03_period_episodes WHERE procedure_category='Bulking'
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
             ARG_MIN(age_publication, svcdate) AS age5,
             CASE WHEN MAX(CASE WHEN pop_context='Concomitant POP' THEN 1 ELSE 0 END)=1
                  THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context,
             'Bulking course' AS burden_category,
             COUNT(*) AS injections_in_course
      FROM bulking_numbered GROUP BY ENROLID, course_id
    ),
    nonbulking AS (
      SELECT ENROLID, svcdate, study_year, age_at_index, age_publication AS age5, pop_context,
             CASE WHEN procedure_category='Sling' THEN 'Sling episode' ELSE 'Hybrid episode' END AS burden_category,
             1 AS injections_in_course
      FROM p03_period_episodes WHERE procedure_category IN ('Sling', 'Hybrid')
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
  first_by_period_age_publication = "SELECT study_period,
      CASE WHEN age_at_index<30 THEN '18-29' ELSE age5 END AS age_publication,
      pop_context, procedure_category, COUNT(*) AS women
    FROM p03_first GROUP BY 1,2,3,4 ORDER BY 1,2,3,4",
  first_by_period = "SELECT study_period, pop_context, procedure_category, COUNT(*) AS women
                     FROM p03_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_by_database = "SELECT event_database, pop_context, procedure_category, COUNT(*) AS women
                       FROM p03_first GROUP BY 1,2,3 ORDER BY 1,2,3",
  first_totals = "SELECT pop_context, procedure_category, COUNT(*) AS women
                  FROM p03_first GROUP BY 1,2 ORDER BY 1,2",
  first_period_sensitivity = "SELECT
      CASE WHEN study_year<=2019 THEN '2014-2019' ELSE '2020-2024' END AS study_period,
      pop_context,procedure_category,COUNT(*) AS women
    FROM p03_first_period GROUP BY 1,2,3 ORDER BY 1,2,3"
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
stopifnot(denominator_total == 47258198)
stopifnot(dbGetQuery(con, "SELECT COUNT(*) AS n FROM p03_first")$n == 56257)
stopifnot(dbGetQuery(con, "SELECT COUNT(*) AS n FROM p03_burden_090
                           WHERE pop_context='Isolated SUI'
                             AND burden_category='Sling episode'")$n == 33845)
stopifnot(dbGetQuery(con, "SELECT COUNT(*) AS n FROM p03_burden_090
                           WHERE pop_context='Isolated SUI'
                             AND burden_category='Bulking course'")$n == 7476)
stopifnot(dbGetQuery(con, "SELECT COUNT(*) AS n FROM p03_burden_180
                           WHERE pop_context='Isolated SUI'
                             AND burden_category='Bulking course'")$n == 7135)

writeLines(c(
  sprintf("Run time UTC: %s", format(Sys.time(), tz = "UTC")),
  "P03 server-side aggregation completed.",
  "First qualifying procedure within an eligible woman-year was resolved globally across CCAE and MDCR.",
  "Annual attribution used service-date year; the source claim YEAR field was not used for the event join.",
  "Secondary burden courses used all observed 2014-2024 events among ever-eligible women.",
  "Locked Wu-style pooled person-year denominator check passed: 47,258,198.",
  "Primary bulking-course window: 90 days; sensitivity: 180 days.",
  "Review all cells for disclosure safety before transferring aggregate files."
), file.path(OUT, "P03_run_log.txt"))

cat("P03 aggregate analysis complete. Outputs remain on the Yale server.\n")

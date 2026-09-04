# Aggregate-only method audit for P01-P03.
#
# Run on the Yale MarketScan server. This script never writes person-level
# records. It checks the current derived-parquet schema, eligibility/event-year
# consistency, outcome-definition reconciliation, and the effect of resolving
# first procedures over all observed 2014-2024 events rather than only events
# occurring in eligible woman-years.

suppressPackageStartupMessages({
  library(duckdb)
  library(DBI)
})

ROOT <- "/data/MarketScan_data/cohort/analytic"
OUT <- path.expand("~/p01_p03_method_audit_2026-09-04")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)
dir.create(path.expand("~/duckdb_tmp"), showWarnings = FALSE, recursive = TRUE)

con <- dbConnect(duckdb(shared_home = FALSE))
on.exit(dbDisconnect(con, shutdown = TRUE), add = TRUE)
dbExecute(con, "SET memory_limit='4GB'")
dbExecute(con, "SET threads=2")
dbExecute(con, sprintf("SET temp_directory='%s'", path.expand("~/duckdb_tmp")))

sql_list <- function(x) paste(sprintf("'%s'", x), collapse = ", ")
has_any <- function(x, field = "codes") {
  paste(sprintf("list_contains(%s, '%s')", field, x), collapse = " OR ")
}

OBLITERATIVE <- c("57106", "57110", "57120", "58275", "58280")
RECONSTRUCTIVE <- c(
  "56810", "57107", "57109", "57111", "57112", "57200", "57210",
  "57230", "57240", "57250", "57260", "57265", "57267", "57268",
  "57270", "57280", "57282", "57283", "57284", "57285", "57423",
  "57425", "58400"
)
P02_CODES <- c(OBLITERATIVE, RECONSTRUCTIVE)
SUI_NO_BULKING <- c(
  "51840", "51841", "51845", "51990", "51992", "57220", "57288",
  "57289", "58152", "58267", "58293"
)

AGE5 <- paste(
  "CASE",
  "WHEN age_at_index BETWEEN 18 AND 24 THEN '18-24'",
  "WHEN age_at_index BETWEEN 25 AND 84 THEN",
  "  printf('%02d-%02d', CAST(5 * floor(age_at_index / 5) AS INTEGER),",
  "         CAST(5 * floor(age_at_index / 5) + 4 AS INTEGER))",
  "WHEN age_at_index BETWEEN 85 AND 89 THEN '85-89' END"
)

BROAD_AGE <- paste(
  "CASE WHEN age_at_index < 65 THEN '<65'",
  "WHEN age_at_index < 75 THEN '65-74'",
  "WHEN age_at_index < 85 THEN '75-84' ELSE '85-89' END"
)

fa <- function(db) sprintf("read_parquet('%s/%s_final_analysis.parquet')", ROOT, db)
ec <- function(db) sprintf("read_parquet('%s/%s_eligible_cohort.parquet')", ROOT, db)
se <- function(db) sprintf("read_parquet('%s/%s_surgery_events.parquet')", ROOT, db)

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW eligible_rows AS
  SELECT *, %s AS age5, %s AS broad_age FROM (
    SELECT 'CCAE' AS database, study_year, ENROLID, index_date, age_at_index,
           dobyr, enrmon_index_year, memdays_index_year, incident_sui,
           incident_pop, incident_pop_no_hyst, incident_pop_anydx
    FROM %s WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
    UNION ALL
    SELECT 'MDCR' AS database, study_year, ENROLID, index_date, age_at_index,
           dobyr, enrmon_index_year, memdays_index_year, incident_sui,
           incident_pop, incident_pop_no_hyst, incident_pop_anydx
    FROM %s WHERE study_year BETWEEN 2014 AND 2024 AND age_at_index BETWEEN 18 AND 89
  )", AGE5, BROAD_AGE, fa("CCAE"), fa("MDCR")))

dbExecute(con, "CREATE OR REPLACE TEMP VIEW eligible_keys AS
  SELECT ENROLID, study_year, MIN(index_date) AS index_date,
         MIN(age_at_index) AS age_at_index, MIN(dobyr) AS dobyr,
         MIN(age5) AS age5, MIN(broad_age) AS broad_age
  FROM eligible_rows GROUP BY ENROLID, study_year")

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW surgery_all AS
  SELECT 'CCAE' AS database, * FROM %s
  UNION ALL
  SELECT 'MDCR' AS database, * FROM %s", se("CCAE"), se("MDCR")))

dbExecute(con, "CREATE OR REPLACE TEMP VIEW surgery_dedup AS
  SELECT ENROLID, CAST(svcdate AS DATE) AS svcdate,
         YEAR(CAST(svcdate AS DATE)) AS svc_year,
         CASE WHEN COUNT(DISTINCT database)=1 THEN MIN(database) ELSE 'BOTH' END AS event_database,
         list_distinct(flatten(list(codes))) AS codes,
         MAX(sui_proc) AS sui_proc, MAX(pop_proc) AS pop_proc,
         MAX(hyst_benign_proc) AS hyst_benign_proc,
         MAX(hyst_oncobst_proc) AS hyst_oncobst_proc,
         MAX(pop_dx_primary) AS pop_dx_primary, MAX(pop_dx_any) AS pop_dx_any,
         MAX(is_sui_surgery) AS is_sui_surgery,
         MAX(is_pop_surgery) AS is_pop_surgery,
         MAX(is_pop_surgery_no_hyst) AS is_pop_surgery_no_hyst,
         MAX(is_pop_surgery_anydx) AS is_pop_surgery_anydx,
         MIN(CAST(YEAR AS INTEGER)) AS claim_year_min,
         MAX(CAST(YEAR AS INTEGER)) AS claim_year_max
  FROM surgery_all
  GROUP BY ENROLID, CAST(svcdate AS DATE)")

# Current data inventory and cohort-flow counts.
inventory <- do.call(rbind, lapply(c("CCAE", "MDCR"), function(db) {
  eligible <- dbGetQuery(con, sprintf("SELECT COUNT(*) AS rows,
      COUNT(DISTINCT ENROLID) AS women, MIN(study_year) AS min_year,
      MAX(study_year) AS max_year, MIN(age_at_index) AS min_age,
      MAX(age_at_index) AS max_age, MIN(enrmon_index_year) AS min_enrmon,
      MAX(enrmon_index_year) AS max_enrmon, MIN(lookback_years_enrolled) AS min_lookback,
      MAX(lookback_years_enrolled) AS max_lookback FROM %s", ec(db)))
  final <- dbGetQuery(con, sprintf("SELECT COUNT(*) AS rows,
      COUNT(DISTINCT ENROLID) AS women, MIN(study_year) AS min_year,
      MAX(study_year) AS max_year, MIN(age_at_index) AS min_age,
      MAX(age_at_index) AS max_age, MIN(enrmon_index_year) AS min_enrmon,
      MAX(enrmon_index_year) AS max_enrmon, NULL::INTEGER AS min_lookback,
      NULL::INTEGER AS max_lookback FROM %s", fa(db)))
  rbind(data.frame(database = db, layer = "eligible_cohort", eligible),
        data.frame(database = db, layer = "final_analysis", final))
}))
write.csv(inventory, file.path(OUT, "inventory_and_cohort_flow.csv"), row.names = FALSE)

year_check <- dbGetQuery(con, "SELECT
    COUNT(*) AS surgery_rows,
    SUM(CASE WHEN claim_year_min<>svc_year OR claim_year_max<>svc_year THEN 1 ELSE 0 END) AS dates_with_year_mismatch,
    COUNT(DISTINCT CASE WHEN claim_year_min<>svc_year OR claim_year_max<>svc_year THEN ENROLID END) AS women_with_year_mismatch,
    SUM(CASE WHEN (claim_year_min<>svc_year OR claim_year_max<>svc_year)
                   AND (is_sui_surgery=1 OR is_pop_surgery=1) THEN 1 ELSE 0 END) AS qualifying_dates_with_year_mismatch
  FROM surgery_dedup")
write.csv(year_check, file.path(OUT, "service_year_check.csv"), row.names = FALSE)

# Reconcile the parent POP day definition with P02's explicit-code definition.
dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW pop_reconciliation AS
  WITH joined AS (
    SELECT s.*, e.study_year, e.age_at_index, e.age5, e.broad_age,
           CASE WHEN %s THEN 1 ELSE 0 END AS p02_explicit,
           CASE WHEN %s THEN 1 ELSE 0 END AS has_obliterative,
           CASE WHEN %s THEN 1 ELSE 0 END AS has_reconstructive
    FROM surgery_dedup s
    INNER JOIN eligible_keys e ON s.ENROLID=e.ENROLID AND s.svc_year=e.study_year
  )
  SELECT *,
         CASE WHEN is_pop_surgery=1 AND p02_explicit=1 THEN 'Both definitions'
              WHEN is_pop_surgery=1 THEN 'P01 only'
              WHEN p02_explicit=1 THEN 'P02 only' ELSE 'Neither' END AS definition_group
  FROM joined WHERE is_pop_surgery=1 OR p02_explicit=1",
  has_any(P02_CODES), has_any(OBLITERATIVE), has_any(RECONSTRUCTIVE)))

pop_summary <- dbGetQuery(con, "SELECT definition_group,
    COUNT(*) AS operation_dates, COUNT(DISTINCT ENROLID) AS women
  FROM pop_reconciliation GROUP BY 1 ORDER BY 1")
write.csv(pop_summary, file.path(OUT, "p01_p02_pop_definition_reconciliation.csv"), row.names = FALSE)

pop_by_year <- dbGetQuery(con, "SELECT study_year, definition_group,
    COUNT(*) AS operation_dates, COUNT(DISTINCT ENROLID) AS women
  FROM pop_reconciliation GROUP BY 1,2 ORDER BY 1,2")
write.csv(pop_by_year, file.path(OUT, "p01_p02_pop_definition_by_year.csv"), row.names = FALSE)

# Primary P02 first eligible-year procedure and an augmented parent-definition sensitivity.
dbExecute(con, "CREATE OR REPLACE TEMP VIEW p02_first_current AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM pop_reconciliation WHERE p02_explicit=1
  ) WHERE rn=1")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p02_first_augmented AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM pop_reconciliation
  ) WHERE rn=1")

p02_sensitivity <- dbGetQuery(con, "WITH a AS (
    SELECT 'Current explicit-code definition' AS definition,
           COUNT(*) AS first_procedures,
           SUM(has_obliterative) AS obliterative
    FROM p02_first_current
    UNION ALL
    SELECT 'Augmented with parent hysterectomy channel', COUNT(*), SUM(has_obliterative)
    FROM p02_first_augmented
  ) SELECT *, 100.0*obliterative/first_procedures AS obliterative_share_percent FROM a")
write.csv(p02_sensitivity, file.path(OUT, "p02_parent_definition_sensitivity.csv"), row.names = FALSE)

p02_obl_composition <- dbGetQuery(con, sprintf("WITH expanded AS (
    SELECT f.age5, f.broad_age, f.pop_dx_primary, u.code
    FROM p02_first_current f, UNNEST(f.codes) AS u(code)
    WHERE f.has_obliterative=1 AND u.code IN (%s)
  ) SELECT broad_age, code, COUNT(*) AS operation_dates,
           SUM(pop_dx_primary) AS with_primary_pop_diagnosis
    FROM expanded GROUP BY 1,2 ORDER BY 1,2", sql_list(OBLITERATIVE)))
p02_obl_composition$operation_dates[p02_obl_composition$operation_dates < 11] <- NA
p02_obl_composition$with_primary_pop_diagnosis[
  p02_obl_composition$with_primary_pop_diagnosis < 11
] <- NA
write.csv(p02_obl_composition, file.path(OUT, "p02_obliterative_code_by_broad_age_screened.csv"),
          row.names = FALSE, na = "SUPPRESSED")

# Compare eligible-year first procedures with all observed 2014-2024 events among
# women who contributed at least one eligible woman-year.
dbExecute(con, "CREATE OR REPLACE TEMP VIEW ever_eligible AS
  SELECT ENROLID, MIN(dobyr) AS dobyr FROM eligible_keys GROUP BY ENROLID")

dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW p02_all_period_events AS
  SELECT s.*,
         YEAR(s.svcdate)-e.dobyr AS event_age,
         CASE WHEN %s THEN 1 ELSE 0 END AS p02_explicit,
         CASE WHEN %s THEN 1 ELSE 0 END AS has_obliterative
  FROM surgery_dedup s INNER JOIN ever_eligible e USING (ENROLID)
  WHERE s.svc_year BETWEEN 2014 AND 2024 AND (%s)",
  has_any(P02_CODES), has_any(OBLITERATIVE), has_any(P02_CODES)))

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p02_first_all_period AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM p02_all_period_events
  ) WHERE rn=1")

p02_estimand <- dbGetQuery(con, "WITH current AS (
    SELECT ENROLID, svcdate, has_obliterative FROM p02_first_current
  ), allperiod AS (
    SELECT ENROLID, svcdate, has_obliterative FROM p02_first_all_period
  ) SELECT
    (SELECT COUNT(*) FROM current) AS eligible_year_first_n,
    (SELECT COUNT(*) FROM allperiod) AS all_period_first_n,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL) AS common_women,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL AND c.svcdate<>a.svcdate) AS earlier_visible_date,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL AND c.has_obliterative<>a.has_obliterative) AS changed_group
  FROM current c FULL OUTER JOIN allperiod a USING (ENROLID)")
write.csv(p02_estimand, file.path(OUT, "p02_eligible_year_estimand_audit.csv"), row.names = FALSE)

# P03 first-procedure and burden audit over all observed 2014-2024 episodes.
dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_all_period_events AS
  SELECT s.*, YEAR(s.svcdate)-e.dobyr AS event_age,
         CASE WHEN list_contains(s.codes,'57288') THEN 1 ELSE 0 END AS has_sling,
         CASE WHEN list_contains(s.codes,'51715') THEN 1 ELSE 0 END AS has_bulking,
         CASE WHEN has_sling=1 AND has_bulking=1 THEN 'Hybrid'
              WHEN has_sling=1 THEN 'Sling' ELSE 'Bulking' END AS procedure_category,
         CASE WHEN s.is_pop_surgery=1 THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context
  FROM surgery_dedup s INNER JOIN ever_eligible e USING (ENROLID)
  WHERE s.svc_year BETWEEN 2014 AND 2024
    AND (list_contains(s.codes,'57288') OR list_contains(s.codes,'51715'))")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_eligible_year_events AS
  SELECT s.*, e.study_year, e.age_at_index,
         CASE WHEN list_contains(s.codes,'57288') THEN 1 ELSE 0 END AS has_sling,
         CASE WHEN list_contains(s.codes,'51715') THEN 1 ELSE 0 END AS has_bulking,
         CASE WHEN has_sling=1 AND has_bulking=1 THEN 'Hybrid'
              WHEN has_sling=1 THEN 'Sling' ELSE 'Bulking' END AS procedure_category,
         CASE WHEN s.is_pop_surgery=1 THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context
  FROM surgery_dedup s INNER JOIN eligible_keys e
    ON s.ENROLID=e.ENROLID AND s.svc_year=e.study_year
  WHERE list_contains(s.codes,'57288') OR list_contains(s.codes,'51715')")

dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_first_all_period AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM p03_all_period_events
  ) WHERE rn=1")
dbExecute(con, "CREATE OR REPLACE TEMP VIEW p03_first_eligible_year AS
  SELECT * EXCLUDE(rn) FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ENROLID ORDER BY svcdate) AS rn
    FROM p03_eligible_year_events
  ) WHERE rn=1")

p03_estimand <- dbGetQuery(con, "WITH c AS (
    SELECT ENROLID, svcdate, procedure_category, pop_context FROM p03_first_eligible_year
  ), a AS (
    SELECT ENROLID, svcdate, procedure_category, pop_context FROM p03_first_all_period
  ) SELECT
    (SELECT COUNT(*) FROM c) AS eligible_year_first_n,
    (SELECT COUNT(*) FROM a) AS all_period_first_n,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL) AS common_women,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL AND c.svcdate<>a.svcdate) AS earlier_visible_date,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL AND c.procedure_category<>a.procedure_category) AS changed_procedure,
    COUNT(*) FILTER (WHERE c.ENROLID IS NOT NULL AND a.ENROLID IS NOT NULL AND c.pop_context<>a.pop_context) AS changed_pop_context
  FROM c FULL OUTER JOIN a USING (ENROLID)")
write.csv(p03_estimand, file.path(OUT, "p03_eligible_year_estimand_audit.csv"), row.names = FALSE)

make_p03_all_period_burden <- function(window_days) {
  view_name <- sprintf("p03_all_period_burden_%03d", window_days)
  dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW %s AS
    WITH bulking_lag AS (
      SELECT *, LAG(svcdate) OVER (PARTITION BY ENROLID ORDER BY svcdate) AS prior_date
      FROM p03_all_period_events WHERE procedure_category='Bulking'
    ), marked AS (
      SELECT *, CASE WHEN prior_date IS NULL OR DATE_DIFF('day',prior_date,svcdate)>%d
                     THEN 1 ELSE 0 END AS new_course
      FROM bulking_lag
    ), numbered AS (
      SELECT *, SUM(new_course) OVER (PARTITION BY ENROLID ORDER BY svcdate
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS course_id
      FROM marked
    ), courses AS (
      SELECT ENROLID, MIN(svcdate) AS svcdate,
             CASE WHEN MAX(is_pop_surgery)=1 THEN 'Concomitant POP' ELSE 'Isolated SUI' END AS pop_context,
             'Bulking course' AS burden_category, COUNT(*) AS contributing_dates
      FROM numbered GROUP BY ENROLID,course_id
    ), other AS (
      SELECT ENROLID,svcdate,pop_context,
             CASE WHEN procedure_category='Sling' THEN 'Sling episode' ELSE 'Hybrid episode' END AS burden_category,
             1 AS contributing_dates
      FROM p03_all_period_events WHERE procedure_category IN ('Sling','Hybrid')
    ) SELECT * FROM courses UNION ALL SELECT * FROM other", view_name, window_days))
  view_name
}

for (window_days in c(90L, 180L)) {
  v <- make_p03_all_period_burden(window_days)
  out <- dbGetQuery(con, sprintf("SELECT pop_context, burden_category,
      COUNT(*) AS treatment_units, SUM(contributing_dates) AS contributing_dates
    FROM %s GROUP BY 1,2 ORDER BY 1,2", v))
  write.csv(out, file.path(OUT, sprintf("p03_all_period_burden_%03d.csv", window_days)), row.names = FALSE)
}

# Exact P01 no-bulking sensitivity on the active woman-year definition. Export
# only age-level aggregates after masking small count cells; the lifetime-risk
# result can be calculated on-server from the public mortality table.
dbExecute(con, sprintf("CREATE OR REPLACE TEMP VIEW p01_year_flags_no_bulk AS
  WITH event_flags AS (
    SELECT e.ENROLID, e.study_year,
           MAX(CASE WHEN %s THEN 1 ELSE 0 END) AS sui_no_bulking
    FROM eligible_keys e LEFT JOIN surgery_dedup s
      ON e.ENROLID=s.ENROLID AND e.study_year=s.svc_year
    GROUP BY e.ENROLID,e.study_year
  )
  SELECT e.*, f.sui_no_bulking,
         CASE WHEN f.sui_no_bulking=1 OR e.incident_pop=1 THEN 1 ELSE 0 END AS any_no_bulking
  FROM eligible_rows e INNER JOIN event_flags f USING (ENROLID,study_year)",
  has_any(SUI_NO_BULKING)))

p01_nobulk_band <- dbGetQuery(con, "SELECT
    CASE WHEN age_at_index<30 THEN '18-29' WHEN age_at_index<40 THEN '30-39'
         WHEN age_at_index<50 THEN '40-49' WHEN age_at_index<60 THEN '50-59'
         WHEN age_at_index<70 THEN '60-69' WHEN age_at_index<80 THEN '70-79'
         ELSE '80-89' END AS age_band,
    COUNT(*) AS person_years, SUM(sui_no_bulking) AS sui_no_bulking,
    SUM(any_no_bulking) AS any_no_bulking
  FROM p01_year_flags_no_bulk GROUP BY 1 ORDER BY 1")
write.csv(p01_nobulk_band, file.path(OUT, "p01_no_bulking_by_age_band.csv"), row.names = FALSE)

p01_nobulk_age <- dbGetQuery(con, "SELECT age_at_index AS age,
    COUNT(*) AS person_years, SUM(sui_no_bulking) AS sui_no_bulking,
    SUM(any_no_bulking) AS any_no_bulking
  FROM p01_year_flags_no_bulk GROUP BY 1 ORDER BY 1")

qx_path <- path.expand("~/nchs2019_female_qx.csv")
if (file.exists(qx_path)) {
  qx <- read.csv(qx_path)
  cumulative_risk <- function(events, person_years, mortality) {
    survival <- 1
    cumulative <- 0
    for (age in 18:79) {
      i <- match(age, p01_nobulk_age$age)
      j <- match(age, qx$age)
      p <- events[i] / person_years[i]
      lambda <- -log1p(-p)
      mu <- -log1p(-qx$qx[j])
      total <- lambda + mu
      cumulative <- cumulative + survival * lambda / total * (1 - exp(-total))
      survival <- survival * exp(-total)
    }
    cumulative
  }
  nobulk_summary <- data.frame(
    endpoint = c("SUI excluding 51715", "Either excluding 51715"),
    operation_person_years = c(sum(p01_nobulk_age$sui_no_bulking),
                               sum(p01_nobulk_age$any_no_bulking)),
    cumulative_risk_percent = 100 * c(
      cumulative_risk(p01_nobulk_age$sui_no_bulking, p01_nobulk_age$person_years, qx$qx),
      cumulative_risk(p01_nobulk_age$any_no_bulking, p01_nobulk_age$person_years, qx$qx)
    )
  )
  write.csv(nobulk_summary, file.path(OUT, "p01_no_bulking_lifetime_risk.csv"), row.names = FALSE)
}

writeLines(c(
  sprintf("Run UTC: %s", format(Sys.time(), tz = "UTC")),
  "Aggregate-only method audit completed.",
  "No person-level output was written.",
  "Review every output before transfer."
), file.path(OUT, "RUN_LOG.txt"))

cat("Aggregate-only P01-P03 method audit complete.\n")

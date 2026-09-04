# Build the minimum disclosure-screened aggregate inputs needed for the P02
# and P03 publication analyses. This script runs on the Yale server and reads
# only aggregate CSVs created by the server analysis scripts.

THRESHOLD <- 11L
P02_IN <- path.expand("~/p02_aggregate_out")
P03_IN <- path.expand("~/p03_aggregate_out")
P02_OUT <- path.expand("~/p02_transfer_safe")
P03_OUT <- path.expand("~/p03_transfer_safe")

dir.create(P02_OUT, showWarnings = FALSE, recursive = TRUE)
dir.create(P03_OUT, showWarnings = FALSE, recursive = TRUE)

read_pooled <- function(input_dir, stem) {
  read.csv(
    file.path(input_dir, sprintf("pooled_%s_server_aggregate.csv", stem)),
    check.names = FALSE, stringsAsFactors = FALSE
  )
}

# Exact zero is structural and is retained. Suppression flags are calculated
# from the original vector before either the count or a linked field is masked.
suppress_small <- function(x, count_cols, linked_cols = list()) {
  original <- x
  masks <- setNames(lapply(count_cols, function(count_col) {
    !is.na(original[[count_col]]) & original[[count_col]] > 0 &
      original[[count_col]] < THRESHOLD
  }), count_cols)
  for (source_col in names(linked_cols)) {
    for (linked_col in linked_cols[[source_col]]) {
      if (linked_col %in% names(masks)) {
        masks[[linked_col]] <- masks[[linked_col]] | masks[[source_col]]
      }
    }
  }
  for (count_col in count_cols) {
    flag <- masks[[count_col]]
    x[[paste0(count_col, "_suppressed")]] <- flag
    x[[count_col]][flag] <- NA
    linked <- linked_cols[[count_col]]
    if (!is.null(linked)) {
      for (linked_col in linked) x[[linked_col]][flag] <- NA
    }
  }
  x
}

write_safe <- function(x, path, count_cols, linked_cols = list()) {
  screened <- suppress_small(x, count_cols, linked_cols)
  write.csv(screened, path, row.names = FALSE, na = "SUPPRESSED")
}

# P02: publish one nonredundant age table. Ages 18-24 and 25-29 are combined
# on the server, so no protected cell can be recovered from an overall margin.
write_safe(read_pooled(P02_IN, "denominators")[c("study_year", "age5", "broad_age", "woman_years")],
           file.path(P02_OUT, "pooled_denominators.csv"), "woman_years")
write_safe(read_pooled(P02_IN, "totals"),
           file.path(P02_OUT, "pooled_totals.csv"),
           c("first_observed_women", "obliterative", "reconstructive", "mixed_code_dates"))
write_safe(read_pooled(P02_IN, "first_by_age_publication"),
           file.path(P02_OUT, "pooled_first_by_age_publication.csv"), "women")
write_safe(read_pooled(P02_IN, "first_by_year")[c("study_year", "procedure_group", "women")],
           file.path(P02_OUT, "pooled_first_by_year.csv"), "women")
write_safe(read_pooled(P02_IN, "first_by_year_broad_age")[c("study_year", "broad_age", "procedure_group", "women")],
           file.path(P02_OUT, "pooled_first_by_year_broad_age.csv"), "women")
write_safe(read_pooled(P02_IN, "total_burden_by_year")[c("study_year", "procedure_group", "operation_dates")],
           file.path(P02_OUT, "pooled_eligible_year_procedure_dates_by_year.csv"), "operation_dates")
write_safe(read_pooled(P02_IN, "code_contribution")[c("code", "operation_dates")],
           file.path(P02_OUT, "pooled_code_contribution.csv"), "operation_dates")
write_safe(read_pooled(P02_IN, "definition_reconciliation"),
           file.path(P02_OUT, "pooled_definition_reconciliation.csv"),
           c("operation_dates", "women"))
write_safe(read_pooled(P02_IN, "parent_definition_sensitivity"),
           file.path(P02_OUT, "pooled_parent_definition_sensitivity.csv"),
           c("first_procedures", "obliterative"))

# P03: hybrid totals are reportable overall but are omitted from the period,
# annual and age detail files, where redundant margins previously allowed
# small cells to be recovered. The age table is server-collapsed to 18-29.
write_safe(read_pooled(P03_IN, "denominators")[c("study_year", "age5", "woman_years")],
           file.path(P03_OUT, "pooled_denominators.csv"), "woman_years")
write_safe(read_pooled(P03_IN, "first_totals"),
           file.path(P03_OUT, "pooled_first_totals.csv"), "women")

p03_period <- subset(read_pooled(P03_IN, "first_by_period"), procedure_category != "Hybrid")
write_safe(p03_period, file.path(P03_OUT, "pooled_first_by_period.csv"), "women")

p03_year <- subset(
  read_pooled(P03_IN, "first_by_year"),
  pop_context == "Isolated SUI" & procedure_category != "Hybrid"
)
write_safe(p03_year, file.path(P03_OUT, "pooled_first_by_year.csv"), "women")

p03_age <- subset(
  read_pooled(P03_IN, "first_by_period_age_publication"),
  pop_context == "Isolated SUI" & procedure_category != "Hybrid"
)
write_safe(p03_age, file.path(P03_OUT, "pooled_first_by_period_age_publication.csv"), "women")

p03_sensitivity <- subset(
  read_pooled(P03_IN, "first_period_sensitivity"), procedure_category != "Hybrid"
)
write_safe(p03_sensitivity,
           file.path(P03_OUT, "pooled_first_period_sensitivity.csv"), "women")

for (window in c("090d", "180d")) {
  totals <- subset(
    read_pooled(P03_IN, sprintf("total_burden_%s_totals", window)),
    pop_context == "Isolated SUI" & burden_category != "Hybrid episode"
  )
  write_safe(
    totals,
    file.path(P03_OUT, sprintf("pooled_total_burden_%s_totals.csv", window)),
    c("treatment_units", "contributing_injection_dates"),
    linked_cols = list(treatment_units = "contributing_injection_dates")
  )

  annual <- subset(
    read_pooled(P03_IN, sprintf("total_burden_%s_by_year", window)),
    pop_context == "Isolated SUI" & burden_category != "Hybrid episode"
  )
  write_safe(
    annual,
    file.path(P03_OUT, sprintf("pooled_total_burden_%s_by_year.csv", window)),
    c("treatment_units", "contributing_injection_dates"),
    linked_cols = list(treatment_units = "contributing_injection_dates")
  )
}

manifest <- c(
  sprintf("Created UTC: %s", format(Sys.time(), tz = "UTC")),
  "Input: server-side aggregate CSVs only; no person-level records.",
  "Annual attribution uses service-date year.",
  "P02 publication age groups combine ages 18-29.",
  "P03 publication age groups combine ages 18-29 and detailed hybrid rows are omitted.",
  "Secondary P03 burden includes all observed 2014-2024 events among ever-eligible women and is not a woman-year rate.",
  sprintf("Primary suppression: every nonzero count below %d is written as SUPPRESSED; structural zero is retained.", THRESHOLD),
  "The transfer set excludes redundant margins that could reconstruct protected cells."
)
writeLines(manifest, file.path(P02_OUT, "TRANSFER_MANIFEST.txt"))
writeLines(manifest, file.path(P03_OUT, "TRANSFER_MANIFEST.txt"))

validate_transfer <- function(directory, expected_files, fully_reportable_files) {
  observed <- sort(basename(list.files(directory, full.names = TRUE)))
  observed <- setdiff(observed, "VALIDATION_REPORT.txt")
  stopifnot(identical(observed, sort(c(expected_files, "TRANSFER_MANIFEST.txt"))))
  checked_cells <- 0L
  suppressed_cells <- 0L
  for (filename in expected_files) {
    path <- file.path(directory, filename)
    x <- read.csv(path, check.names = FALSE, stringsAsFactors = FALSE,
                  na.strings = "SUPPRESSED")
    count_columns <- names(x)[grepl(
      "^(woman_years|women|first_observed_women|first_procedures|obliterative|reconstructive|mixed_code_dates|operation_dates|treatment_units|contributing_injection_dates)$",
      names(x)
    )]
    for (count_column in count_columns) {
      values <- x[[count_column]]
      checked_cells <- checked_cells + length(values)
      stopifnot(!any(!is.na(values) & values > 0 & values < THRESHOLD))
      flag_column <- paste0(count_column, "_suppressed")
      if (flag_column %in% names(x)) {
        flags <- x[[flag_column]]
        stopifnot(all(is.na(values) == flags))
        suppressed_cells <- suppressed_cells + sum(flags)
      }
    }
    if (filename %in% fully_reportable_files) stopifnot(!any(is.na(x)))
  }
  c(checked_cells = checked_cells, suppressed_cells = suppressed_cells)
}

p02_files <- c(
  "pooled_denominators.csv", "pooled_totals.csv",
  "pooled_first_by_age_publication.csv", "pooled_first_by_year.csv",
  "pooled_first_by_year_broad_age.csv",
  "pooled_eligible_year_procedure_dates_by_year.csv",
  "pooled_code_contribution.csv", "pooled_definition_reconciliation.csv",
  "pooled_parent_definition_sensitivity.csv"
)
p03_files <- c(
  "pooled_denominators.csv", "pooled_first_totals.csv",
  "pooled_first_by_period.csv", "pooled_first_by_year.csv",
  "pooled_first_by_period_age_publication.csv",
  "pooled_first_period_sensitivity.csv",
  "pooled_total_burden_090d_totals.csv",
  "pooled_total_burden_090d_by_year.csv",
  "pooled_total_burden_180d_totals.csv",
  "pooled_total_burden_180d_by_year.csv"
)

p02_validation <- validate_transfer(
  P02_OUT, p02_files,
  c("pooled_denominators.csv", "pooled_totals.csv",
    "pooled_first_by_age_publication.csv", "pooled_first_by_year.csv",
    "pooled_first_by_year_broad_age.csv",
    "pooled_eligible_year_procedure_dates_by_year.csv",
    "pooled_definition_reconciliation.csv",
    "pooled_parent_definition_sensitivity.csv")
)
p03_validation <- validate_transfer(P03_OUT, p03_files, p03_files)

validation_lines <- c(
  sprintf("Validated UTC: %s", format(Sys.time(), tz = "UTC")),
  sprintf("Threshold: nonzero counts below %d", THRESHOLD),
  sprintf("P02 count cells checked: %d; protected cells retained only in the nonredundant code table: %d.",
          p02_validation[["checked_cells"]], p02_validation[["suppressed_cells"]]),
  sprintf("P03 count cells checked: %d; protected cells in transfer: %d.",
          p03_validation[["checked_cells"]], p03_validation[["suppressed_cells"]]),
  "Every visible nonzero count is at least 11.",
  "Every suppression flag matches a masked value.",
  "Publication age, period, year, and margin tables are fully reportable after age collapse and field minimization.",
  "Human visual inspection is not asserted by this machine report."
)
writeLines(validation_lines, file.path(P02_OUT, "VALIDATION_REPORT.txt"))
writeLines(validation_lines, file.path(P03_OUT, "VALIDATION_REPORT.txt"))

cat("Lean disclosure-screened transfer files created and validated.\n")

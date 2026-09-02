# Create disclosure-screened transfer files from completed pooled server-side
# follow-up analyses. This script reads aggregate CSVs only.

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

suppress_small <- function(x, count_cols, linked_cols = list()) {
  for (count_col in count_cols) {
    flag <- !is.na(x[[count_col]]) & x[[count_col]] < THRESHOLD
    x[[paste0(count_col, "_suppressed")]] <- flag
    x[[count_col]][flag] <- NA
    linked <- linked_cols[[count_col]]
    if (!is.null(linked)) {
      for (linked_col in linked) x[[linked_col]][flag] <- NA
    }
  }
  x
}

write_safe <- function(x, path) {
  write.csv(x, path, row.names = FALSE, na = "SUPPRESSED")
}

p02_specs <- list(
  denominators = "woman_years",
  first_by_year_age = c("women", "mixed_code_dates"),
  first_by_year = c("women", "mixed_code_dates"),
  first_by_age = c("women", "mixed_code_dates"),
  first_by_year_broad_age = c("women", "mixed_code_dates"),
  first_by_broad_age = c("women", "mixed_code_dates"),
  first_by_database = c("women", "mixed_code_dates"),
  total_burden = c("operation_dates", "mixed_code_dates"),
  total_burden_by_year = c("operation_dates", "mixed_code_dates"),
  totals = c("first_observed_women", "obliterative", "reconstructive", "mixed_code_dates"),
  code_contribution = c("claim_rows", "operation_dates")
)

for (stem in names(p02_specs)) {
  safe <- suppress_small(read_pooled(P02_IN, stem), p02_specs[[stem]])
  write_safe(safe, file.path(P02_OUT, sprintf("pooled_%s.csv", stem)))
}

p03_specs <- list(
  denominators = "woman_years",
  first_by_year = "women",
  first_by_year_age = "women",
  first_by_period_age = "women",
  first_by_period = "women",
  first_by_database = "women",
  first_totals = "women"
)

for (stem in names(p03_specs)) {
  safe <- suppress_small(read_pooled(P03_IN, stem), p03_specs[[stem]])
  write_safe(safe, file.path(P03_OUT, sprintf("pooled_%s.csv", stem)))
}

for (window in c("090d", "180d")) {
  stem <- sprintf("total_burden_%s", window)
  safe <- suppress_small(
    read_pooled(P03_IN, stem),
    c("treatment_units", "contributing_injection_dates"),
    linked_cols = list(treatment_units = "contributing_injection_dates")
  )
  write_safe(safe, file.path(P03_OUT, sprintf("pooled_%s.csv", stem)))

  for (suffix in c("by_year", "totals")) {
    detailed_stem <- sprintf("total_burden_%s_%s", window, suffix)
    detailed <- suppress_small(
      read_pooled(P03_IN, detailed_stem),
      c("treatment_units", "contributing_injection_dates"),
      linked_cols = list(treatment_units = "contributing_injection_dates")
    )
    write_safe(detailed, file.path(P03_OUT, sprintf("pooled_%s.csv", detailed_stem)))
  }
}

manifest <- c(
  sprintf("Created UTC: %s", format(Sys.time(), tz = "UTC")),
  "Input: server-side aggregate CSVs only; no person-level records.",
  "First observed procedures were resolved globally across CCAE and MDCR.",
  sprintf("Suppression rule: all count cells below %d are written as SUPPRESSED.", THRESHOLD),
  "Do not reconstruct suppressed cells by subtraction."
)
writeLines(manifest, file.path(P02_OUT, "TRANSFER_MANIFEST.txt"))
writeLines(manifest, file.path(P03_OUT, "TRANSFER_MANIFEST.txt"))

cat("Disclosure-screened pooled transfer files created.\n")

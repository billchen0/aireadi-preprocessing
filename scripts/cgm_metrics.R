library(iglu)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) stop("Usage: Rscript scripts/cgm_metrics.R INPUT.csv OUTPUT.csv")
input_path <- args[1]
output_path <- args[2]
if (file.exists(output_path)) stop("Output exists")
cat("iglu version:", as.character(packageVersion("iglu")), "\n")

cgm_data <- read.csv(input_path, stringsAsFactors = FALSE, colClasses = c(id = "character"))
if (!all(c("id", "time", "gl") %in% names(cgm_data))) stop("Expected id,time,gl")
# Explicit UTC parsing of the Python ISO-8601 output; never infer host timezone.
cgm_data$time <- as.POSIXct(cgm_data$time, format = "%Y-%m-%d %H:%M:%S", tz = "UTC")
if (anyNA(cgm_data$time)) stop("Invalid timestamps")
cgm_data <- cgm_data[!is.na(cgm_data$gl), c("id", "time", "gl")]
if (nrow(cgm_data) == 0) stop("No usable CGM rows")

# Split by subject
cgm_split <- split(cgm_data, cgm_data$id)
n_subj <- length(cgm_split)

good_results <- list()
skipped_ids <- character()
skipped_info <- list()  # id -> error message

cat("Running iglu::all_metrics per subject...\n")
pb <- txtProgressBar(min = 0, max = n_subj, style = 3)

i <- 0
for (pid in names(cgm_split)) {
  i <- i + 1
  subj_df <- cgm_split[[pid]]

  res <- tryCatch(
    withCallingHandlers(
      all_metrics(subj_df),
      warning = function(w) {
        invokeRestart("muffleWarning")
        stop(conditionMessage(w))
      }
    ),
    error = function(e) e
  )

  if (inherits(res, "error")) {
    msg <- conditionMessage(res)
    skipped_ids <- c(skipped_ids, pid)
    skipped_info[[pid]] <- msg
  } else {
    # success
    if (!("id" %in% colnames(res))) res$id <- pid
    good_results[[pid]] <- res
  }

  setTxtProgressBar(pb, i)
}

close(pb)
cat("\nFinished per-subject processing.\n")

# Combine successful results
if (length(good_results) == 0) {
  stop("No subjects successfully processed by all_metrics().")
}

all_metrics_df <- do.call(rbind, good_results)

colnames(all_metrics_df)[colnames(all_metrics_df) == "id"] <- "person_id"

kept_ids <- unique(all_metrics_df$person_id)
cgm_kept <- cgm_data[cgm_data$id %in% kept_ids, ]

tir_70_140 <- in_range_percent(
  cgm_kept,
  target_ranges = list(c(70, 140))
)

colnames(tir_70_140)[colnames(tir_70_140) == "id"] <- "person_id"
all_metrics_df <- merge(all_metrics_df, tir_70_140, by = "person_id")

write.csv(all_metrics_df, output_path, row.names = FALSE)

# Report skipped subjects
cat("\n====================================\n")
cat("Skipped subjects (id : short message):\n")
if (length(skipped_ids) == 0) {
  cat("  None\n")
} else {
  for (id in sort(unique(skipped_ids))) {
    msg <- skipped_info[[id]]
    short_msg <- if (is.null(msg) || is.na(msg) || nchar(msg) == 0) "<no message>" else substr(msg, 1, 200)
    short_msg <- gsub("\n", " ", short_msg)
    cat(sprintf("  %s : %s\n", id, short_msg))
  }
}

cat("Total skipped:", length(unique(skipped_ids)), "\n")
cat("Total retained:", length(unique(all_metrics_df$person_id)), "\n")
cat("====================================\n")

writeLines(capture.output(sessionInfo()), paste0(output_path, ".session.txt"))

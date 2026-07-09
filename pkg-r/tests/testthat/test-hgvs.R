# HGVS is a grammar source: pattern mode checks variant syntax only. The full
# grammar is exercised by the shared conformance corpus; these are focused
# checks on representative shapes and on the pattern-only contract.

test_that("well-formed HGVS variants across types are valid", {
  ok <- c(
    "NM_004006.2:c.4375C>T",
    "NC_000023.11:g.32867861_32867862del",
    "NM_004006.2:c.88+1G>T",
    "NM_004006.2:c.76_77insACGT",
    "NM_004006.2:c.112_117delinsTG",
    "NP_003997.1:p.(Gly56Ala)",
    "NP_003997.1:p.Trp26Ter",
    "NP_003997.1:p.Arg97ProfsTer23"
  )
  expect_true(all(is_valid_id(ok, "hgvs")))
})

test_that("malformed HGVS variants are invalid", {
  bad <- c(
    "c.4375C>T", # no reference sequence
    "NM_004006.2:c.4375C>", # missing alternate base
    "NM_004006.2:x.123A>T", # unknown coordinate type
    "NM_004006.2:c.76insG", # insertion needs a range
    "NM_004006.2:p.Gly56Xyz" # unknown amino acid code
  )
  expect_false(any(is_valid_id(bad, "hgvs")))
})

test_that("hgvs is pattern-only: remote mode has no resolver", {
  expect_error(
    check_id("NM_004006.2:c.4375C>T", "hgvs", how = "remote"),
    class = "biogate_error_no_resolver"
  )
})

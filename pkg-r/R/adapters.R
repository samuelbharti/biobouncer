# Adapters wrap the core classifier for other validation frameworks. They never
# duplicate validation logic; each one calls is_valid_id().

#' Check that identifiers are valid
#'
#' A checkmate-style check function. Returns `TRUE` when every element of `x` is
#' a valid identifier for `source_db`, otherwise a message describing the
#' failure. Pairs with [assert_valid_id()] and [test_valid_id()].
#'
#' @inheritParams check_id
#' @return `TRUE` if all elements are valid, otherwise a message string.
#' @seealso [assert_valid_id()], [test_valid_id()], [is_valid_id()].
#' @examples
#' check_valid_id(c("MONDO:0005148", "MONDO:0018076"), "mondo")
#' check_valid_id("mondo:5148", "mondo")
#' @export
check_valid_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL
) {
  valid <- is_valid_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version
  )
  ok <- vapply(valid, isTRUE, logical(1))
  if (all(ok)) {
    return(TRUE)
  }
  bad <- which(!ok)
  sprintf(
    "Must be valid %s identifiers (%s mode), but %i of %i failed, for example '%s'",
    source_db,
    how,
    length(bad),
    length(x),
    as.character(x)[bad[1]]
  )
}

#' Assert that identifiers are valid
#'
#' A checkmate-style assertion. Throws an error when any element of `x` is not a
#' valid identifier for `source_db`, otherwise returns `x` invisibly.
#'
#' @inheritParams check_id
#' @param .var.name Name for `x` to use in error messages.
#' @param add A checkmate `AssertCollection` to push messages onto, or `NULL`.
#' @return `x` invisibly on success.
#' @seealso [check_valid_id()], [test_valid_id()].
#' @examples
#' assert_valid_id(c("MONDO:0005148", "MONDO:0018076"), "mondo")
#' @export
assert_valid_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL,
  .var.name = checkmate::vname(x),
  add = NULL
) {
  res <- check_valid_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version
  )
  checkmate::makeAssertion(x, res, .var.name, add)
}

#' Test whether identifiers are valid
#'
#' A checkmate-style test. Returns a single `TRUE` when every element of `x` is
#' valid for `source_db`, otherwise `FALSE`.
#'
#' @inheritParams check_id
#' @return A single logical.
#' @seealso [check_valid_id()], [assert_valid_id()].
#' @examples
#' test_valid_id(c("MONDO:0005148", "MONDO:0018076"), "mondo")
#' test_valid_id("mondo:5148", "mondo")
#' @export
test_valid_id <- function(
  x,
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL
) {
  isTRUE(check_valid_id(
    x,
    source_db = source_db,
    how = how,
    species = species,
    version = version
  ))
}

#' Create a shinyvalidate rule
#'
#' Returns a rule function for use with `shinyvalidate::InputValidator`'s
#' `add_rule()`. The rule returns `NULL` for a valid input and a message
#' otherwise. This adapter does not depend on shinyvalidate; it only produces a
#' rule the package can consume.
#'
#' @inheritParams check_id
#' @param message Optional custom message for an invalid input.
#' @return A function of one argument suitable for `add_rule()`.
#' @seealso [check_valid_id()].
#' @examples
#' rule <- sv_biogate("mondo")
#' rule("MONDO:0005148")
#' rule("mondo:5148")
#' @export
sv_biogate <- function(
  source_db,
  how = "pattern",
  species = NULL,
  version = NULL,
  message = NULL
) {
  force(source_db)
  force(how)
  force(species)
  force(version)
  force(message)
  function(value) {
    ok <- isTRUE(is_valid_id(
      value,
      source_db = source_db,
      how = how,
      species = species,
      version = version
    ))
    if (ok) {
      return(NULL)
    }
    if (!is.null(message)) {
      message
    } else {
      sprintf("Not a valid %s identifier", source_db)
    }
  }
}

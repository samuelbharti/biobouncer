// Error classes mirroring the Python exception hierarchy and the R condition
// classes. Each carries a stable `code` so tests and callers can branch on the
// kind of failure without matching message text.

export class BiobouncerError extends Error {
  readonly code: string;
  constructor(message: string, code: string) {
    super(message);
    this.name = "BiobouncerError";
    this.code = code;
  }
}

export class InvalidModeError extends BiobouncerError {
  constructor(message: string) {
    super(message, "invalid_mode");
    this.name = "InvalidModeError";
  }
}

export class InvalidOnError extends BiobouncerError {
  constructor(message: string) {
    super(message, "invalid_on_error");
    this.name = "InvalidOnError";
  }
}

export class UnknownSourceError extends BiobouncerError {
  constructor(message: string) {
    super(message, "unknown_source");
    this.name = "UnknownSourceError";
  }
}

export class MissingVersionError extends BiobouncerError {
  constructor(message: string) {
    super(message, "missing_version");
    this.name = "MissingVersionError";
  }
}

export class InvalidVersionError extends BiobouncerError {
  constructor(message: string) {
    super(message, "invalid_version");
    this.name = "InvalidVersionError";
  }
}

export class MissingSnapshotError extends BiobouncerError {
  constructor(message: string) {
    super(message, "missing_snapshot");
    this.name = "MissingSnapshotError";
  }
}

export class NoBuilderError extends BiobouncerError {
  constructor(message: string) {
    super(message, "no_builder");
    this.name = "NoBuilderError";
  }
}

export class NoResolverError extends BiobouncerError {
  constructor(message: string) {
    super(message, "no_resolver");
    this.name = "NoResolverError";
  }
}

export class RemoteError extends BiobouncerError {
  constructor(message: string) {
    super(message, "remote");
    this.name = "RemoteError";
  }
}

export class MissingDependencyError extends BiobouncerError {
  constructor(message: string) {
    super(message, "missing_dependency");
    this.name = "MissingDependencyError";
  }
}

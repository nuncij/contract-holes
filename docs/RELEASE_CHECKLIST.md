# Release checklist contract

Every release has a versioned record under `release/`. The signer attests that
each checked item is true for the exact checklist bytes and source revision.

Required sections are:

- identity: version, date, branch, commit/tag convention, and signing method;
- quality: full tests, evaluation, compatibility, proofs, docs, and diff checks;
- security: private-report review, threat-model review, dependency/toolchain pins;
- artifacts: clean export, two byte-identical builds, archive inspection, smoke
  install, hashes, and release manifest;
- publication: immutable upload, signature verification, post-install smoke, and
  rollback/advisory owner;
- explicit exceptions, each with risk, mitigation, owner, and expiry;
- maintainer attestation and detached signature filename.

A Markdown checkbox is evidence only when its command/result is reproducible or
linked. The checklist is not signed by typing a name into it: it requires a
detached cryptographic signature and a signed source tag as described in
[releasing](RELEASING.md).

Release records and signatures are immutable. Correct a mistake with a new
version and preserve the earlier advisory/artifacts for audit history.

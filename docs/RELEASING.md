# Releasing

Release artifacts are a pure-Python wheel and source distribution. The standard
PyPA flow builds both archives from `pyproject.toml`; this repository adds a clean
Git export, fixed build environment, `SOURCE_DATE_EPOCH`, normalized sdist
ownership/timestamps/gzip metadata, independent double build, archive inspection,
wheel installation/smoke scan, and SHA-256 manifest.

The official Python Packaging User Guide describes the
[packaging flow](https://packaging.python.org/en/latest/flow/), and PyPA `build`
is the [standard build frontend](https://packaging.python.org/en/latest/guides/tool-recommendations/).

## 1. Prepare

Start from a clean `main` checkout. Review the changelog, security policy,
compatibility ranges, task tracker, and version in both `pyproject.toml` and
`contract_holes.__version__`.

Create an isolated release environment and install the exact build set:

```bash
python3 -m venv .venv-release
.venv-release/bin/python -m pip install -r requirements/release.txt
```

The package build backend is also exactly pinned in `pyproject.toml`. Runtime
dependencies remain empty.

## 2. Validate the release tree

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
PYTHONPATH=src python3 -m contract_holes evaluate \
  tests/fixtures/evaluation/manifest.json
PYTHONPATH=src python3 -m contract_holes compatibility
git diff --check
git status --short
```

Run relevant generated proof bundles and the compatibility workflow on supported
CI runners. Review `SECURITY.md` for unresolved private reports. Do not release
with skipped compiler coverage unless the exception is written into the release
record and accepted by the signer.

## 3. Commit and sign the checklist

Complete the versioned record in
[`release/1.0.0-checklist.md`](../release/1.0.0-checklist.md). The maintainer signs
that exact file with a documented long-lived key:

```bash
gpg --armor --detach-sign \
  --output release/1.0.0-checklist.md.asc \
  release/1.0.0-checklist.md
gpg --verify release/1.0.0-checklist.md.asc release/1.0.0-checklist.md
git add release/1.0.0-checklist.md release/1.0.0-checklist.md.asc
git commit -m "Sign the 1.0.0 release checklist"
```

Do not generate an ad-hoc signing identity during release. Publish the signer's
fingerprint through a channel users already trust.

## 4. Build and reproduce

The build tool refuses a dirty repository or non-empty output directory. It
exports `HEAD` twice, builds both copies independently, and compares wheel/sdist
SHA-256 digests before copying artifacts:

```bash
.venv-release/bin/python scripts/release.py --output dist
(cd dist && sha256sum -c SHA256SUMS)
```

`dist/release-manifest.json` records the commit, source timestamp, exact build
tools, artifact sizes/digests, byte-for-byte comparison, and wheel smoke result.
`SHA256SUMS` covers both distributions and that manifest. The generated `dist/`
directory is intentionally ignored by Git and should be attached unchanged to
the release.

To reproduce, check out the recorded commit, install the same
`requirements/release.txt`, rerun the command in an empty output directory, and
compare the two distribution hashes. Environment metadata may differ, so the
generated release manifest itself is not expected to be identical across hosts.

## 5. Sign and verify release identity

Create a signed tag over the commit containing the signed checklist:

```bash
git tag -s v1.0.0 -m "Contract Holes 1.0.0"
git tag -v v1.0.0
gpg --armor --detach-sign --output dist/SHA256SUMS.asc dist/SHA256SUMS
gpg --verify dist/SHA256SUMS.asc dist/SHA256SUMS
```

The signed tag authenticates source and checklist; the detached checksum
signature authenticates generated artifacts and their release manifest. Record
the tag object ID, signing fingerprint, and final artifact hashes in release
notes or the hosting service's attestation.

## 6. Publish without mutation

Upload the `.whl`, `.tar.gz`, `release-manifest.json`, `SHA256SUMS`, and its
signature as built. Publishing to a package index is an external maintainer action
and must use that service's trusted-publishing/token policy. Never rebuild or edit
an artifact after signing; issue a new version if contents change.

After publication, install the exact wheel in a fresh environment, run
`holes --version`, `holes rules SOL001`, and a source-only smoke scan. Verify the
hosted hashes/signatures, then announce the compatibility and security links.

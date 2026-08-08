import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from contract_holes.address_source import (
    AddressSourceError,
    VerifiedSource,
    fetch_verified_source,
    write_verified_source,
)
from contract_holes.cli import main


ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"


class FakeResponse:
    def __init__(self, payload: object):
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _maximum: int) -> bytes:
        return self.body


def api_payload(source_code: str, **overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "SourceCode": source_code,
        "ContractName": "Vault",
        "ContractFileName": "contracts/Vault.sol",
        "CompilerType": "solc",
        "CompilerVersion": "v0.8.25+commit.fake",
        "OptimizationUsed": "1",
        "Runs": "200",
        "EVMVersion": "paris",
        "LicenseType": "MIT",
        "Proxy": "1",
        "Implementation": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
    }
    result.update(overrides)
    return {"status": "1", "message": "OK", "result": [result]}


class AddressSourceTests(unittest.TestCase):
    def test_fetches_multifile_standard_json_and_writes_hashed_provenance(self) -> None:
        standard_input = {
            "language": "Solidity",
            "sources": {
                "contracts/Vault.sol": {"content": "contract Vault {}"},
                "contracts/Token.sol": {"content": "contract Token {}"},
            },
            "settings": {"optimizer": {"enabled": True}},
        }
        wrapped = "{" + json.dumps(standard_input) + "}"
        calls: list[tuple[str, float]] = []

        def opener(url: str, *, timeout: float):
            calls.append((url, timeout))
            return FakeResponse(api_payload(wrapped))

        verified = fetch_verified_source(
            "8453",
            ADDRESS.upper().replace("0X", "0x"),
            "secret-api-key",
            timeout_seconds=4.5,
            opener=opener,
            now=lambda: datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc),
        )

        query = parse_qs(urlsplit(calls[0][0]).query)
        self.assertEqual(calls[0][1], 4.5)
        self.assertEqual(query["chainid"], ["8453"])
        self.assertEqual(query["module"], ["contract"])
        self.assertEqual(query["action"], ["getsourcecode"])
        self.assertEqual(query["address"], [ADDRESS])
        self.assertEqual(query["apikey"], ["secret-api-key"])
        self.assertEqual(
            [name for name, _ in verified.sources],
            ["contracts/Token.sol", "contracts/Vault.sol"],
        )

        with TemporaryDirectory() as directory:
            output = Path(directory) / "verified"
            provenance = write_verified_source(verified, output)

            self.assertEqual(
                (output / "contracts/Vault.sol").read_text(encoding="utf-8"),
                "contract Vault {}",
            )
            self.assertEqual(
                json.loads((output / "compiler-input.json").read_text(encoding="utf-8")),
                standard_input,
            )
            self.assertEqual(provenance["schema_version"], "1.0")
            self.assertEqual(provenance["chain_id"], "8453")
            self.assertEqual(provenance["address"], ADDRESS)
            self.assertEqual(provenance["retrieved_at"], "2026-08-08T12:00:00Z")
            self.assertEqual(provenance["contract"]["proxy"], "1")
            self.assertEqual(len(provenance["source_set_sha256"]), 64)
            self.assertEqual(provenance["compiler_input"]["path"], "compiler-input.json")
            rendered = (output / "provenance.json").read_text(encoding="utf-8")
            self.assertNotIn("secret-api-key", rendered)
            self.assertEqual(json.loads(rendered), provenance)

    def test_single_file_uses_contract_filename(self) -> None:
        verified = fetch_verified_source(
            1,
            ADDRESS,
            "key",
            opener=lambda *_args, **_kwargs: FakeResponse(
                api_payload("pragma solidity ^0.8.0; contract Vault {}")
            ),
        )

        self.assertEqual(
            verified.sources,
            (("contracts/Vault.sol", "pragma solidity ^0.8.0; contract Vault {}"),),
        )

    def test_rejects_invalid_identity_api_failures_and_unsafe_paths(self) -> None:
        with self.assertRaisesRegex(AddressSourceError, "chain ID"):
            fetch_verified_source("01", ADDRESS, "key")
        with self.assertRaisesRegex(AddressSourceError, "address"):
            fetch_verified_source(1, "0x1234", "key")
        with self.assertRaisesRegex(AddressSourceError, "rejected"):
            fetch_verified_source(
                1,
                ADDRESS,
                "key",
                opener=lambda *_args, **_kwargs: FakeResponse(
                    {"status": "0", "message": "NOTOK", "result": "not verified"}
                ),
            )
        malicious = {
            "language": "Solidity",
            "sources": {"../Escape.sol": {"content": "contract Escape {}"}},
        }
        with self.assertRaisesRegex(AddressSourceError, "unsafe"):
            fetch_verified_source(
                1,
                ADDRESS,
                "key",
                opener=lambda *_args, **_kwargs: FakeResponse(
                    api_payload(json.dumps(malicious))
                ),
            )

    def test_writer_refuses_existing_output_and_revalidates_paths(self) -> None:
        verified = VerifiedSource(
            chain_id="1",
            address=ADDRESS,
            sources=(("Vault.sol", "contract Vault {}"),),
            metadata={},
            retrieved_at="2026-08-08T12:00:00Z",
        )
        with TemporaryDirectory() as directory:
            output = Path(directory) / "verified"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(AddressSourceError, "refusing to overwrite"):
                write_verified_source(verified, output)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

            unsafe = VerifiedSource(
                chain_id="1",
                address=ADDRESS,
                sources=(("../Escape.sol", "contract Escape {}"),),
                metadata={},
                retrieved_at="2026-08-08T12:00:00Z",
            )
            with self.assertRaisesRegex(AddressSourceError, "unsafe"):
                write_verified_source(unsafe, Path(directory) / "new")

    def test_fetch_cli_uses_named_environment_variable_and_emits_provenance(self) -> None:
        payload = {
            "schema_version": "1.0",
            "chain_id": "1",
            "address": ADDRESS,
        }
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"TEST_EXPLORER_KEY": "key"}, clear=True),
            patch(
                "contract_holes.cli.fetch_and_write_verified_source",
                return_value=payload,
            ) as fetch,
            contextlib.redirect_stdout(output),
        ):
            status = main(
                [
                    "fetch",
                    "1",
                    ADDRESS,
                    "--output",
                    "verified",
                    "--api-key-env",
                    "TEST_EXPLORER_KEY",
                    "--timeout",
                    "12.5",
                ]
            )

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue()), payload)
        fetch.assert_called_once_with(
            "1", ADDRESS, "key", "verified", timeout_seconds=12.5
        )


if __name__ == "__main__":
    unittest.main()

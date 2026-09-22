from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(slots=True)
class CliArgs:
    document: str | None
    signature: str | None


def parse_args(argv: list[str] | None = None) -> CliArgs:
    """Parse Signer command-line arguments (document/signature paths to preload)."""
    parser = argparse.ArgumentParser(description="Signer - place signature over PDF and export JPG")
    parser.add_argument("-document", dest="document", default=None, help="Path to input PDF document")
    parser.add_argument("-signature", dest="signature", default=None, help="Path to signature image")
    ns = parser.parse_args(argv)
    return CliArgs(document=ns.document, signature=ns.signature)

"""Simple command-line runner for SheerID verification (no Docker required)."""
import argparse
import json
import logging
from typing import Optional

from sheerid_verifier import SheerIDVerifier, SCHOOLS, DEFAULT_SCHOOL_ID

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def _prompt_verification_id(initial_url: Optional[str] = None) -> str:
    """Ask user for verification link or ID and normalize to an ID."""
    if initial_url:
        parsed = SheerIDVerifier.parse_verification_id(initial_url)
        if parsed:
            return parsed
        logger.warning("Tidak bisa mengambil verificationId dari URL, minta input manual")

    user_input = input("Tempel verification link atau ID langsung: ").strip()
    parsed = SheerIDVerifier.parse_verification_id(user_input)
    return parsed or user_input


def _prompt_school(default_school: str) -> str:
    """Ask user to pick a school ID (shows list)."""
    print("\nSekolah tersedia:")
    for key, school in SCHOOLS.items():
        city = school.get("city")
        state = school.get("state")
        location = f" ({city}, {state})" if city and state else ""
        print(f" - {key}: {school['name']}{location} | {school['type']}")

    choice = input(f"\nPilih school ID (default {default_school}): ").strip()
    return choice or default_school


def run_from_cli(url: Optional[str], verification_id: Optional[str], school_id: Optional[str]) -> None:
    """Execute verification with interactive fallbacks."""
    if not verification_id:
        verification_id = _prompt_verification_id(url)

    if not school_id:
        school_id = _prompt_school(DEFAULT_SCHOOL_ID)

    if school_id not in SCHOOLS:
        raise SystemExit(f"School ID {school_id} tidak ditemukan di config")

    verifier = SheerIDVerifier(verification_id)
    result = verifier.verify(school_id=school_id)
    print("\nHasil verifikasi:")
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SheerID verification via command prompt")
    parser.add_argument("--url", help="Tempel URL SheerID (akan diekstrak otomatis)")
    parser.add_argument("--verification-id", dest="verification_id", help="ID verifikasi langsung")
    parser.add_argument("--school-id", dest="school_id", help="ID sekolah (lihat daftar di config.py)")
    args = parser.parse_args()

    run_from_cli(args.url, args.verification_id, args.school_id)


if __name__ == "__main__":
    main()

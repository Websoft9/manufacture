"""Validate all authored product drafts without AWS credentials or network calls."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cli.offer import DATA, render  # noqa: E402


def main() -> int:
    paths = sorted((DATA / "products").glob("*.json"))
    failures = 0
    for path in paths:
        try:
            value = render(path)
            if path.stem != value["key"]:
                raise ValueError("filename does not match product key")
            print(f"{path.name}: valid draft, {len(value['publishBlockers'])} publication blockers")
        except Exception as error:
            failures += 1
            print(f"{path.name}: {error}", file=sys.stderr)
    if not paths:
        print("No product master records found", file=sys.stderr)
        return 1
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())

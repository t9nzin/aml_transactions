"""Download one variant of the IBM AML dataset from Kaggle into data/raw/.

Needs Kaggle API credentials (~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY).

    uv run python scripts/download_data.py --variant HI-Small
"""

import argparse
import subprocess
import zipfile
from pathlib import Path

DATASET = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"
VARIANTS = ["HI-Small", "HI-Medium", "HI-Large", "LI-Small", "LI-Medium", "LI-Large"]
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def download_file(name: str, dest: Path) -> Path:
    target = dest / name
    if target.exists():
        print(f"{target} already exists, skipping")
        return target
    subprocess.run(
        ["kaggle", "datasets", "download", "-d", DATASET, "-f", name, "-p", str(dest)],
        check=True,
    )
    # Kaggle zips larger files; unzip in place if so.
    zipped = dest / f"{name}.zip"
    if zipped.exists():
        with zipfile.ZipFile(zipped) as zf:
            zf.extractall(dest)
        zipped.unlink()
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, default="HI-Small")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("_Trans.csv", "_Patterns.txt"):
        print(download_file(f"{args.variant}{suffix}", RAW_DIR))


if __name__ == "__main__":
    main()

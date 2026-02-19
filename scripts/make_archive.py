import argparse
from pathlib import Path
import zipfile


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True, help="output folder (contains pages/ and index.txt)")
    args = p.parse_args()

    out_dir: Path = args.out
    pages_dir = out_dir / "pages"
    index_path = out_dir / "index.txt"
    zip_path = out_dir / "pages.zip"

    if not pages_dir.exists():
        raise SystemExit(f"pages dir not found: {pages_dir}")
    if not index_path.exists():
        raise SystemExit(f"index.txt not found: {index_path}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pages_dir.glob("*.html")):
            z.write(f, arcname=f"pages/{f.name}")
        z.write(index_path, arcname="index.txt")

    print(f"[ok] created: {zip_path}")


if __name__ == "__main__":
    main()

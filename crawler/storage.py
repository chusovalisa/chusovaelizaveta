from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class RunStats:
    requested: int = 0
    saved: int = 0
    skipped: int = 0
    failed: int = 0


class Storage:
    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.pages_dir = out_dir / "pages"
        self.index_path = out_dir / "index.txt"
        self.errors_path = out_dir / "errors.log"
        self.summary_path = out_dir / "summary.json"

        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.index_path.write_text("", encoding="utf-8")
        self.errors_path.write_text("", encoding="utf-8")

        self.stats = RunStats()

    def save_page(self, num: int, url: str, html: str) -> Path:
        fname = f"{num:06d}.html"
        fpath = self.pages_dir / fname
        fpath.write_text(html, encoding="utf-8", errors="ignore")

        with self.index_path.open("a", encoding="utf-8") as f:
            f.write(f"{num:06d}\t{url}\n")

        self.stats.saved += 1
        return fpath

    def log_skip(self, url: str, reason: str):
        with self.errors_path.open("a", encoding="utf-8") as f:
            f.write(f"SKIP\t{reason}\t{url}\n")
        self.stats.skipped += 1

    def log_fail(self, url: str, reason: str):
        with self.errors_path.open("a", encoding="utf-8") as f:
            f.write(f"FAIL\t{reason}\t{url}\n")
        self.stats.failed += 1

    def finalize(self):
        self.summary_path.write_text(
            json.dumps(self.stats.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

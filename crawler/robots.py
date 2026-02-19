from dataclasses import dataclass
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import time
import requests


@dataclass
class RobotsCache:
    user_agent: str
    timeout: float = 10.0
    cache_ttl_sec: int = 60 * 60

    def __post_init__(self):
        self._cache: dict[str, tuple[float, RobotFileParser]] = {}

    def allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        now = time.time()

        if base in self._cache:
            ts, rp = self._cache[base]
            if now - ts < self.cache_ttl_sec:
                return rp.can_fetch(self.user_agent, url)

        rp = RobotFileParser()
        robots_url = urljoin(base, "/robots.txt")
        try:
            r = requests.get(robots_url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
            rp.parse(r.text.splitlines())
        except Exception:
            rp.parse([])

        self._cache[base] = (now, rp)
        return rp.can_fetch(self.user_agent, url)

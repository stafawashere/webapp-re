import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_SITE_ROOT = PACKAGE_DIR.parents[2]
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
CATALOGUE_MAX_AGE_SECONDS = 7 * 24 * 3600
REGION_CONFIG_MAX_AGE_SECONDS = 7 * 24 * 3600
STOP_CACHE_MAX_AGE_SECONDS = 7 * 24 * 3600
PLACE_CACHE_MAX_AGE_SECONDS = 30 * 24 * 3600
BRAND_DIRECTORY_MAX_AGE_SECONDS = 7 * 24 * 3600
ROUTE_STATUS_MAX_AGE_SECONDS = 60


@dataclass(frozen=True)
class Paths:
   site_root: Path

   @property
   def env_file(self):
      return self.site_root / ".env"

   @property
   def cache_dir(self):
      return self.site_root / "var" / "cache"

   @property
   def state_dir(self):
      return self.site_root / "var" / "state"

   @property
   def logs_dir(self):
      return self.site_root / "var" / "logs"

   @property
   def pacer_state(self):
      return self.state_dir / "pacer.json"

   @property
   def readiness_file(self):
      return self.state_dir / "readiness.json"


def site_paths():
   configured_root = os.environ.get("CITYMAPPER_ROOT")
   site_root = Path(configured_root).expanduser() if configured_root else DEFAULT_SITE_ROOT
   return Paths(site_root=site_root)

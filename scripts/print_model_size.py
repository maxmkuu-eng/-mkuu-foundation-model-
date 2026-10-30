import argparse
import sys
from pathlib import Path

import yaml

# Allow this file to run directly from any working directory.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model import ModelConfig, MKUUTransformer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/model_300m.yaml")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path

    with config_path.open(encoding="utf-8") as handle:
        config = ModelConfig.from_dict(yaml.safe_load(handle))

    model = MKUUTransformer(config)
    count = model.parameter_count()
    print(f"Parameters: {count:,} ({count / 1e6:.2f}M)")
    print("Check this measured count against the ~300M target before training.")


if __name__ == "__main__":
    main()

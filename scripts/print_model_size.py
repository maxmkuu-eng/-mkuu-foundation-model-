import argparse
import yaml
from model import ModelConfig, MKUUTransformer

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="configs/model_300m.yaml")
    a=p.parse_args()
    with open(a.config,encoding="utf-8") as f:
        cfg=ModelConfig.from_dict(yaml.safe_load(f))
    model=MKUUTransformer(cfg)
    n=model.parameter_count()
    print(f"Parameters: {n:,} ({n/1e6:.2f}M)")
    print("Check this measured count against the ~300M target before training.")

if __name__=="__main__":
    main()

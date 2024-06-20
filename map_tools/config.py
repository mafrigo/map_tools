from pathlib import Path
import yaml
from typing import Dict, Any


def get_yaml_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, "r") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    return cfg

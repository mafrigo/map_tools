from pathlib import Path
import yaml


def get_yaml_config():
    config_path = Path(__file__).parent / "../config.yaml"
    with open(config_path, "r") as ymlfile:
        cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    return cfg
"""Config management for litellm-ride"""
import json
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_DIR = Path.home() / ".openclaw" / "litellm-ride"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
LITELLM_CONFIG = Path.home() / ".openclaw" / "litellm_config.yaml"

# Default model configurations
DEFAULT_MODELS = {
    "free-gateway": {
        "model_name": "free-gateway",
        "litellm_params": {
            "model": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
            "api_key": os.environ.get("OPENROUTER_API_KEY", "os.environ/OPENROUTER_API_KEY"),
            "falls_backs": [
                "openrouter/stepfun/step-3.5-flash:free",
                "openrouter/qwen/qwen3-next-80b-a3b-instruct:free"
            ]
        }
    },
    "minimax": {
        "model_name": "minimax",
        "litellm_params": {
            "model": "minimax/MiniMax-Text-01",
            "api_key": os.environ.get("MINIMAX_API_KEY", "os.environ/MINIMAX_API_KEY")
        }
    },
    "qwen3": {
        "model_name": "qwen3",
        "litellm_params": {
            "model": "openrouter/qwen/qwen3-8b",
            "api_key": os.environ.get("OPENROUTER_API_KEY", "os.environ/OPENROUTER_API_KEY")
        }
    }
}


def ensure_config_dir():
    """Create config directory if it doesn't exist"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict:
    """Load litellm-ride config"""
    ensure_config_dir()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: Dict):
    """Save litellm-ride config"""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def generate_litellm_config(models: List[Dict]) -> Dict:
    """Generate litellm config from model list"""
    return {
        "model_list": models,
        "litellm_settings": {
            "drop_params": True,
            "set_verbose": False
        },
        "general_settings": {
            "master_key": os.environ.get("LITELLM_MASTER_KEY", None)
        }
    }


def write_litellm_config(config: Dict):
    """Write litellm config file"""
    with open(LITELLM_CONFIG, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def add_model(model_key: str, custom_params: Optional[Dict] = None):
    """Add a model to the config"""
    config = load_config()
    
    if model_key in DEFAULT_MODELS:
        model = DEFAULT_MODELS[model_key].copy()
    elif custom_params:
        model = custom_params
    else:
        raise ValueError(f"Unknown model: {model_key}")
    
    config["models"] = config.get("models", [])
    
    # Check if model already exists
    for i, m in enumerate(config["models"]):
        if m.get("model_name") == model["model_name"]:
            config["models"][i] = model
            break
    else:
        config["models"].append(model)
    
    save_config(config)
    sync_litellm()


def remove_model(model_name: str):
    """Remove a model from config"""
    config = load_config()
    config["models"] = [m for m in config.get("models", []) 
                        if m.get("model_name") != model_name]
    save_config(config)
    sync_litellm()


def set_primary(model_name: str):
    """Set primary model"""
    config = load_config()
    config["primary"] = model_name
    save_config(config)
    sync_litellm()


def sync_litellm():
    """Sync config to litellm config file"""
    config = load_config()
    models = config.get("models", [])
    
    litellm_config = generate_litellm_config(models)
    write_litellm_config(litellm_config)
    
    return litellm_config


def status() -> Dict:
    """Get current status"""
    config = load_config()
    return {
        "models": config.get("models", []),
        "primary": config.get("primary"),
        "litellm_config": str(LITELLM_CONFIG)
    }


def auto_configure():
    """Auto-configure with default models"""
    config = load_config()
    
    # Add default models
    models = []
    for key, model in DEFAULT_MODELS.items():
        models.append(model.copy())
    
    config["models"] = models
    config["primary"] = "free"
    
    save_config(config)
    sync_litellm()
    
    return {"status": "configured", "models": models}

"""CLI for litellm-ride"""
import sys
import click
import os
from pathlib import Path

# Add skill to path
SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR))

from litellm_ride.config import (
    add_model,
    remove_model,
    set_primary,
    auto_configure,
    status,
    sync_litellm,
    load_config,
    DEFAULT_MODELS,
    LITELLM_CONFIG
)


@click.group()
def cli():
    """LiteLLM Ride - Manage AI models through Litellm proxy"""
    pass


@cli.command()
def auto():
    """Auto-configure with best free + paid models"""
    click.echo("Configuring LiteLLM with default models...")
    result = auto_configure()
    
    click.echo(f"✓ Configured {len(result['models'])} models:")
    for m in result["models"]:
        click.echo(f"  - {m['model_name']} -> {m['litellm_params']['model']}")
    
    click.echo(f"\n✓ Config written to {LITELLM_CONFIG}")
    click.echo("\nTo start litellm proxy: litellm-ride start")
    click.echo("To update OpenClaw: openclaw gateway restart")


@cli.command()
def start():
    """Start the litellm proxy server"""
    click.echo("Starting LiteLLM proxy on http://localhost:4000")
    click.echo("Press Ctrl+C to stop")
    
    os.system(f"LITELLM_CONFIG={LITELLM_CONFIG} litellm --port 4000")


@cli.command()
@click.argument("model_key")
def add(model_key):
    """Add a model (free, minimax, qwen, or custom config)"""
    try:
        if model_key in DEFAULT_MODELS:
            add_model(model_key)
            click.echo(f"✓ Added {model_key}")
        else:
            click.echo(f"Unknown model. Available: {', '.join(DEFAULT_MODELS.keys())}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("model_name")
def remove(model_name):
    """Remove a model by name"""
    remove_model(model_name)
    click.echo(f"✓ Removed {model_name}")


@cli.command()
@click.argument("model_name")
def primary(model_name):
    """Set primary model"""
    set_primary(model_name)
    click.echo(f"✓ Primary model set to {model_name}")


@cli.command()
def status_cmd():
    """Show current configuration"""
    s = status()
    
    click.echo("=== LiteLLM Ride Status ===")
    click.echo(f"Config: {s['litellm_config']}")
    click.echo(f"\nPrimary: {s['primary'] or 'Not set'}")
    click.echo(f"\nModels ({len(s['models'])}):")
    for m in s["models"]:
        click.echo(f"  - {m['model_name']}: {m['litellm_params']['model']}")


@cli.command()
def sync():
    """Force sync config to litellm"""
    sync_litellm()
    click.echo(f"✓ Synced to {LITELLM_CONFIG}")


@cli.command()
def list():
    """List available default models"""
    click.echo("Available default models:")
    for key, model in DEFAULT_MODELS.items():
        click.echo(f"  - {key}: {model['litellm_params']['model']}")


@cli.command()
def envcheck():
    """Check required environment variables"""
    click.echo("=== Environment Check ===")
    
    vars_to_check = [
        ("OPENROUTER_API_KEY", "OpenRouter (free models)"),
        ("MINIMAX_API_KEY", "MiniMax"),
        ("LITELLM_MASTER_KEY", "LiteLLM master key (optional)")
    ]
    
    for var, desc in vars_to_check:
        value = os.environ.get(var)
        if value:
            click.echo(f"✓ {var}: {'*' * 8}{value[-4:] if len(value) > 4 else ''} ({desc})")
        else:
            click.echo(f"○ {var}: Not set ({desc})")


if __name__ == "__main__":
    cli()

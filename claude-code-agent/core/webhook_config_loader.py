from pathlib import Path
import yaml
from typing import Dict
from shared.machine_models import WebhookConfig, WebhookCommand
import structlog

logger = structlog.get_logger()


class WebhookConfigLoader:
    def __init__(self, config_dir: Path = Path("config/webhooks")):
        self.config_dir = config_dir
        self.schema_path = config_dir / "schema.yaml"

    def load_webhook_config(self, webhook_name: str) -> WebhookConfig:
        yaml_path = self.config_dir / f"{webhook_name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"webhook config not found: {yaml_path}")

        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        self._validate_against_schema(yaml_data, webhook_name)

        commands = [
            WebhookCommand(**cmd_data) for cmd_data in yaml_data.get("commands", [])
        ]

        config = WebhookConfig(
            name=yaml_data["name"],
            endpoint=yaml_data["endpoint"],
            source=yaml_data["source"],
            commands=commands,
            command_prefix=yaml_data.get("command_prefix", "@agent"),
            requires_signature=yaml_data.get("requires_signature", True),
            signature_header=yaml_data.get("signature_header"),
            secret_env_var=yaml_data.get("secret_env_var"),
            default_command=yaml_data.get("default_command"),
        )

        logger.info("webhook_config_loaded", webhook=webhook_name, commands_count=len(commands))
        return config

    def load_all_webhook_configs(self) -> Dict[str, WebhookConfig]:
        configs = {}
        for yaml_file in self.config_dir.glob("*.yaml"):
            if yaml_file.name == "schema.yaml":
                continue
            webhook_name = yaml_file.stem
            try:
                configs[webhook_name] = self.load_webhook_config(webhook_name)
            except Exception as e:
                logger.error("webhook_config_load_failed", webhook=webhook_name, error=str(e))
                raise
        return configs

    def _validate_against_schema(self, yaml_data: dict, webhook_name: str) -> None:
        if not self.schema_path.exists():
            logger.warning("schema_not_found", schema_path=self.schema_path)
            return

        try:
            import jsonschema
            with open(self.schema_path, "r") as f:
                schema = yaml.safe_load(f)

            jsonschema.validate(yaml_data, schema)
        except ImportError:
            logger.warning("jsonschema_not_installed")
        except jsonschema.ValidationError as e:
            raise ValueError(f"invalid webhook config for {webhook_name}: {e.message}")


webhook_config_loader = WebhookConfigLoader()

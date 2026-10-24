import json
import os

class Settings:
    def __init__(self, data: dict):
        self.nats_url = os.environ.get("NATS_URL") or data.get("nats_url")
        self.nats_user = os.environ.get("NATS_USER") or data.get("nats_user")
        self.nats_password = os.environ.get("NATS_PASSWORD") or data.get("nats_password")
        self.task_subject = data.get("task_subject", "scraper.task.redjum")
        self.result_subject = data.get("result_subject", "scraper.result.redjum")
        self.queue_group = data.get("queue_group", "scrapers")
        self.redjum_url = data.get("redjum_url", "https://redjum.pj.gob.pe/redjum")
        self.max_concurrent_requests = data.get("max_concurrent_requests", 5)
        self.vps_id = os.environ.get("VPS_ID") or data.get("vps_id", "local-vps")
        self.worker_technology = data.get("worker_technology", "python")
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY") or data.get("deepseek_api_key")

        self.admin_api_url = os.environ.get("ADMIN_API_URL")
        self.worker_api_key = os.environ.get("WORKER_API_KEY")
        self.worker_token = os.environ.get("WORKER_TOKEN")
        self.proxy_flush_interval_seconds = data.get("proxy_flush_interval_seconds", 60)
        self.proxy_flush_batch_size = data.get("proxy_flush_batch_size", 10)
        self.heartbeat_interval_seconds = data.get("heartbeat_interval_seconds", 120)

    @staticmethod
    def load() -> "Settings":
        from dotenv import load_dotenv
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for env_path in [
            os.path.join(base_dir, ".env"),
            os.path.join(base_dir, "src", ".env"),
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.getcwd(), "src", ".env")
        ]:
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)

        settings_path = os.path.join(base_dir, "settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Settings(data)

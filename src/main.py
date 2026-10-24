import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file, override=True)

from config.settings import Settings
from parsing.redjum_parser import RedjumParser
from scraping.redjum_scraper import RedjumScraper
from messaging.nats_worker import NatsWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Iniciando Worker de REDJUM (curl_cffi) en Python...")
    settings = Settings.load()

    parser = RedjumParser()
    scraper = RedjumScraper(settings)
    nats_worker = NatsWorker(settings, scraper, parser)

    try:
        asyncio.create_task(nats_worker.run())
        logger.info("Worker REDJUM corriendo. Presiona Ctrl+C para detener.")

        while True:
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("Cerrando la aplicación por solicitud del usuario...")
    except Exception as e:
        logger.error(f"Error en la ejecución del main: {e}")
    finally:
        await nats_worker.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

import sys
import os
import json
import asyncio
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file, override=True)

from config.settings import Settings
from scraping.redjum_scraper import RedjumScraper
from parsing.redjum_parser import RedjumParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def test_consulta(numero_documento: str):
    parameters = {"ruc": numero_documento} if len(numero_documento) == 11 else {"numeroDocumento": numero_documento}
    print(f"Probando RedjumScraper con parametros: {parameters}...")
    settings = Settings.load()
    parser = RedjumParser()
    scraper = RedjumScraper(settings)

    try:
        raw_result = await scraper.scrape(parameters)
        parsed_data = parser.parse(raw_result, numero_documento=numero_documento)

        final_contract = {
            "success": True,
            "data": parsed_data,
            "errorMessage": None
        }

        print("\n=== Contrato de salida (data) ===")
        print(json.dumps(final_contract, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"\n❌ Error al ejecutar consulta: {e}")

if __name__ == "__main__":
    doc_test = sys.argv[1] if len(sys.argv) > 1 else "08247963"
    asyncio.run(test_consulta(doc_test))

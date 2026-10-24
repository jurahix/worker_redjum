import logging
import json
import uuid
import time
import asyncio
from datetime import datetime
import nats
from config.settings import Settings
from scraping.redjum_scraper import RedjumScraper
from parsing.redjum_parser import RedjumParser
from messaging.event_publisher import EventPublisher

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    from shared.event_publisher import EventPublisher as SharedEventPublisher
    from shared.proxy_stats_collector import ProxyStatsCollector
    from shared.scrape_instrumentor import ScrapeInstrumentor
    from shared.failures import build_failure, ScrapeFailure, PARSE_ERROR
except ImportError as e:
    logging.getLogger(__name__).error(f"Error importando modulos shared: {e}")
    raise

logger = logging.getLogger(__name__)

class NatsWorker:
    def __init__(self, settings: Settings, scraper: RedjumScraper, parser: RedjumParser):
        self._settings = settings
        self._scraper = scraper
        self._parser = parser

        from dotenv import load_dotenv
        load_dotenv()

        self.WORKER_ID = os.environ.get("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")
        self.VPS_ID = os.environ.get("VPS_ID", "local-vps")
        self.ENTITY = os.environ.get("ENTITY", "redjum")
        self._worker_id = self.WORKER_ID
        self._active_contexts = 0
        self._active_contexts_lock = asyncio.Lock()
        self._nc = None
        self._heartbeat_task = None
        self._proxy_manager = None

    def get_active_contexts(self):
        return self._active_contexts

    async def run(self):
        try:
            nc = await nats.connect(
                self._settings.nats_url,
                user=self._settings.nats_user,
                password=self._settings.nats_password
            )
            self._nc = nc
            logger.info(f"Conectado a NATS exitosamente con WorkerId: {self._worker_id}")

            self._shared_event_publisher = SharedEventPublisher(nc, self.WORKER_ID, self.VPS_ID, self.ENTITY)
            self._stats_collector = ProxyStatsCollector(nc, self.WORKER_ID, self.ENTITY, flush_interval=30)
            self._stats_collector.start()

            self._event_publisher = EventPublisher(self._settings, nc, self.VPS_ID)

            try:
                from shared.proxy_session_manager import ProxySessionManager
                self._proxy_manager = ProxySessionManager(
                    entity=self.ENTITY,
                    admin_api_url=self._settings.admin_api_url,
                    worker_api_key=self._settings.worker_api_key,
                    event_publisher=self._shared_event_publisher
                )
                try:
                    await self._proxy_manager.initialize()
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo inicializar el pool de proxies: {e}")
            except Exception as outer_e:
                logger.error(f"Error instanciando ProxySessionManager: {outer_e}")
                self._proxy_manager = None

            await self._event_publisher.publish_event(
                self._worker_id, "worker_start", {"message": "Worker REDJUM started successfully"}
            )

            async def proxy_update_handler(msg):
                if self._proxy_manager:
                    try:
                        await self._proxy_manager.initialize()
                    except Exception as e:
                        logger.error(f"Error actualizando proxies: {e}")

            await nc.subscribe("config.proxy.update.redjum", cb=proxy_update_handler)

            self._heartbeat_task = asyncio.create_task(
                self._event_publisher.start_heartbeat_loop(self._worker_id, self.get_active_contexts)
            )

            semaphore = asyncio.Semaphore(self._settings.max_concurrent_requests)

            async def message_handler(msg):
                await semaphore.acquire()
                async with self._active_contexts_lock:
                    self._active_contexts += 1
                asyncio.create_task(self._process_message(nc, msg, semaphore))

            await nc.subscribe(self._settings.task_subject, queue=self._settings.queue_group, cb=message_handler)
            logger.info(f"Suscrito a {self._settings.task_subject} (Queue: {self._settings.queue_group})")

        except Exception as e:
            import traceback
            logger.critical(f"Error en NatsWorker run: {e}\n{traceback.format_exc()}")

    async def _process_message(self, nc, msg, semaphore):
        logger.info(f"Payload crudo recibido: {msg.data.decode('utf-8')}")
        proxy_url = None
        correlation_id = None
        start_time = time.time()

        try:
            payload = json.loads(msg.data.decode("utf-8"))
            correlation_id = payload.get("CorrelationId")
            consultation_id = payload.get("ConsultationId")
            parameters = payload.get("Parameters", {})
            options = payload.get("Options", {})
            scraper_id = payload.get("ScraperId")
            scraper_name = payload.get("ScraperName")
            request_hash = payload.get("RequestHash")
            endpoint_path = payload.get("EndpointPath")

            use_proxy = options.get("UseProxy", False)
            if not use_proxy:
                proxy_url = options.get("ProxyUrl")

            success = False
            data_string = None
            error_message = None


            result_state = None


            result_message = None
            failure_code = None
            failure_detail = None

            try:
                if use_proxy and self._proxy_manager:
                    if not self._proxy_manager._sessions:
                        logger.info("El pool de proxies esta vacio al recibir tarea. Intentando inicializarlo...")
                        try:
                            await self._proxy_manager.initialize()
                        except Exception as e:
                            logger.error(f"Fallo al re-inicializar el pool de proxies: {e}")

                instrumentor = ScrapeInstrumentor(self._shared_event_publisher, self._stats_collector)
                kwargs = {}
                if not use_proxy and proxy_url:
                    kwargs["proxy_url"] = proxy_url

                raw_result = await instrumentor.run(
                    self._scraper.scrape,
                    parameters,
                    proxy_session_manager=self._proxy_manager if use_proxy else None,
                    **kwargs
                )

                try:
                    num_doc = str(parameters.get("numeroDocumento") or parameters.get("ruc") or "")
                    parsed_data = self._parser.parse(raw_result, numero_documento=num_doc)
                except Exception as parse_exc:
                    raise ScrapeFailure(PARSE_ERROR, f"Error en parser REDJUM: {parse_exc}") from parse_exc

                success = True
                from shared.result_states import resolve_entity_result
                result_state, result_message = resolve_entity_result(self.ENTITY, parsed_data, parameters)

                if isinstance(parsed_data, dict):
                    if result_state in ("NO TIENE DATOS", "NO REGISTRA", "SIN RUC"):
                        parsed_data["mensaje"] = result_message
                        parsed_data["message"] = result_message
                    parsed_data["resultState"] = result_state
                    parsed_data["resultMessage"] = result_message

                data_string = json.dumps({
                    "success": parsed_data.get("success", True) if isinstance(parsed_data, dict) else True,
                    "resultState": result_state,
                    "resultMessage": result_message,
                    "data": parsed_data,
                    "errorMessage": None
                }, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Error procesando mensaje para {correlation_id}: {e}")
                failure_code, failure_detail = build_failure(e, {"url": getattr(self._settings, "redjum_url", None)})

                from shared.failures import classify_client_failure

                result_state, error_message = classify_client_failure(e, failure_code, failure_detail)

                result_message = error_message

                data_string = json.dumps({

                    "success": False,

                    "resultState": result_state,

                    "resultMessage": result_message,

                    "data": None,

                    "errorMessage": error_message

                }, ensure_ascii=False)

            processing_time_ms = int((time.time() - start_time) * 1000)

            result = {
                "correlationId": correlation_id,
                "consultationId": consultation_id,
                "entity": self.ENTITY,
                "success": success,
                "resultState": result_state,
                "resultMessage": result_message,
                "data": data_string,
                "errorMessage": error_message,
                "failureCode": failure_code,
                "failureDetail": failure_detail,
                "processedAt": datetime.utcnow().isoformat() + "Z",
                "scraperId": scraper_id,
                "scraperName": scraper_name,
                "requestHash": request_hash,
                "endpointPath": endpoint_path,
                "parameters": parameters,
                "processor": {
                    "vps": self._settings.vps_id,
                    "technology": self._settings.worker_technology,
                    "workerId": self._worker_id,
                    "processingTimeMs": processing_time_ms
                }
            }

            await nc.publish(self._settings.result_subject, json.dumps(result, ensure_ascii=False).encode("utf-8"))
            logger.info(f"Procesado {correlation_id}. Success: {success}. Tiempo: {processing_time_ms}ms")

        except Exception as e:
            logger.error(f"Error inesperado en _process_message: {e}")
        finally:
            async with self._active_contexts_lock:
                self._active_contexts -= 1
            semaphore.release()

    async def stop(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if hasattr(self, '_stats_collector') and self._stats_collector:
            await self._stats_collector.stop()
        if hasattr(self, '_shared_event_publisher') and self._shared_event_publisher:
            await self._shared_event_publisher.publish("worker_stop", detail={"entity": self.ENTITY})
        if self._nc:
            await self._nc.drain()

import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from curl_cffi import requests

from config.settings import Settings
from captcha.captcha_solver import RedjumCaptchaSolver
from parsing.redjum_parser import RedjumParser

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
try:
    from shared.failures import ScrapeFailure, CAPTCHA_FAILED, SITE_DOWN, format_no_data_message
except ImportError:
    CAPTCHA_FAILED = "CAPTCHA_FAILED"
    SITE_DOWN = "SITE_DOWN"

    class ScrapeFailure(Exception):
        def __init__(self, code, message, detail=None):
            super().__init__(message)
            self.code = code
            self.message = message
            self.detail = detail or {}

    def format_no_data_message(document_number, document_type=""):
        doc_str = str(document_number or "").strip()
        is_ruc = (str(document_type).strip().upper() == "RUC") or (
            len(doc_str) == 11 and doc_str.startswith(("10", "20")))
        if is_ruc:
            return f"El RUC  [{doc_str}] No tiene datos"
        return f"El numero documento [{doc_str}] No tiene datos"

logger = logging.getLogger(__name__)


class RedjumScraper:
    """
    Scraper para REDJUM (Registro de Deudores Judiciales Morosos - Poder Judicial)
    https://redjum.pj.gob.pe/redjum/

    Flujo (replica lo que hace el frontend AngularJS):
      1. GET  /redjum/                          -> cookies de sesion (JSESSIONID)
      2. GET  /redjum/Captcha.jpg?hash_id=<rnd> -> imagen captcha (PNG)
      3. GET  /redjum/deudoresPorDocumento/?hash_id=<mismo>&captcha=<txt>&tipoDocumento=<campo>&numerodocumento=<num>
      4. GET  /redjum/deudasPorDeudor/?hash_id=<rnd>&id=<idDeudor>   (detalle)
      5. (fotoDeudorByte deshabilitado: ya no se consultan fotos)

    La capa HTTP de curl_cffi es sincrona; el metodo publico `scrape` la
    ejecuta en un hilo aparte para no bloquear el event loop del worker.
    """

    def __init__(self, settings: Settings, solver: Optional[RedjumCaptchaSolver] = None):
        self.settings = settings
        self.base_url = getattr(settings, "redjum_url", "https://redjum.pj.gob.pe/redjum").rstrip("/")
        self.solver = solver or RedjumCaptchaSolver(
            api_key=getattr(settings, "deepseek_api_key", None),
            solver_type=getattr(settings, "captcha_solver_type", None)
        )
        self.parser = RedjumParser()
        self._tipos_documentos_cache: Optional[list] = None

    # ------------------------------------------------------------------
    # API del worker
    # ------------------------------------------------------------------
    async def scrape(self, parameters: dict, proxy_session=None, proxy_url: str = None) -> Dict[str, Any]:
        """
        Consulta un deudor en REDJUM por numeroDocumento (DNI) o ruc.
        Parametros de entrada estandar (exactamente uno de los dos):
          - numeroDocumento -> DNI (8 digitos)
          - ruc             -> RUC (11 digitos)
        """
        parameters = parameters or {}
        ruc = parameters.get("ruc")
        numero_documento = parameters.get("numeroDocumento") or ruc
        if not numero_documento:
            raise ValueError("El parametro 'numeroDocumento' o 'ruc' es obligatorio.")

        numero_documento = str(numero_documento).strip()
        tipo_documento = "RUC" if ruc or len(numero_documento) == 11 else "DNI"

        if tipo_documento == "DNI" and (len(numero_documento) != 8 or not numero_documento.isdigit()):
            raise ValueError(f"numeroDocumento invalido: '{numero_documento}'. El DNI debe contener exactamente 8 digitos numericos.")
        if tipo_documento == "RUC" and (len(numero_documento) != 11 or not numero_documento.isdigit()):
            raise ValueError(f"ruc invalido: '{numero_documento}'. El RUC debe contener exactamente 11 digitos numericos.")

        proxy_target = None
        if proxy_session:
            proxy_target = proxy_session.as_url
            logger.info(f"Usando proxy del pool: {proxy_target} (ID={getattr(proxy_session, 'proxy_id', None)})")
        elif proxy_url:
            proxy_target = proxy_url
            logger.info(f"Usando proxy directo: {proxy_target}")

        logger.info(f"Iniciando consulta REDJUM - Tipo: {tipo_documento}, Numero: {numero_documento}...")
        return await asyncio.to_thread(
            self._scrape_sync, tipo_documento, numero_documento, proxy_target
        )

    # ------------------------------------------------------------------
    # Nucleo sincrono (port de pruebas/redjum)
    # ------------------------------------------------------------------
    def _scrape_sync(self, tipo_documento: str, numero_documento: str, proxy: str = None) -> Dict[str, Any]:
        return self._consultar_por_documento(tipo_documento, numero_documento, proxy=proxy)

    def _create_session(self, proxy: str = None) -> requests.Session:
        session = requests.Session(impersonate="chrome", verify=False)
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session

    def _resolver_captcha(self, session: requests.Session) -> tuple:
        """Descarga el captcha ligado a un hash_id y lo resuelve. Retorna (hash_id, texto).
        El captcha de REDJUM siempre tiene 4 caracteres; si el OCR devuelve otra
        longitud se descarga uno nuevo en lugar de quemar un intento de consulta."""
        hash_id, captcha_text = "", ""
        for _ in range(5):
            hash_id = str(random.random())
            resp = session.get(f"{self.base_url}/Captcha.jpg", params={"hash_id": hash_id}, timeout=30)
            resp.raise_for_status()
            if not resp.content:
                continue

            captcha_text = self.solver.solve(resp.content)
            if captcha_text and len(captcha_text) == 4:
                break
            logger.debug(f"OCR devolvio '{captcha_text}' (longitud invalida), descargando otro captcha...")
        else:
            raise ScrapeFailure(CAPTCHA_FAILED, "El solver no devolvio un captcha valido de 4 caracteres",
                                {"url": f"{self.base_url}/Captcha.jpg"})

        logger.info(f"Captcha resuelto: '{captcha_text}' (hash_id={hash_id})")
        return hash_id, captcha_text

    @staticmethod
    def _fmt_fecha(fecha) -> str:
        """Acepta datetime, date o str 'dd/mm/yyyy' y devuelve 'dd/mm/yyyy HH:mm:ss'."""
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha.strip(), "%d/%m/%Y")
        return fecha.strftime("%d/%m/%Y 00:00:00")

    def _consultar(self, endpoint: str, params: dict, proxy: str = None) -> tuple:
        """Ejecuta una consulta protegida por captcha. Retorna (payload, sesion_exitosa).
        Reintenta con captcha nuevo si es rechazado, y con sesion nueva (otro nodo
        backend) ante respuestas transitorias (503/vacio) del balanceador.
        HTTP 204 se interpreta como 'sin datos' y se devuelve como payload vacio."""
        session = self._nuevo_intento(proxy)
        last_error = "sin respuesta"
        for attempt in range(1, 8):
            try:
                hash_id, captcha_text = self._resolver_captcha(session)
                query = {"hash_id": hash_id, "captcha": captcha_text, **params}
                resp = session.get(f"{self.base_url}/{endpoint}/", params=query, timeout=60)

                # HTTP 204 = el portal no tiene datos para el criterio (respuesta valida)
                if resp.status_code == 204:
                    return {"data": None, "error": None}, session

                if resp.status_code != 200 or not resp.text.strip():
                    last_error = f"HTTP {resp.status_code}"
                    logger.warning(f"Intento {attempt}: respuesta no valida ({last_error}), renovando sesion...")
                    session.close()
                    session = self._nuevo_intento(proxy)
                    continue

                payload = resp.json()
                error = payload.get("error")
                if error:
                    descripcion = (error.get("descripcion") or "") if isinstance(error, dict) else str(error)
                    last_error = descripcion
                    logger.warning(f"Intento {attempt}: el portal devolvio error: {descripcion}")
                    if "captcha" in descripcion.lower():
                        time.sleep(0.5)
                        continue
                    session.close()
                    raise Exception(f"Error del portal REDJUM: {descripcion}")
                return payload, session
            except Exception as e:
                if isinstance(e, ScrapeFailure) or str(e).startswith("Error del portal"):
                    session.close()
                    raise
                last_error = str(e)
                logger.warning(f"Intento {attempt}: {e}")
                session.close()
                session = self._nuevo_intento(proxy)
                time.sleep(1)
        session.close()

        code = CAPTCHA_FAILED if "captcha" in str(last_error).lower() else SITE_DOWN
        raise ScrapeFailure(
            code,
            f"No se pudo completar la consulta al endpoint {endpoint}. Ultimo error: {last_error}",
            {"url": f"{self.base_url}/{endpoint}/", "attempts": 7}
        )

    def _nuevo_intento(self, proxy: str = None) -> requests.Session:
        """Crea una sesion nueva y la inicializa contra la pagina principal."""
        session = self._create_session(proxy)
        session.get(f"{self.base_url}/", timeout=30).raise_for_status()
        return session

    # ------------------------------------------------------------------
    # CONSULTAS PUBLICAS
    # ------------------------------------------------------------------
    def consultar_por_periodo(self, fecha_inicio=None, fecha_fin=None,
                              incluir_detalle: bool = False, max_detalles: int = None,
                              max_retries: int = 3, proxy: str = None) -> dict:
        """
        Consulta deudores registrados en un rango de fechas.

        fecha_inicio / fecha_fin: datetime o str 'dd/mm/yyyy'. Por defecto los ultimos 30 dias.
        incluir_detalle: si True, descarga las deudas de cada deudor.
        max_detalles: limita cuantos deudores detallar (None = todos).
        """
        fecha_fin = fecha_fin or datetime.now()
        fecha_inicio = fecha_inicio or (fecha_fin - timedelta(days=30) if not isinstance(fecha_fin, str) else datetime.now() - timedelta(days=30))

        params = {
            "fechaInicio": self._fmt_fecha(fecha_inicio),
            "fechaFin": self._fmt_fecha(fecha_fin),
        }
        logger.info(f"Consultando REDJUM por periodo: {params['fechaInicio']} -> {params['fechaFin']}")

        session = None
        last_error = None
        try:
            for attempt in range(1, max_retries + 1):
                try:
                    payload, session = self._consultar("deudoresPorPeriodo", params, proxy=proxy)
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Error en intento {attempt}/{max_retries}: {e}")
                    time.sleep(1)
            else:
                raise ScrapeFailure(
                    SITE_DOWN,
                    f"No se pudo completar la consulta a REDJUM tras {max_retries} intentos. Ultimo error: {last_error}",
                    {"url": f"{self.base_url}/deudoresPorPeriodo/", "attempts": max_retries}
                )

            info_basico_json = json.dumps(payload, ensure_ascii=False)
            data_array = payload.get("data") or []

            if not data_array:
                return {
                    "InfoBasico": info_basico_json,
                    "Deudores": [],
                    "Detalles": [],
                    "Total": 0,
                    "Mensaje": f"El periodo {params['fechaInicio']} - {params['fechaFin']} no presenta registros de deudores",
                    "ResultState": "NO TIENE DATOS",
                }

            deudores = self.parser.parse_deudores(data_array)
            logger.info(f"Se encontraron {len(deudores)} deudores en el periodo")

            detalles = []
            if incluir_detalle:
                limite = len(deudores) if max_detalles is None else min(max_detalles, len(deudores))
                for deudor in deudores[:limite]:
                    detalles.append(self.obtener_detalle(session, deudor["id"]))
                    time.sleep(0.3)

            return {
                "InfoBasico": info_basico_json,
                "Deudores": deudores,
                "Detalles": detalles,
                "Total": len(deudores),
                "Mensaje": "Registra deudores judiciales morosos",
                "ResultState": "REGISTRA",
            }
        finally:
            if session:
                session.close()

    def _resolver_campo_documento(self, tipo_documento: str) -> str:
        """Traduce 'DNI'/'RUC'/... al codigo 'campo' que espera el portal (ej. '01  ')."""
        tipo = str(tipo_documento).strip().upper()
        if tipo and tipo[0].isdigit():
            return str(tipo_documento)  # ya es un codigo campo
        for item in self.tipos_documentos():
            desc = (item.get("descrimaestra") or "").strip().upper()
            if desc == tipo or re.sub(r'[^A-Z0-9]', '', desc) == re.sub(r'[^A-Z0-9]', '', tipo):
                return item.get("campo")
        raise ValueError(f"Tipo de documento no reconocido por REDJUM: {tipo_documento}")

    def _consultar_por_documento(self, tipo_documento: str, numero_documento: str,
                                 incluir_detalle: bool = True, max_retries: int = 3,
                                 proxy: str = None) -> dict:
        """
        Consulta un deudor por tipo y numero de documento (equivalente al flujo REDAM).
        tipo_documento: 'DNI', 'RUC', 'PASAPORTE', 'CARNET DE EXTRANJERIA' o el codigo campo.
        """
        if not numero_documento:
            raise ValueError("El parametro numero_documento es requerido")

        campo = self._resolver_campo_documento(tipo_documento)
        params = {"tipoDocumento": campo, "numerodocumento": str(numero_documento)}
        logger.info(f"Consultando REDJUM por documento: {tipo_documento} {numero_documento} (campo={campo!r})")

        session = None
        last_error = None
        try:
            for attempt in range(1, max_retries + 1):
                try:
                    payload, session = self._consultar("deudoresPorDocumento", params, proxy=proxy)
                    break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Error en intento {attempt}/{max_retries}: {e}")
                    time.sleep(1)
            else:
                raise ScrapeFailure(
                    SITE_DOWN,
                    f"No se pudo completar la consulta a REDJUM tras {max_retries} intentos. Ultimo error: {last_error}",
                    {"url": f"{self.base_url}/deudoresPorDocumento/", "attempts": max_retries}
                )

            info_basico_json = json.dumps(payload, ensure_ascii=False)
            data_array = payload.get("data") or []

            if not data_array:
                return {
                    "InfoBasico": info_basico_json,
                    "InfCompleta": "",
                    "Foto": "",
                    "Mensaje": format_no_data_message(numero_documento, tipo_documento),
                    "ResultState": "NO REGISTRA",
                }

            id_deudor = data_array[0].get("id")
            logger.info(f"ID Deudor encontrado: {id_deudor}")

            info_completa_json = ""
            if incluir_detalle:
                detalle = self.obtener_detalle(session, id_deudor)
                info_completa_json = json.dumps(detalle["deudas"], ensure_ascii=False)

            return {
                "InfoBasico": info_basico_json,
                "InfCompleta": info_completa_json,
                "Mensaje": "Registra deudas judiciales morosas",
                "ResultState": "REGISTRA",
            }
        finally:
            if session:
                session.close()

    # ------------------------------------------------------------------
    # DETALLE DEL DEUDOR
    # ------------------------------------------------------------------
    def obtener_detalle(self, session: requests.Session, id_deudor: str) -> dict:
        """Descarga las deudas de un deudor dentro de una sesion ya validada (sin foto)."""
        deudas_resp = session.get(
            f"{self.base_url}/deudasPorDeudor/",
            params={"hash_id": str(random.random()), "id": id_deudor},
            timeout=60,
        )
        deudas_resp.raise_for_status()
        deudas_payload = deudas_resp.json()

        return {
            "id": id_deudor,
            "deudas": deudas_payload,
            "deudas_normalizadas": self.parser.parse_deudas(deudas_payload.get("data")),
        }

    def tipos_documentos(self, proxy: str = None) -> list:
        """Devuelve la lista de tipos de documento aceptados por el portal (cacheada)."""
        if self._tipos_documentos_cache:
            return self._tipos_documentos_cache
        session = self._nuevo_intento(proxy)
        try:
            resp = session.get(
                f"{self.base_url}/tiposDocumentos/",
                params={"hash_id": str(random.random())},
                timeout=30,
            )
            resp.raise_for_status()
            self._tipos_documentos_cache = resp.json()
            return self._tipos_documentos_cache
        finally:
            session.close()

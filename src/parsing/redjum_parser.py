import json
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _ts_to_iso(ts) -> str | None:
    """Convierte un timestamp en milisegundos a fecha legible."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _loads_or_none(value):
    """Parsea una cadena JSON; devuelve None si viene vacia o no es JSON."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


class RedjumParser:
    """
    Normaliza las respuestas del portal REDJUM (Registro de Deudores
    Judiciales Morosos) hacia el contrato de salida del worker.
    """

    # ------------------------------------------------------------------
    # Normalizadores de payloads crudos del portal
    # ------------------------------------------------------------------
    @staticmethod
    def parse_deudores(data: list) -> list:
        deudores = []
        for item in data or []:
            deudores.append({
                "id": item.get("id"),
                "tipoDocumento": item.get("tipoDocumento"),
                "nroDocumento": item.get("nroDocumento"),
                "nombres": item.get("nombres") or item.get("razonSocial"),
                "nombre": item.get("nombre"),
                "apePaterno": item.get("apePaterno"),
                "apeMaterno": item.get("apeMaterno"),
                "razonSocial": item.get("razonSocial"),
                "nroPartidaElect": item.get("nroPartidaElect"),
                "fecRegistro": _ts_to_iso(item.get("fecRegistro")),
            })
        return deudores

    @staticmethod
    def parse_deudas(data: list) -> list:
        deudas = []
        for item in data or []:
            deudas.append({
                "nProceso": item.get("nProceso"),
                "nExpediente": item.get("nExpediente"),
                "nAnoExpediente": item.get("nAnoExpediente"),
                "xDistritoJudicial": item.get("xDistritoJudicial"),
                "xEspecialidad": item.get("xEspecialidad"),
                "xJuzgado": item.get("xJuzgado"),
                "xMateria": item.get("xMateria"),
                "aFavorDe": (item.get("aFavorDe") or "").strip() or None,
                "xSecretario": item.get("xSecretario"),
                "nResolucionMandato": item.get("nResolucionMandato"),
                "fResolucionMandato": _ts_to_iso(item.get("fResolucionMandato")),
                "montos": [
                    {"monto": d.get("nMonto"), "moneda": d.get("xMoneda")}
                    for d in (item.get("deudasBean") or [])
                ],
            })
        return deudas

    @staticmethod
    def parse_foto(data: list):
        if data and isinstance(data, list) and data[0]:
            return data[0].get("foto")
        return None

    # ------------------------------------------------------------------
    # Contrato del worker
    # ------------------------------------------------------------------
    def parse(self, raw_input: Any, numero_documento: str = "") -> Dict[str, Any]:
        """
        Convierte la salida cruda del scraper (dict con InfoBasico/InfCompleta/
        Foto/Mensaje/ResultState, o su equivalente en JSON string) al contrato
        normalizado: infoBasico, deudor, infCompleta, deudas, foto, mensaje,
        resultState.
        """
        raw = raw_input
        if isinstance(raw, str):
            raw = _loads_or_none(raw) or {}
        if not isinstance(raw, dict):
            raw = {}

        mensaje = raw.get("Mensaje") or raw.get("mensaje") or ""
        result_state = raw.get("ResultState") or raw.get("resultState") or ""

        info_basico = _loads_or_none(raw.get("InfoBasico") or raw.get("infoBasico"))
        inf_completa = _loads_or_none(raw.get("InfCompleta") or raw.get("infCompleta"))
        foto_payload = _loads_or_none(raw.get("Foto") or raw.get("foto"))

        deudores = self.parse_deudores((info_basico or {}).get("data"))
        deudor = deudores[0] if deudores else None
        deudas = self.parse_deudas((inf_completa or {}).get("data"))
        foto = self.parse_foto((foto_payload or {}).get("data"))

        if not result_state:
            result_state = "REGISTRA" if deudor else "NO TIENE DATOS"

        if result_state == "REGISTRA" and not deudor:
            result_state = "NO TIENE DATOS"

        if not mensaje:
            if deudor:
                mensaje = "Registra deudas judiciales morosas"
            else:
                mensaje = f"El numero documento [{numero_documento}] No tiene datos"

        return {
            "success": True,
            "numeroDocumento": numero_documento or None,
            "infoBasico": info_basico if deudor else None,
            "deudor": deudor,
            "infCompleta": inf_completa if deudor else {"mensaje": mensaje},
            "deudas": deudas,
            "foto": foto,
            "mensaje": mensaje,
            "resultState": result_state,
        }

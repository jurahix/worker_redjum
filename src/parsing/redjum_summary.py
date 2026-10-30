import logging

logger = logging.getLogger(__name__)


class RedjumSummaryMapper:
    """
    Capa de minimización de datos (protección de datos personales).
    Reduce la salida completa del parser REDJUM a lo que muestra la tarjeta:
    identidad del deudor, fecha de registro y la(s) deuda(s) (moneda + monto).
    Sin foto ni detalle procesal completo.

    El parser (RedjumParser) no se toca: sus datos siguen alimentando
    la resolución de estados (semaforización) por dentro.
    """

    DEUDOR_FIELDS = (
        "nombres",
        "apePaterno",
        "apeMaterno",
        "razonSocial",
        "tipoDocumento",
        "nroDocumento",
        "fecRegistro",
    )

    def build_summary(self, parsed_data, parameters: dict = None) -> dict:
        """
        Devuelve el resumen mínimo para data:
        {"numeroDocumento": ..., "deudor": {...}|None,
         "deudas": [{"moneda": ..., "monto": ...}, ...]}
        """
        parameters = parameters or {}
        parsed = parsed_data if isinstance(parsed_data, dict) else {}

        numero_doc = str(
            parsed.get("numeroDocumento")
            or parameters.get("numeroDocumento")
            or parameters.get("numero_documento")
            or ""
        )

        deudor = parsed.get("deudor")
        deudor_res = None
        if isinstance(deudor, dict):
            deudor_res = {f: deudor.get(f, "") for f in self.DEUDOR_FIELDS}
            if not numero_doc:
                numero_doc = str(deudor_res.get("nroDocumento") or "")

        # Aplana los montos de todas las deudas: [{"moneda": ..., "monto": ...}]
        deudas_res = []
        for item in parsed.get("deudas") or []:
            if not isinstance(item, dict):
                continue
            for m in item.get("montos") or []:
                if isinstance(m, dict) and m.get("monto") not in (None, ""):
                    deudas_res.append({
                        "moneda": m.get("moneda"),
                        "monto": m.get("monto"),
                    })

        return {
            "numeroDocumento": numero_doc,
            "deudor": deudor_res,
            "deudas": deudas_res,
        }

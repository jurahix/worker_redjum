import base64
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

PROMPT_SISTEMA_REDJUM = """Eres un OCR especializado en la resolución de CAPTCHAs.

Tu única tarea es analizar la imagen y extraer la secuencia de caracteres alfanuméricos que contiene.
El texto puede aparecer en color blanco sobre fondo transparente u oscuro.

Reglas:
1. Longitud: La cadena contiene exactamente 4 caracteres alfanuméricos.
2. Formato: Letras y números (0-9).
3. Responde ÚNICAMENTE con los 4 caracteres en mayúsculas, sin espacios, saltos de línea ni explicaciones."""


class RedjumCaptchaSolver:
    """
    Solucionador de Captcha para el portal REDJUM del Poder Judicial.
    El captcha consiste en 4 caracteres alfanumericos (texto blanco
    sobre fondo transparente).

    Estrategia segun CAPTCHA_SOLVER_TYPE:
      - "local" (default): ddddocr primero, DeepSeek como fallback.
      - "deepseek": DeepSeek (visión/OCR) primero, ddddocr como fallback.
    Todos los metodos son sincronos: el scraper los ejecuta dentro de
    un hilo (asyncio.to_thread), por lo que la llamada a DeepSeek usa
    httpx sincrono.
    """
    def __init__(self, solver_type: str = None, api_key: str = None,
                 api_base: str = None, model: str = None):
        self.solver_type = (solver_type or os.getenv("CAPTCHA_SOLVER_TYPE") or "local").strip().lower()

        self.api_key = (api_key or "").strip() or (os.getenv("DEEPSEEK_API_KEY") or "").strip() or None
        self.api_base = (api_base or "").strip() or (os.getenv("DEEPSEEK_API_BASE") or "").strip() or "https://api.deepseek.com/v1"
        self.model = (model or "").strip() or (os.getenv("DEEPSEEK_MODEL") or "").strip() or "deepseek-chat"

        self._ocr = None

        if self.api_key:
            masked = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "***"
            logger.info(f"RedjumCaptchaSolver: DeepSeek disponible como {'primario' if self.solver_type == 'deepseek' else 'fallback'} (Key: {masked}, Model: {self.model})")
        else:
            logger.warning("DEEPSEEK_API_KEY no configurada. Solo estara disponible el solucionador local ddddocr.")

    @property
    def ocr(self):
        if self._ocr is None:
            import ddddocr
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr

    def solve(self, image_bytes: bytes) -> str:
        """
        Resuelve el captcha a partir de los bytes de la imagen.
        Retorna la cadena en mayusculas (4 caracteres alfanumericos) o "".
        """
        if not image_bytes:
            return ""

        solvers = [self._solve_deepseek, self._solve_local]
        if self.solver_type != "deepseek":
            solvers.reverse()

        for solver in solvers:
            try:
                texto = solver(image_bytes)
                if texto:
                    return texto
            except Exception as e:
                logger.error(f"Error en {solver.__name__}: {e}")
        return ""

    def solve_from_bytes(self, image_bytes: bytes) -> str:
        return self.solve(image_bytes)

    # ------------------------------------------------------------------
    def _solve_local(self, image_bytes: bytes) -> str:
        texto = self.ocr.classification(image_bytes)
        clean = re.sub(r'[^a-zA-Z0-9]', '', texto or '').strip().upper()
        if clean:
            logger.info(f"Captcha resuelto por ddddocr: '{clean}'")
        return clean

    def _solve_deepseek(self, image_bytes: bytes) -> str:
        if not self.api_key:
            return ""

        image_bytes = self._flatten_for_vision(image_bytes)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = "image/png" if image_bytes.startswith(b"\x89PNG") else "image/jpeg"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA_REDJUM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extrae los 4 caracteres de este captcha en mayusculas:"},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 10
        }

        url = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code} desde DeepSeek API: {response.text}")
                return ""
            data = response.json()
            raw_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            clean = re.sub(r'[^a-zA-Z0-9]', '', raw_text).upper()
            if clean:
                logger.info(f"Captcha resuelto por DeepSeek: '{clean}'")
            return clean

    @staticmethod
    def _flatten_for_vision(image_bytes: bytes) -> bytes:
        """
        El captcha de REDJUM es texto blanco sobre fondo transparente; si el
        canal alpha se compone sobre blanco el texto queda invisible para el
        modelo de vision. Se aplana sobre fondo negro para hacerlo legible.
        """
        try:
            import io
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img = img.convert("RGBA")
                fondo = Image.new("RGBA", img.size, (0, 0, 0, 255))
                img = Image.alpha_composite(fondo, img).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            logger.warning(f"No se pudo preprocesar el captcha para DeepSeek: {e}")
            return image_bytes

import re

class InterruptionHandler:
    def __init__(self):
        # La lógica de interrupción ahora es manejada nativamente por el Server VAD de OpenAI Realtime API.
        # Retenemos esta clase para exportar la configuración recomendada de latencia ultra-baja (140ms)
        # y mantener la estructura del proyecto en caso de requerir fallback en el futuro.
        pass

    @staticmethod
    def get_realtime_vad_config():
        """
        Retorna la configuración de turn_detection requerida por la API Realtime de OpenAI
        para lograr un Barge-in de latencia ultra-baja (~140ms).
        """
        return {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 140
        }
import re

class InterruptionHandler:
    def __init__(self):
        # 1. Backchannels: Palabras que el usuario dice para mostrar que escucha
        # Si el usuario dice esto, el bot DEBE SEGUIR HABLANDO.
        self.backchannels = {
            "ajá", "aja", "mmm", "uh", "eh", "sí", "si", "ok", "vale", "claro",
            "perfecto", "bien", "ya", "entiendo", "uh huh", "uh-huh", "hmm", 
            "bueno", "dale", "fino", "listo", "venga"
        }

        # 2. Interruptores Críticos: Palabras que indican intención de tomar el turno
        # Si estas aparecen, cortamos el audio en <140ms.
        self.interruption_triggers = {
            "pero", "espera", "oye", "disculpa", "perdona", "para", "detente",
            "no", "quiero", "necesito", "busco", "pregunta", "dime", "cuánto", 
            "precio", "talla", "tienes", "hola", "stop"
        }

        # Regex optimizada para detectar sonidos vocálicos repetidos (ej: "mmmmm")
        self.filler_regex = re.compile(r"^(a+j+a+|m+m+|u+h+|e+h+|h+m+)$", re.IGNORECASE)

    def is_backchannel(self, text: str) -> bool:
        """Determina si el texto es solo ruido de fondo o asentimiento."""
        t = text.lower().strip().replace(".", "").replace(",", "")
        
        if not t:
            return True

        # Caso 1: Es una palabra de la lista de backchannels
        if t in self.backchannels:
            return True

        # Caso 2: Es un sonido de relleno (regex)
        if self.filler_regex.match(t):
            return True

        return False

    def should_interrupt(self, transcript: str) -> bool:
        """
        Lógica de decisión ultra-rápida para Barge-in.
        Retorna True si el bot debe callarse inmediatamente.
        """
        cleaned_text = transcript.strip().lower()
        
        if not cleaned_text:
            return False

        # --- REGLA 1: Prioridad a Interruptores Críticos ---
        # Si la primera palabra ya indica una interrupción, no perdemos tiempo.
        words = cleaned_text.split()
        if any(word in self.interruption_triggers for word in words[:2]):
            return True

        # --- REGLA 2: Ignorar Backchanneling ---
        if self.is_backchannel(cleaned_text):
            return False

        # --- REGLA 3: Longitud y Carga Semántica ---
        # Una frase de más de 2 palabras que no sea backchannel suele ser intención real (Barge-in rápido).
        if len(words) >= 2:
            return True

        # --- REGLA 4: Detección de Preguntas (Modismos Latinos) ---
        query_indicators = ["qué", "quien", "cuál", "cuanto", "dónde", "cómo"]
        if any(q in cleaned_text for q in query_indicators):
            return True

        return False
from abc import ABC, abstractmethod


class AIProvider(ABC):
    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Envoie un prompt et retourne la réponse textuelle du modèle."""

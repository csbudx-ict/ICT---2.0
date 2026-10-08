import json

from google import genai

from ict_scanner.ai.providers import AIProvider
from ict_scanner.ai.schemas import AIEvaluationSchema
from ict_scanner.config.settings import settings


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
    async def evaluate_setup(self, prompt: str) -> AIEvaluationSchema:
        # In genai SDK, we can pass response_schema directly
        response = self.client.models.generate_content(
            model=settings.ai_model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AIEvaluationSchema,
            },
        )
        data = json.loads(response.text or "{}")
        return AIEvaluationSchema(**data)

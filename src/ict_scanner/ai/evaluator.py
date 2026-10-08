import json
import logging
from typing import Dict, Any, Optional
from ict_scanner.config.settings import settings
from ict_scanner.ai.prompt_templates import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger(__name__)

class AIEvaluator:
    def __init__(self):
        self.provider = settings.ai_provider.lower()
        if self.provider == "openai":
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.openai_api_key or "dummy_key_to_prevent_startup_crash")
        elif self.provider == "anthropic":
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        elif self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self.client = genai.GenerativeModel(settings.ai_model, system_instruction=SYSTEM_PROMPT)
        else:
            self.client = None
            
    async def evaluate_setup(self, setup: Dict[str, Any], htf_bias: str = "Neutral", itf_trend: str = "Neutral") -> Optional[Dict[str, Any]]:
        prompt = USER_PROMPT.format(
            symbol=setup.get('symbol', 'Unknown'),
            session_name=setup.get('session_name', 'Unknown'),
            htf_bias=htf_bias,
            itf_trend=itf_trend,
            direction=setup.get('direction', 'Unknown'),
            sweep_level=setup.get('sweep_level', 0.0),
            fvg_low=setup.get('fvg_low', 0.0),
            fvg_high=setup.get('fvg_high', 0.0),
            entry_price=setup.get('entry_price', 0.0),
            stop_loss=setup.get('stop_loss', 0.0),
            take_profit=setup.get('take_profit', 0.0),
            rr_ratio=setup.get('rr_ratio', 0.0)
        )
        
        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=settings.ai_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    timeout=30.0
                )
                raw_json = response.choices[0].message.content
                
            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=settings.ai_model,
                    system=SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    timeout=30.0
                )
                raw_json = response.content[0].text
            elif self.provider == "gemini":
                import google.generativeai as genai
                response = await self.client.generate_content_async(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )
                raw_json = response.text
            else:
                logger.error("AI provider not supported.")
                return None
                
            # Parse and validate JSON
            data = json.loads(raw_json)
            
            # Enforce server-side probability threshold
            prob = data.get('probability_score', 0)
            data['approved'] = bool(prob >= settings.min_probability_threshold)
            
            if not data['approved']:
                logger.info(f"Setup rejected by AI. Score: {prob} < {settings.min_probability_threshold}")
                
            return data
            
        except Exception as e:
            logger.error(f"Error evaluating setup with AI: {e}")
            return None

from ict_scanner.ai.providers import AIProvider
from ict_scanner.ai.schemas import AIEvaluationSchema
from ict_scanner.config.settings import settings
from ict_scanner.domain.models import Setup


class AIAnalyst:
    def __init__(self, provider: AIProvider):
        self.provider = provider
        
    def _build_prompt(self, setup: Setup) -> str:
        return f"""
        Evaluate this setup:
        Asset: {setup.symbol} | Killzone: {setup.session_name.value}
        Direction: {setup.direction.value}
        Liquidity swept: {setup.sweep_type} at {setup.sweep_level}
        MSS: {setup.mss_level}, displacement = {setup.displacement_atr}x ATR
        FVG: [{setup.fvg_low} - {setup.fvg_high}]
        Levels: Entry={setup.entry_price}, SL={setup.stop_loss}, TP1={setup.tp1}, TP2={setup.tp2}
        """
        
    async def analyze(self, setup: Setup) -> AIEvaluationSchema:
        prompt = self._build_prompt(setup)
        eval_result = await self.provider.evaluate_setup(prompt)
        return eval_result
        
    def calculate_final_probability(self, setup: Setup, evaluation: AIEvaluationSchema) -> int:
        return int(
            settings.ai_weight * evaluation.probability_score + 
            (1.0 - settings.ai_weight) * setup.rule_score
        )

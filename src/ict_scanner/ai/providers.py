from typing import Protocol

from ict_scanner.ai.schemas import AIEvaluationSchema


class AIProvider(Protocol):
    async def evaluate_setup(self, prompt: str) -> AIEvaluationSchema:
        ...

class DummyAIProvider:
    async def evaluate_setup(self, prompt: str) -> AIEvaluationSchema:
        from ict_scanner.ai.schemas import ConfluenceFactor
        return AIEvaluationSchema(
            probability_score=85,
            market_bias="Bullish",
            headline="Strong Bullish Setup",
            thesis="This is a dummy thesis.",
            why_take_it=["Reason 1"],
            risks=["Risk 1"],
            invalidation="Below SL",
            confluence_checklist=[ConfluenceFactor(factor="HTF Bias", present=True)],
            management_plan="Trail SL to breakeven at TP1"
        )

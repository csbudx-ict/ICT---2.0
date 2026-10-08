from pydantic import BaseModel, Field


class ConfluenceFactor(BaseModel):
    factor: str
    present: bool

class AIEvaluationSchema(BaseModel):
    probability_score: int = Field(..., ge=1, le=100)
    market_bias: str = Field(..., pattern="^(Bullish|Bearish|Neutral)$")
    headline: str
    thesis: str
    why_take_it: list[str]
    risks: list[str]
    invalidation: str
    confluence_checklist: list[ConfluenceFactor]
    management_plan: str

from pydantic import BaseModel, Field


class MetricCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    value: float
    labels: dict = Field(default_factory=dict)

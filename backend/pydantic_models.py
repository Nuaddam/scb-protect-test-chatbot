from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class ModelName(str, Enum):
    GPT4_1 = "gpt-4.1"
    GPT4_1_MINI = "gpt-4.1-mini"

class QueryInput(BaseModel):
    question: str
    session_id: str = Field(default=None)
    model: ModelName = Field(default=ModelName.GPT4_1_MINI)

class QueryResponse(BaseModel):
    answer: str
    session_id: str
    model: ModelName

class DocumentInfo(BaseModel):
    id: int
    filename: str
    upload_timestamp: datetime

class DeleteFileRequest(BaseModel):
    file_id: int
    
class ProductInterest(BaseModel):
    """Structured product interest data."""
    name: str = Field(..., description="Customer name")
    age: int = Field(..., description="Customer age")
    occupation: str = Field(..., description="Customer occupation")
    income: int = Field(..., description="Customer monthly income")
    product_name: str = Field(..., description="Customer product of interest")
    memo: str = Field("", description="Extra notes from customer")
from pydantic import BaseModel, Field

class ProductInterest(BaseModel):
    name: str = Field(..., description="User's name")
    age: int = Field(..., description="User's age")
    occupation: str = Field(..., description="User's occupation")
    income: int = Field(..., description="User's income per month")
    product_name: str = Field(..., description="Product user is interested in")
    memo: str = Field("", description="Additional notes or preferences")
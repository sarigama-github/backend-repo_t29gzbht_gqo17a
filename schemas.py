"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# SaaS.ai specific schemas

class Idea(BaseModel):
    """Represents a submitted idea from the user"""
    text: str = Field(..., description="Raw idea text from the user")

class PrototypeVersion(BaseModel):
    """Represents a generated prototype version for an idea"""
    idea_id: str = Field(..., description="Associated idea document ID")
    idea_text: str = Field(..., description="Original idea text snapshot")
    version: int = Field(..., ge=1, description="Monotonic version number per idea")
    site_type: Literal["landing","dashboard","ecommerce","blog"] = Field(..., description="Prototype type")
    code: str = Field(..., description="Single-file prototype code (HTML + Tailwind + optional JSX via Babel)")
    notes: Optional[str] = Field(None, description="Additional generation notes or recommendations")

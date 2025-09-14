"""Custom PyObjectId field for MongoDB ObjectId handling in Pydantic"""

from bson import ObjectId
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema
from typing import Any, Dict


class PyObjectId(ObjectId):
    """
    Custom PyObjectId that works with Pydantic v2
    Handles MongoDB ObjectId serialization/deserialization
    """
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, 
        source_type: Any, 
        handler: Any
    ) -> core_schema.CoreSchema:
        """Define core schema for Pydantic v2"""
        return core_schema.union_schema([
            # Handle ObjectId objects
            core_schema.is_instance_schema(ObjectId),
            # Handle string representations
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ])
        ])
    
    @classmethod  
    def __get_pydantic_json_schema__(
        cls, 
        core_schema: core_schema.CoreSchema, 
        handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Define JSON schema for OpenAPI docs"""
        return {"type": "string", "format": "objectid"}
    
    @classmethod
    def validate(cls, value: Any) -> ObjectId:
        """Validate and convert value to ObjectId"""
        if isinstance(value, ObjectId):
            return value
        elif isinstance(value, str):
            if ObjectId.is_valid(value):
                return ObjectId(value)
            else:
                raise ValueError(f"Invalid ObjectId: {value}")
        else:
            raise ValueError(f"ObjectId expected, got {type(value)}")
    
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        """Modify field schema for Pydantic v1 compatibility"""
        field_schema.update({"type": "string", "format": "objectid"})
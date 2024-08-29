from types import UnionType
from typing import List, Literal, Optional, Type, get_args, get_origin

from pydantic import BaseModel


def generate_schema_prompt(schema: Type[BaseModel]) -> str:
    """
    Converts the pydantic schema into a text representation that can be embedded
    into the prompt payload.
    """

    def generate_payload(model: Type[BaseModel]):
        payload = []
        for key, value in model.model_fields.items():
            field_annotation = value.annotation
            annotation_origin = get_origin(field_annotation)
            annotation_arguments = get_args(field_annotation)

            if field_annotation is None:
                continue
            elif annotation_origin in {list, List}:
                if len(annotation_arguments) > 0:
                    if isinstance(annotation_arguments[0], type) and issubclass(annotation_arguments[0], BaseModel):
                        payload.append(
                            f'"{key}": [{generate_payload(annotation_arguments[0])}]'
                        )
                    else:
                        payload.append(f'"{key}": [{get_type_name(annotation_arguments[0])}]')
                else:
                    payload.append(f'"{key}": [any]')
            elif annotation_origin == UnionType or (annotation_origin is Optional and len(annotation_arguments) > 1):
                union_types = [arg for arg in annotation_arguments if arg is not type(None)]
                union_payload = []
                for arg in union_types:
                    if isinstance(arg, type) and issubclass(arg, BaseModel):
                        union_payload.append(generate_payload(arg))
                    else:
                        union_payload.append(get_type_name(arg))
                payload.append(f'"{key}": {" | ".join(union_payload)}')
            elif annotation_origin == Literal:
                allowed_values = [f'"{arg}"' for arg in annotation_arguments]
                payload.append(f'"{key}": {" | ".join(allowed_values)}')
            elif isinstance(field_annotation, type) and issubclass(field_annotation, BaseModel):
                payload.append(f'"{key}": {generate_payload(field_annotation)}')
            else:
                payload.append(f'"{key}": {get_type_name(field_annotation)}')

            if value.description:
                payload[-1] += f" // {value.description}"

        # All brackets are double defined so they will passthrough a call to `.format()` where we
        # pass custom variables
        return "{{\n" + ",\n".join(payload) + "\n}}"

    def get_type_name(annotation):
        if isinstance(annotation, type):
            return annotation.__name__.lower()
        elif hasattr(annotation, '__name__'):
            return annotation.__name__.lower()
        else:
            return str(annotation).lower()

    return generate_payload(schema)

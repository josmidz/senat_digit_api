

from types import GeneratorType
from typing import Any, Dict, Optional

def add_translation_meta(*, may_have_translation: bool = False, to_be_translated_in_front: bool = False, data_type: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Returns metadata for translation to be added to a Pydantic Field.
    """
    return {
        "may_have_translation": may_have_translation,
        "to_be_translated_in_front": to_be_translated_in_front,
        "data_type": data_type or {}
    }

 
def translation_meta(
    may_have_translation: bool = False,
    to_be_translated_in_front: bool = False,
    data_type: Dict[str, bool] = None,
    extra_metas: Dict[str, bool] = {}, 
    auto_generate: bool = False,
    can_be_encrypted: Optional[bool] = False,
    generator_type: Optional[GeneratorType] = None,
    overview_data_type: Optional[Dict[str, bool]] = {}, 
    custom_generator: Optional[callable] = None,
    exclude_from_head: Optional[bool] = False,
    exclude_from_update_head: Optional[bool] = False,
    exclude_at_all: Optional[bool] = False,
    exclude_from_data_table: Optional[bool] = False,
    exclude_from_overview: Optional[bool] = False,
    no_uuid_field_priority: Optional[int] = -1,
    **extra_meta: Any
) -> Dict[str, Any]:
    """
    Generates metadata for json_schema_extra, supporting translation and additional metadata.

    :param may_have_translation: Boolean indicating if the field can be translated.
    :param to_be_translated_in_front: Boolean indicating if translation is required in the frontend.
    :param data_type: The data type information (e.g., {"is_string": True}).
    :param auto_generate: Boolean indicating if the field is auto-generated.
    :param generator_type: The type of generator to use (from GeneratorType Enum).
    :param custom_generator: A callable for custom generation logic.
    :return: A dictionary with all metadata for json_schema_extra.
    """
    data_type = data_type or {"is_string": True}
    return {
        "may_have_translation": may_have_translation,
        "to_be_translated_in_front": to_be_translated_in_front,
        "data_type": data_type,
        "auto_generate": auto_generate,
        "generator_type": generator_type.value if generator_type else None,
        "custom_generator": custom_generator,
        "exclude_from_head": exclude_from_head,
        "can_be_encrypted": can_be_encrypted,
        "exclude_at_all": exclude_at_all,
        "exclude_from_update_head": exclude_from_update_head,
        "exclude_from_data_table": exclude_from_data_table,
        "exclude_from_overview": exclude_from_overview,
        "extra_metas":extra_metas,
        "overview_data_type":overview_data_type,
        "no_uuid_field_priority":no_uuid_field_priority,
        **extra_meta
    }
 


  
from typing import List, Dict, Any, Optional
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.enums.type_enum import EAppGroupFlag, FormatedOutPut, OutputDataType
from app.modules.core.utils.common.helpers import extract_field_on_output_data_element
from app.modules.core.utils.helpers.line_helper import format_exception
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.ref_currency.ref_currency_model import RefCurrencyModel


class SystemCountryService:
    """
    Service for handling system country operations and related data fetching
    """

    def __init__(self,accept_language: Optional[str] = DEFAULT_LANGUAGE):
        from app.modules.core.services.generic.generic_services import GenericService
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language=accept_language)

    async def get_trans_registration_system_country(self,) -> list:
        try:

            from bson import ObjectId
            country_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
            )
            if not country_named_entity:
                return [] 

            # Start from countries, go down country → provinces → towns,
            # then verify at least one town is registered in CFG_SYSTEM_TOWN_ENTITY
            pipeline = [
                # Match only country-level entities
                {"$match": {"ref_named_entity_id": ObjectId(country_named_entity['id'])}},
                # Lookup provinces (direct children of country)
                {"$lookup": {
                    "from": f"{CollectionKey.REF_ENTITY.model_name}",
                    "localField": "_id",
                    "foreignField": "ref_entity_id",
                    "as": "provinces"
                }},
                # Collect all province IDs
                {"$addFields": {"province_ids": "$provinces._id"}},
                # Lookup towns (children of provinces)
                {"$lookup": {
                    "from": f"{CollectionKey.REF_ENTITY.model_name}",
                    "localField": "province_ids",
                    "foreignField": "ref_entity_id",
                    "as": "towns"
                }},
                # Check if any town is registered in CFG_SYSTEM_TOWN_ENTITY
                {"$lookup": {
                    "from": f"{CollectionKey.CFG_SYSTEM_TOWN_ENTITY.model_name}",
                    "localField": "towns._id",
                    "foreignField": "ref_entity_id",
                    "as": "registered_towns"
                }},
                # Keep only countries with at least one registered town
                {"$match": {"registered_towns": {"$ne": []}}},
                # Clean up helper fields
                {"$project": {"provinces": 0, "province_ids": 0, "towns": 0, "registered_towns": 0}},
            ]
            system_countries = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT,
                pipeline=pipeline,
                all_data=True,
            )
            print(f" >> system_countries >>> {system_countries}")

            # Fetch all registered towns from CFG_SYSTEM_TOWN_ENTITY
            all_registered_towns = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_SYSTEM_TOWN_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            # Build a set of registered town entity IDs for fast lookup
            registered_town_ids = {str(t.get("ref_entity_id")) for t in all_registered_towns if t.get("ref_entity_id")}
            print(f" >> registered_town_ids >>> {registered_town_ids}")

            # Fetch all named entities to use for flag filtering
            all_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            
            # Build a lookup for named_entity by id
            named_entity_lookup = {str(ent.get("id")): ent for ent in all_named_entities}
            print(f"System Countries >>>> : {system_countries}", True)
            # Build tree filtered by registered towns only
            async def build_tree_level(entity_id, level_flag, next_level_flag=None):
                try:
                    children = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___ref_entity_id": entity_id},
                        all_data=True
                    )
                    
                    if (not children or len(children) == 0) and isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                        children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___ref_entity_id": ObjectId(entity_id)},
                            all_data=True
                        )
                    
                    if not children or len(children) == 0:
                        all_entities = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                        children = [e for e in all_entities if e.get("ref_entity_id") and str(e.get("ref_entity_id")) == str(entity_id)]

                    print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                except Exception as e:
                    print(f"Error fetching children: {str(e)}", True)
                    children = []
                
                result_children = []
                
                for child in children:
                    named_entity_id = child.get("ref_named_entity_id")
                    if not named_entity_id:
                        continue
                        
                    named_entity = named_entity_lookup.get(str(named_entity_id))
                    if not named_entity:
                        continue
                    
                    child_flag = named_entity.get("named_entity_flag", "")
                    if level_flag == "province" and child_flag != "province":
                        child_flag = "province"
                    elif level_flag == "town" and child_flag != "town":
                        child_flag = "town"
                    
                    # At town level, skip towns not registered in CFG_SYSTEM_TOWN_ENTITY
                    if level_flag == "town":
                        if str(child.get("id")) not in registered_town_ids:
                            print(f"Skipping unregistered town: {child.get('name')}", True)
                            continue
                    
                    child_node = {
                        "id": str(child.get("id")),
                        "name": child.get("name"),
                        "named_entity_flag": child_flag,
                        "children": []
                    }
                    
                    if next_level_flag:
                        next_level_children = await build_tree_level(child.get("id"), next_level_flag)
                        # Prune this node if no registered towns found underneath
                        if not next_level_children or len(next_level_children) == 0:
                            print(f"Pruning {level_flag} {child.get('name')} - no registered towns underneath", True)
                            continue
                        child_node["children"] = next_level_children
                    
                    result_children.append(child_node)
                
                return result_children

            country_entity_map = {}  # Maps entity_id to system_country_id
            # Result array for trees
            result_trees = []
            
            for country in system_countries:
                # Create the country node
                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )

                telephone_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )
                map_country_codes = [{"id": c["id"], "country_code": c["country_code"]} for c in country_codes]
                map_telephone_prefixes =  [{"id": t["id"], "prefix": t["prefix"]} for t in telephone_prefixes]
                country_node = {
                    "id": country['id'],
                    "name": country['name'],
                    "country_codes":map_country_codes,
                    "min_phone_number_chars": country['min_phone_number_chars'],
                    "max_phone_number_chars": country['max_phone_number_chars'],
                    "telephone_prefixes":map_telephone_prefixes,
                    "country_flag": country['country_flag'],
                    "system_country_id": country['id'],
                    "children": []
                }

                # Get provinces (children of country)
                province_children = await build_tree_level(country['id'], "province", "town")
                country_node["children"] = province_children
                # Add to results
                result_trees.append(country_node)
 
                # Add to results
            return result_trees
        except Exception as e:
            print(f"Error fetching system countries: {str(e)}", True)
            return []
    

    async def get_drc_registration_system_country(self,application_group_flag: Optional[EAppGroupFlag] = EAppGroupFlag.COMMON) -> list:
        try:

            from bson import ObjectId
            country_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
            )
            if not country_named_entity:
                return [] 
            system_countries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__ref_named_entity_id": country_named_entity['id'],"filter__unique_flag":"rdc-country"},
                all_data=True
            )
            # Fetch all named entities to use for flag filtering
            all_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            
            # Build a lookup for named_entity by id
            named_entity_lookup = {str(ent.get("id")): ent for ent in all_named_entities}
            print(f"System Countries >>>> : {system_countries}", True)
            # Function to build a tree for a specific node level
            async def build_tree_level(entity_id, level_flag, next_level_flag=None):
                # Fetch direct children of this entity
                print(f"Fetching children for entity_id: {entity_id}", True)
                # Try multiple query approaches to find all children
                try:
                    # First, try with filter___ref_entity_id (3 underscores)
                    print(f"Querying for children with ref_entity_id: {entity_id}", True)

                    children = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___ref_entity_id": entity_id},
                        all_data=True
                    )
                    
                    # If that didn't work and ID is a string that can be an ObjectId, try that
                    if (not children or len(children) == 0) and isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                        print(f"Trying ObjectId format for ref_entity_id: {entity_id}", True)
                        children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___ref_entity_id": ObjectId(entity_id)},
                            all_data=True
                        )
                    
                    # If we still have no children, try using the full entity object approach
                    if not children or len(children) == 0:
                        print(f"Trying alternate approach to find children", True)
                        all_entities = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                        
                        # Filter entities manually
                        children = []
                        for e in all_entities:
                            ref_id = e.get("ref_entity_id")
                            if ref_id and (str(ref_id) == str(entity_id)):
                                children.append(e)
                                print(f"Found child through manual filtering: {e.get('name')}", True)
                                
                    print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                except Exception as e:
                    print(f"Error fetching children: {str(e)}", True)
                    children = []
                
                print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                
                result_children = []
                
                # Process each child
                for child in children:
                    named_entity_id = child.get("ref_named_entity_id")
                    if not named_entity_id:
                        continue
                        
                    named_entity = named_entity_lookup.get(str(named_entity_id))
                    if not named_entity:
                        continue
                    
                    # Get the named entity flag or use a default value    
                    child_flag = named_entity.get("named_entity_flag", "")
                    
                    # Log the child entity and its flag
                    print(f"Child entity: {child.get('name')}, flag: {child_flag}, expected: {level_flag}", True)
                    
                    # Always include children regardless of flag match
                    # We'll assign the expected flag based on level
                    if level_flag == "province" and child_flag != "province":
                        child_flag = "province"
                        print(f"Assigning province flag to entity {child.get('name')}", True)
                    elif level_flag == "town" and child_flag != "town":
                        child_flag = "town"
                        print(f"Assigning town flag to entity {child.get('name')}", True)
                    
                    child_node = {
                        "id": str(child.get("id")),
                        "name": child.get("name"),
                        "named_entity_flag": child_flag,
                        "children": []
                    }
                    
                    # If we need to fetch the next level
                    if next_level_flag:
                        next_level_children = await build_tree_level(child.get("id"), next_level_flag)
                        if next_level_children and len(next_level_children) > 0:
                            child_node["children"] = next_level_children
                            print(f"Added {len(next_level_children)} {next_level_flag} children to {child.get('name')}", True)
                        else:
                            # If no children found through normal means, try manual lookup for towns
                            print(f"No {next_level_flag} found for {child.get('name')}, trying manual lookup", True)
                            
                            # Look for entities that have this entity as parent
                            all_potential_children = await self.generic_service.fetch_data_from_collection(
                                collection_key=CollectionKey.REF_ENTITY,
                                output_data_type=OutputDataType.DEFAULT.value,
                                query={},
                                all_data=True
                            )
                            
                            child_id = child.get("id")
                            town_nodes = []
                            
                            for potential_child in all_potential_children:
                                parent_entity_id = potential_child.get("parent_entity_id")
                                if parent_entity_id and (str(parent_entity_id) == str(child_id)):
                                    town_node = {
                                        "id": str(potential_child.get("id")),
                                        "name": potential_child.get("name"),
                                        "named_entity_flag": next_level_flag,
                                        "children": []
                                    }
                                    town_nodes.append(town_node)
                                    print(f"Manually added {next_level_flag} {potential_child.get('name')} to {child.get('name')}", True)
                            
                            child_node["children"] = town_nodes
                    
                    result_children.append(child_node)
                
                return result_children

            country_entity_map = {}  # Maps entity_id to system_country_id
            # Result array for trees
            result_trees = []
            
            for country in system_countries:
                # Create the country node
                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )

                telephone_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )
                map_country_codes = [{"id": c["id"], "country_code": c["country_code"]} for c in country_codes]
                map_telephone_prefixes =  [{"id": t["id"], "prefix": t["prefix"]} for t in telephone_prefixes]
                country_node = {
                    "id": country['id'],
                    "name": country['name'],
                    "country_codes":map_country_codes,
                    "min_phone_number_chars": country['min_phone_number_chars'],
                    "max_phone_number_chars": country['max_phone_number_chars'],
                    "telephone_prefixes":map_telephone_prefixes,
                    "country_flag": country['country_flag'],
                    "system_country_id": country['id'],
                    "children": []
                }

                # Get provinces (children of country)
                province_children = await build_tree_level(country['id'], "province", "town")
                country_node["children"] = province_children
                # Add to results
                result_trees.append(country_node)
 
                # Add to results
            return result_trees
        except Exception as e:
            print(f"Error fetching system countries: {str(e)}", True)
            return []
    

    async def get_static_parent_entity_by_flag(
        self,
        entity_id: str,
        target_flag: str,
        max_depth: int = 10
    ) -> Optional[dict]:
        """
        Find the parent entity with a specific named entity flag by traversing
        the recursive entity relationships.
        
        Args:
            db_connection: MongoDB connection
            entity_id: Starting entity ID
            target_flag: Target named entity flag (e.g., 'country')
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            Parent entity with target flag, or None if not found
        """
        static_entity = await self.generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_ENTITY,
            output_data_type=OutputDataType.DEFAULT.value,
            query={"filter___id": entity_id}
        )
        if not static_entity:
            return None
        depth = 0
        
        while depth < max_depth:
            # Get current entity with its named entity information
            current_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": static_entity.get('ref_named_entity_id')}
            )
            if not current_named_entity:
                return None
            if current_named_entity.get("named_entity_flag") == target_flag:
                return static_entity
            
            static_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter___id": static_entity.get('ref_entity_id')}
            )
            if not static_entity:
                return None
            depth += 1
        
        # Max depth reached without finding target flag
        return None
    
    
    async def get_registration_system_country(self,application_group_flag: Optional[EAppGroupFlag] = EAppGroupFlag.COMMON) -> list:
        try:

            from bson import ObjectId
            country_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
            )
            if not country_named_entity:
                return [] 
            system_countries = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__ref_named_entity_id": country_named_entity['id']},
                all_data=True
            )
            # Fetch all named entities to use for flag filtering
            all_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            
            # Build a lookup for named_entity by id
            named_entity_lookup = {str(ent.get("id")): ent for ent in all_named_entities}
            print(f"System Countries >>>> : {system_countries}", True)
            # Function to build a tree for a specific node level
            async def build_tree_level(entity_id, level_flag, next_level_flag=None):
                # Fetch direct children of this entity
                print(f"Fetching children for entity_id: {entity_id}", True)
                # Try multiple query approaches to find all children
                try:
                    # First, try with filter___ref_entity_id (3 underscores)
                    print(f"Querying for children with ref_entity_id: {entity_id}", True)

                    children = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___ref_entity_id": entity_id},
                        all_data=True
                    )
                    
                    # If that didn't work and ID is a string that can be an ObjectId, try that
                    if (not children or len(children) == 0) and isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                        print(f"Trying ObjectId format for ref_entity_id: {entity_id}", True)
                        children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___ref_entity_id": ObjectId(entity_id)},
                            all_data=True
                        )
                    
                    # If we still have no children, try using the full entity object approach
                    if not children or len(children) == 0:
                        print(f"Trying alternate approach to find children", True)
                        all_entities = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                        
                        # Filter entities manually
                        children = []
                        for e in all_entities:
                            ref_id = e.get("ref_entity_id")
                            if ref_id and (str(ref_id) == str(entity_id)):
                                children.append(e)
                                print(f"Found child through manual filtering: {e.get('name')}", True)
                                
                    print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                except Exception as e:
                    print(f"Error fetching children: {str(e)}", True)
                    children = []
                
                print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                
                result_children = []
                
                # Process each child
                for child in children:
                    named_entity_id = child.get("ref_named_entity_id")
                    if not named_entity_id:
                        continue
                        
                    named_entity = named_entity_lookup.get(str(named_entity_id))
                    if not named_entity:
                        continue
                    
                    # Get the named entity flag or use a default value    
                    child_flag = named_entity.get("named_entity_flag", "")
                    
                    # Log the child entity and its flag
                    print(f"Child entity: {child.get('name')}, flag: {child_flag}, expected: {level_flag}", True)
                    
                    # Always include children regardless of flag match
                    # We'll assign the expected flag based on level
                    if level_flag == "province" and child_flag != "province":
                        child_flag = "province"
                        print(f"Assigning province flag to entity {child.get('name')}", True)
                    elif level_flag == "town" and child_flag != "town":
                        child_flag = "town"
                        print(f"Assigning town flag to entity {child.get('name')}", True)
                    
                    child_node = {
                        "id": str(child.get("id")),
                        "name": child.get("name"),
                        "named_entity_flag": child_flag,
                        "children": []
                    }
                    
                    # If we need to fetch the next level
                    if next_level_flag:
                        next_level_children = await build_tree_level(child.get("id"), next_level_flag)
                        if next_level_children and len(next_level_children) > 0:
                            child_node["children"] = next_level_children
                            print(f"Added {len(next_level_children)} {next_level_flag} children to {child.get('name')}", True)
                        else:
                            # If no children found through normal means, try manual lookup for towns
                            print(f"No {next_level_flag} found for {child.get('name')}, trying manual lookup", True)
                            
                            # Look for entities that have this entity as parent
                            all_potential_children = await self.generic_service.fetch_data_from_collection(
                                collection_key=CollectionKey.REF_ENTITY,
                                output_data_type=OutputDataType.DEFAULT.value,
                                query={},
                                all_data=True
                            )
                            
                            child_id = child.get("id")
                            town_nodes = []
                            
                            for potential_child in all_potential_children:
                                parent_entity_id = potential_child.get("parent_entity_id")
                                if parent_entity_id and (str(parent_entity_id) == str(child_id)):
                                    town_node = {
                                        "id": str(potential_child.get("id")),
                                        "name": potential_child.get("name"),
                                        "named_entity_flag": next_level_flag,
                                        "children": []
                                    }
                                    town_nodes.append(town_node)
                                    print(f"Manually added {next_level_flag} {potential_child.get('name')} to {child.get('name')}", True)
                            
                            child_node["children"] = town_nodes
                    
                    result_children.append(child_node)
                
                return result_children

            country_entity_map = {}  # Maps entity_id to system_country_id
            # Result array for trees
            result_trees = []
            
            for country in system_countries:
                # Create the country node
                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )

                telephone_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )
                map_country_codes = [{"id": c["id"], "country_code": c["country_code"]} for c in country_codes]
                map_telephone_prefixes =  [{"id": t["id"], "prefix": t["prefix"]} for t in telephone_prefixes]
                country_node = {
                    "id": country['id'],
                    "name": country['name'],
                    "country_codes":map_country_codes,
                    "min_phone_number_chars": country['min_phone_number_chars'],
                    "max_phone_number_chars": country['max_phone_number_chars'],
                    "telephone_prefixes":map_telephone_prefixes,
                    "country_flag": country['country_flag'],
                    "system_country_id": country['id'],
                    "children": []
                }

                # Get provinces (children of country)
                province_children = await build_tree_level(country['id'], "province", "town")
                country_node["children"] = province_children
                # Add to results
                result_trees.append(country_node)
 
                # Add to results
            return result_trees
        except Exception as e:
            print(f"Error fetching system countries: {str(e)}", True)
            return []
    
    async def get_flaged_registration_system_country(self,application_group_flag: Optional[EAppGroupFlag] = EAppGroupFlag.COMMON) -> list:
        try:

            from bson import ObjectId
            country_named_entity = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={"filter__named_entity_flag": "country"},
            )
            if not country_named_entity:
                return [] 

            # Use aggregation on REF_ENTITY to fetch only countries that exist
            # in CFG_SYSTEM_COUNTRY with the lokotroo app flag — single DB round-trip
            pipeline = [
                # Match only country-level entities
                {"$match": {"ref_named_entity_id": ObjectId(country_named_entity['id'])}},
                # Lookup into cfgSystemCountries to check if this entity is registered with lokotroo flag
                {"$lookup": {
                    "from": f"{CollectionKey.CFG_SYSTEM_COUNTRY.model_name}",
                    "let": {"entity_id": "$_id"},
                    "pipeline": [
                        {"$match": {
                            "$expr": {"$eq": ["$ref_entity_id", "$$entity_id"]},
                            "application_group_flag": application_group_flag.value,
                        }}
                    ],
                    "as": "system_country_match"
                }},
                # Keep only entities that have at least one matching CFG_SYSTEM_COUNTRY record
                {"$match": {"system_country_match": {"$ne": []}}},
                # Remove the lookup field from the output
                {"$project": {"system_country_match": 0}},
            ]
            system_countries = await self.generic_service.fetch_native_aggregate_data_from_collection(
                collection_key=CollectionKey.REF_ENTITY,
                output_data_type=OutputDataType.DEFAULT,
                pipeline=pipeline,
                all_data=True,
            )
            # Fetch all named entities to use for flag filtering
            all_named_entities = await self.generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                output_data_type=OutputDataType.DEFAULT.value,
                query={},
                all_data=True
            )
            
            # Build a lookup for named_entity by id
            named_entity_lookup = {str(ent.get("id")): ent for ent in all_named_entities}
            print(f"System Countries >>>> : {system_countries}", True)
            # Function to build a tree for a specific node level
            async def build_tree_level(entity_id, level_flag, next_level_flag=None):
                # Fetch direct children of this entity
                print(f"Fetching children for entity_id: {entity_id}", True)
                # Try multiple query approaches to find all children
                try:
                    # First, try with filter___ref_entity_id (3 underscores)
                    print(f"Querying for children with ref_entity_id: {entity_id}", True)

                    children = await self.generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType.DEFAULT.value,
                        query={"filter___ref_entity_id": entity_id},
                        all_data=True
                    )
                    
                    # If that didn't work and ID is a string that can be an ObjectId, try that
                    if (not children or len(children) == 0) and isinstance(entity_id, str) and ObjectId.is_valid(entity_id):
                        print(f"Trying ObjectId format for ref_entity_id: {entity_id}", True)
                        children = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={"filter___ref_entity_id": ObjectId(entity_id)},
                            all_data=True
                        )
                    
                    # If we still have no children, try using the full entity object approach
                    if not children or len(children) == 0:
                        print(f"Trying alternate approach to find children", True)
                        all_entities = await self.generic_service.fetch_data_from_collection(
                            collection_key=CollectionKey.REF_ENTITY,
                            output_data_type=OutputDataType.DEFAULT.value,
                            query={},
                            all_data=True
                        )
                        
                        # Filter entities manually
                        children = []
                        for e in all_entities:
                            ref_id = e.get("ref_entity_id")
                            if ref_id and (str(ref_id) == str(entity_id)):
                                children.append(e)
                                print(f"Found child through manual filtering: {e.get('name')}", True)
                                
                    print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                except Exception as e:
                    print(f"Error fetching children: {str(e)}", True)
                    children = []
                
                print(f"Found {len(children) if children else 0} children for entity_id: {entity_id}", True)
                
                result_children = []
                
                # Process each child
                for child in children:
                    named_entity_id = child.get("ref_named_entity_id")
                    if not named_entity_id:
                        continue
                        
                    named_entity = named_entity_lookup.get(str(named_entity_id))
                    if not named_entity:
                        continue
                    
                    # Get the named entity flag or use a default value    
                    child_flag = named_entity.get("named_entity_flag", "")
                    
                    # Log the child entity and its flag
                    print(f"Child entity: {child.get('name')}, flag: {child_flag}, expected: {level_flag}", True)
                    
                    # Always include children regardless of flag match
                    # We'll assign the expected flag based on level
                    if level_flag == "province" and child_flag != "province":
                        child_flag = "province"
                        print(f"Assigning province flag to entity {child.get('name')}", True)
                    elif level_flag == "town" and child_flag != "town":
                        child_flag = "town"
                        print(f"Assigning town flag to entity {child.get('name')}", True)
                    
                    child_node = {
                        "id": str(child.get("id")),
                        "name": child.get("name"),
                        "named_entity_flag": child_flag,
                        "children": []
                    }
                    
                    # If we need to fetch the next level
                    if next_level_flag:
                        next_level_children = await build_tree_level(child.get("id"), next_level_flag)
                        if next_level_children and len(next_level_children) > 0:
                            child_node["children"] = next_level_children
                            print(f"Added {len(next_level_children)} {next_level_flag} children to {child.get('name')}", True)
                        else:
                            # If no children found through normal means, try manual lookup for towns
                            print(f"No {next_level_flag} found for {child.get('name')}, trying manual lookup", True)
                            
                            # Look for entities that have this entity as parent
                            all_potential_children = await self.generic_service.fetch_data_from_collection(
                                collection_key=CollectionKey.REF_ENTITY,
                                output_data_type=OutputDataType.DEFAULT.value,
                                query={},
                                all_data=True
                            )
                            
                            child_id = child.get("id")
                            town_nodes = []
                            
                            for potential_child in all_potential_children:
                                parent_entity_id = potential_child.get("parent_entity_id")
                                if parent_entity_id and (str(parent_entity_id) == str(child_id)):
                                    town_node = {
                                        "id": str(potential_child.get("id")),
                                        "name": potential_child.get("name"),
                                        "named_entity_flag": next_level_flag,
                                        "children": []
                                    }
                                    town_nodes.append(town_node)
                                    print(f"Manually added {next_level_flag} {potential_child.get('name')} to {child.get('name')}", True)
                            
                            child_node["children"] = town_nodes
                    
                    result_children.append(child_node)
                
                return result_children

            country_entity_map = {}  # Maps entity_id to system_country_id
            # Result array for trees
            result_trees = []
            
            for country in system_countries:
                # Create the country node
                country_codes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )

                telephone_prefixes = await self.generic_service.fetch_data_from_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    output_data_type=OutputDataType.DEFAULT.value,
                    query={"filter__cfg_system_country_id": country['id']},
                    all_data=True
                )
                map_country_codes = [{"id": c["id"], "country_code": c["country_code"]} for c in country_codes]
                map_telephone_prefixes =  [{"id": t["id"], "prefix": t["prefix"]} for t in telephone_prefixes]
                country_node = {
                    "id": country['id'],
                    "name": country['name'],
                    "country_codes":map_country_codes,
                    "min_phone_number_chars": country['min_phone_number_chars'],
                    "max_phone_number_chars": country['max_phone_number_chars'],
                    "telephone_prefixes":map_telephone_prefixes,
                    "country_flag": country['country_flag'],
                    "system_country_id": country['id'],
                    "children": []
                }

                # Get provinces (children of country)
                province_children = await build_tree_level(country['id'], "province", "town")
                country_node["children"] = province_children
                # Add to results
                result_trees.append(country_node)
 
                # Add to results
            return result_trees
        except Exception as e:
            print(f"Error fetching system countries: {str(e)}", True)
            return []
    
    @staticmethod
    async def get_formatted_system_countries_with_related_data(
        system_countries: List[Dict[str, Any]],
        output_data_type: str,
        accept_language: str
    ) -> List[Dict[str, Any]]:
        """
        Static method to format system countries with all related data
        (currencies, ewallet prefixes, country codes, phone prefixes)

        Args:
            system_countries: List of system country elements
            output_data_type: Output data type for formatting
            accept_language: Language for responses

        Returns:
            List of formatted system countries with related data
        """
        try:
            generic_service = GenericService(accept_language)
            formated_system_countries = []

            for element in system_countries:
                try:
                    # Extract IDs from the system country element
                    cfg_system_country_id = extract_field_on_output_data_element(
                        element, 'id', output_data_type
                    )
                    ref_country_id = extract_field_on_output_data_element(
                        element, 'ref_country_id', output_data_type
                    )

                    # Fetch the reference country data
                    country = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_COUNTRY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter___id": ref_country_id}
                    )

                    if not country:
                        continue

                    # Fetch and format available currencies
                    formated_currencies = await SystemCountryService._get_formatted_currencies(
                        cfg_system_country_id, output_data_type, accept_language, generic_service
                    )

                    # Fetch ewallet number prefixes
                    ewallet_number_prefixes = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter__cfg_system_country_id": cfg_system_country_id}
                    )

                    # Fetch country codes
                    country_codes = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter__cfg_system_country_id": cfg_system_country_id}
                    )

                    # Fetch phone number prefixes
                    phone_number_prefixes = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter__cfg_system_country_id": cfg_system_country_id}
                    )

                    # Combine all data into formatted system country
                    formated_system_countries.append({
                        **element,
                        "ref_country": country,
                        "availlable_currencies": formated_currencies,
                        "ewallet_number_prefixes": ewallet_number_prefixes,
                        "country_codes": country_codes,
                        "phone_number_prefixes": phone_number_prefixes,
                    })

                except Exception as e:
                    error_detail = format_exception(f"Error processing system country element", e)
                    print(error_detail)  # You can replace with proper logging
                    continue

            return formated_system_countries

        except Exception as e:
            error_detail = format_exception("Error in get_formatted_system_countries_with_related_data", e)
            print(error_detail)  # You can replace with proper logging
            return []
        
    @staticmethod
    async def get_formatted_system_countries_from_ref_entity_with_related_data(
        system_countries: List[Dict[str, Any]],
        output_data_type: str,
        accept_language: str
    ) -> List[Dict[str, Any]]:
        """
        Static method to format system countries with all related data
        (currencies, ewallet prefixes, country codes, phone prefixes)

        Args:
            system_countries: List of system country elements
            output_data_type: Output data type for formatting
            accept_language: Language for responses

        Returns:
            List of formatted system countries with related data
        """
        try:
            generic_service = GenericService(accept_language)
            formated_system_countries = []

            for element in system_countries:
                try:
                    # Extract IDs from the system country element
                    cfg_system_country_id = element.get('ref_entity_id',{}).get('real_value',None) 
                    # cfg_system_country_id = extract_field_on_output_data_element(
                    #     element, 'id', output_data_type
                    # )
                    # ref_country_id = extract_field_on_output_data_element(
                    #     element, 'ref_entity_id', output_data_type
                    # )

                    # print(f"cfg_system_country_id >>>>> : {cfg_system_country_id}, ref_country_id: {cfg_system_country_id}", True)

                    # Fetch the reference country data
                    country = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_ENTITY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter___id": cfg_system_country_id}
                    )
                    # print(f"country >>>> : {country}", True)

                    if not country:
                        continue

                    # Fetch and format available currencies
                    formated_currencies = await SystemCountryService._get_formatted_currencies(
                        cfg_system_country_id, output_data_type, accept_language, generic_service
                    )

                    # Fetch ewallet number prefixes
                    ewallet_number_prefixes = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter__cfg_system_country_id": cfg_system_country_id}
                    )

                    # Fetch country codes
                    country_codes = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter__cfg_system_country_id": cfg_system_country_id}
                    )

                    # Fetch phone number prefixes
                    phone_number_prefixes = await generic_service.fetch_data_from_collection(
                        collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                        all_data=True,
                        page=0,
                        limit=100000,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter__cfg_system_country_id": cfg_system_country_id}
                    )

                    # Combine all data into formatted system country
                    formated_system_countries.append({
                        **element,
                        "ref_country": {
                            "id": country['id'],
                            "name": country['name'],
                            "country_flag": country['country_flag'],
                        },
                        "availlable_currencies": formated_currencies,
                        "ewallet_number_prefixes": ewallet_number_prefixes,
                        "country_codes": country_codes,
                        "phone_number_prefixes": phone_number_prefixes,
                    })

                except Exception as e:
                    error_detail = format_exception(f"Error processing system country element", e)
                    print(error_detail)  # You can replace with proper logging
                    continue

            return formated_system_countries

        except Exception as e:
            error_detail = format_exception("Error in get_formatted_system_countries_with_related_data", e)
            print(error_detail)  # You can replace with proper logging
            return []

    @staticmethod
    async def get_formatted_single_system_country_with_related_data(
        system_country: Dict[str, Any],
        output_data_type: str,
        accept_language: str
    ) -> Dict[str, Any]:
        """
        Static method to format a single system country with all related data
        (currencies, ewallet prefixes, country codes, phone prefixes)

        Args:
            system_country: Single system country element
            output_data_type: Output data type for formatting
            accept_language: Language for responses

        Returns:
            Formatted system country with related data, or empty dict if error
        """
        try:
            generic_service = GenericService(accept_language)

            print(f"Formatting single system country")

            # Extract IDs from the system country element
            cfg_system_country_id = extract_field_on_output_data_element(
                system_country, 'id', output_data_type
            )
            ref_country_id = extract_field_on_output_data_element(
                system_country, 'ref_country_id', output_data_type
            )

            # Fetch the reference country data
            country = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_COUNTRY,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=accept_language,
                query={"filter___id": ref_country_id}
            )

            if not country:
                print(f"Reference country not found for ID: {ref_country_id}")
                return {}

            # Fetch and format available currencies
            formated_currencies = await SystemCountryService._get_formatted_currencies(
                cfg_system_country_id, output_data_type, accept_language, generic_service
            )

            # Fetch ewallet number prefixes
            ewallet_number_prefixes = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=accept_language,
                query={"filter__cfg_system_country_id": cfg_system_country_id}
            )

            # Fetch country codes
            country_codes = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=accept_language,
                query={"filter__cfg_system_country_id": cfg_system_country_id}
            )

            # Fetch phone number prefixes
            phone_number_prefixes = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=accept_language,
                query={"filter__cfg_system_country_id": cfg_system_country_id}
            )

            # Return formatted system country with all related data
            return {
                **system_country,
                "ref_country": country,
                "availlable_currencies": formated_currencies,
                "ewallet_number_prefixes": ewallet_number_prefixes,
                "country_codes": country_codes,
                "phone_number_prefixes": phone_number_prefixes,
            }

        except Exception as e:
            error_detail = format_exception("Error in get_formatted_single_system_country_with_related_data", e)
            print(error_detail)  # You can replace with proper logging
            return {}

    @staticmethod
    async def format_system_countries(
        system_countries_data,  # Can be Dict or List[Dict]
        output_data_type: str,
        accept_language: str
    ):
        """
        Convenience static method that can handle both single system country and list of system countries

        Args:
            system_countries_data: Either a single system country dict or list of system country dicts
            output_data_type: Output data type for formatting
            accept_language: Language for responses

        Returns:
            Formatted system country(ies) - returns same type as input (Dict or List[Dict])
        """
        try:
            # Check if input is a list or single item
            if isinstance(system_countries_data, list):
                # Handle list of system countries
                return await SystemCountryService.get_formatted_system_countries_with_related_data(
                    system_countries=system_countries_data,
                    output_data_type=output_data_type,
                    accept_language=accept_language
                )
            elif isinstance(system_countries_data, dict):
                # Handle single system country
                return await SystemCountryService.get_formatted_single_system_country_with_related_data(
                    system_country=system_countries_data,
                    output_data_type=output_data_type,
                    accept_language=accept_language
                )
            else:
                # Invalid input type
                error_detail = format_exception(
                    f"Invalid input type: {type(system_countries_data)}. Expected dict or list of dicts.",
                    ValueError("Invalid input type")
                )
                print(error_detail)
                return [] if isinstance(system_countries_data, list) else {}

        except Exception as e:
            error_detail = format_exception("Error in format_system_countries", e)
            print(error_detail)  # You can replace with proper logging
            return [] if isinstance(system_countries_data, list) else {}


    @staticmethod
    async def get_entity_default_currency(
        entity_id: str,
        accept_language: str
    ) -> Optional[Dict[str, Any]]:
        try:
            generic_service = GenericService(accept_language)
            default_currencies = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                output_data_type=OutputDataType.DEFAULT.value,
                all_data=True,
                accept_language=accept_language,
                query={"filter__cfg_system_country_id": entity_id}
            )
            if len(default_currencies) == 0:
                return None
            default_currency = default_currencies[0]
            currency = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=accept_language,
                query={"filter___id": default_currency['ref_currency_id']}
            )

            if currency:
                currency = await RefCurrencyModel(**currency).get_formated_data(accept_language,FormatedOutPut.MINIMAL)

            return currency
        except Exception as e:
            error_detail = format_exception("Error in get_entity_default_currency", e)
            print(error_detail)  # You can replace with proper logging
            return None



    @staticmethod
    async def _get_formatted_currencies(
        cfg_system_country_id: str,
        output_data_type: str,
        accept_language: str,
        generic_service: GenericService
    ) -> List[Dict[str, Any]]:
        """
        Private helper method to fetch and format currencies for a system country

        Args:
            cfg_system_country_id: System country ID
            output_data_type: Output data type for formatting
            accept_language: Language for responses
            generic_service: Generic service instance

        Returns:
            List of formatted currencies with reference currency data
        """
        try:
            formated_currencies = []

            # Fetch available currencies for the system country
            list_of_availlable_currencies = await generic_service.fetch_data_from_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                all_data=True,
                page=0,
                limit=100000,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=accept_language,
                query={"filter__cfg_system_country_id": str(cfg_system_country_id)}
            )

            # Process each currency
            for currency in list_of_availlable_currencies:
                try:
                    ref_currency_id = currency.get('ref_currency_id',{}).get('real_value',None) # extract_field_on_output_data_element(
                        # currency, 'ref_currency_id', output_data_type
                    # )

                    # Fetch the reference currency data
                    currency_data = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_CURRENCY,
                        output_data_type=OutputDataType(output_data_type).value,
                        accept_language=accept_language,
                        query={"filter___id": ref_currency_id}
                    )

                    if not currency_data:
                        continue

                    # Add the reference currency data to the currency object
                    formated_currencies.append({
                        **currency,
                        "ref_currency": {
                            "id": currency_data.get('id',{}),
                            "name": currency_data.get('name',{}),
                            "code": currency_data.get('code',{}),
                            "symbol": currency_data.get('symbol',{})
                        }
                    })

                except Exception as e:
                    error_detail = format_exception(f"Error processing currency", e)
                    print(error_detail)  # You can replace with proper logging
                    continue

            return formated_currencies

        except Exception as e:
            error_detail = format_exception("Error in _get_formatted_currencies", e)
            print(error_detail)  # You can replace with proper logging
            return []




            
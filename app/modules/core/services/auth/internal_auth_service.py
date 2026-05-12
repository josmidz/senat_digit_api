"""
Module for internal authentication services.

This module provides services for internal authentication without requiring
user interaction, primarily for scheduled tasks and system operations.
"""

import logging
import os
from typing import Dict, Any, Optional

from app.modules.core.enums.profiles_enum import ESysProfileFlag
from app.modules.core.enums.type_enum import OutputDataType
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService

logger = logging.getLogger(__name__)

class InternalAuthService:
    """
    Service for internal authentication operations.
    
    This service provides methods for authenticating internal system
    operations, such as scheduled tasks, without requiring user interaction.
    """
    
    def __init__(self):
        """Initialize the internal authentication service."""
        pass
        
    async def get_system_user(self) -> Optional[Dict[str, Any]]:
        """
        Get a system user for internal operations.
        
        Returns:
            Dict[str, Any]: A dictionary containing user information for the system user,
                           or None if the system user could not be retrieved.
        """
        try:
            # import generic service
            from app.modules.core.services.generic.generic_services import GenericService
            generic_service = GenericService()
            # Retriev system profile
            system_profil = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type = OutputDataType.DEFAULT,
                query={
                    "filter__flag": ESysProfileFlag.SYSTEM_PROFIL.value,
                    "filter__system_reserved_actions":True,
                }
            ) 
            # Create a system user with admin privileges for internal operations
            if not system_profil:
                DebugService.app_debug_print(f"\n\n[ INTERNAL_AUTH_SERVICE ] System profile not found for internal auth service.\n\n",True)
                return None
            system_org = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__rbac_profile_id":system_profil['id'],
                }, 
            )
            if not system_org:
                DebugService.app_debug_print(f"\n\n[ INTERNAL_AUTH_SERVICE ] System organization not found for system profile.\n\n",True)
                return None
            default_role = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    "filter__is_default":True,
                    "filter__rbac_profile_id":system_org['rbac_profile_id'],
                }, 
            )
            if not default_role:
                # debug
                DebugService.app_debug_print(f"\n\n[ INTERNAL_AUTH_SERVICE ] Default role not found for system organization.\n\n",True)
                return None
            
            # system_user by role
            system_user = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT.value,
                query={
                    # "filter__is_system_user":True,
                    "filter__sys_organization_id":system_org['id'],
                    "filter__rbac_role_id":default_role['id'],
                }, 
            )
            if system_user:
                return {
                    "id": system_user['id'],
                    "username": system_user['username'],
                    "email": system_user['email'],
                    "phone_number": system_user['phone_number'],
                    "is_system_user": True,
                    "sys_organization_id": system_user['sys_organization_id']
                }
            else: 
                DebugService.app_debug_print(f"\n\n [ INTERNAL_AUTH_SERVICE ] System user not found for system organization and role.\n\n",True)
                return None
            
        except Exception as e:
            DebugService.app_debug_print(f"\n\n [ INTERNAL_AUTH_SERVICE ] Error retrieving system user: {str(e)}\n\n",True)
            return None
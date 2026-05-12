from typing import Optional

from fastapi import HTTPException, Request, status

from app.modules.auth.enums.common import MessageCategory
from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.enums.type_enum import FormatedOutPut, OutputDataType
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.converter.converter_service import ConverterService
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse
from app.modules.security.models.cfg_rls_setup.cfg_rls_setup_model import CfgRlsSetupModel
from app.modules.security.models.cfg_sudo_action_setup.cfg_sudo_action_setup_model import CfgSudoActionSetupModel


class SecuritySettingsController(DebugService, ResponseService, ConverterService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        self.generic_service = GenericService(accept_language)
        super().__init__(accept_language)

    # ─── FETCH RLS SETTINGS ───────────────────────────────────────────────────

    async def fetch_rls_settings(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
    ):
        """
        Fetch the RLS (Row-Level Security) configuration for the current organization.
        Returns a single CfgRlsSetupModel document scoped to sys_organization_id.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_RLS_SETUP,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": str(user_details['sys_organization_id'])},
                user=user_details,
            )

            self.app_debug_print(f" \n\n data fetch_rls_settings: {data}\n\n",True)

            if not data:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)
            data_instance = CfgRlsSetupModel(**data)
            data = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "RLS settings fetched successfully",
                    "data": data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── PATCH RLS PROTECTION SETTINGS ──────────────────────────────────────────

    async def patch_rls_protection_settings(
        self,
        request: Request,
        body: dict,
    ):
        """
        Update the RLS protection (is_enabled) setting for the current organization.
        Expects body: { "is_enabled": bool }
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            is_enabled = body.get("is_enabled")
            if is_enabled is None:
                raise HTTPException(status_code=400, detail="is_enabled field is required.")

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_RLS_SETUP,
                output_data_type="default",
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            if not data:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

            data_instance = CfgRlsSetupModel(**data)
            data_instance.is_enabled = bool(is_enabled)
            await data_instance.save()

            formatted_data = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "RLS protection settings updated successfully",
                    "data": formatted_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── PATCH RLS STRICT SETTINGS ────────────────────────────────────────────

    async def patch_rls_strict_settings(
        self,
        request: Request,
        body: dict,
    ):
        """
        Update the RLS strict mode setting for the current organization.
        Expects body: { "is_strict_mode": bool }
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            is_strict_mode = body.get("is_strict_mode")
            if is_strict_mode is None:
                raise HTTPException(status_code=400, detail="is_strict_mode field is required.")

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_RLS_SETUP,
                output_data_type="default",
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            if not data:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

            data_instance = CfgRlsSetupModel(**data)
            data_instance.is_strict_mode = bool(is_strict_mode)
            await data_instance.save()

            formatted_data = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "RLS strict settings updated successfully",
                    "data": formatted_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── PATCH SUDO ACTION SETTINGS ──────────────────────────────────────────

    async def patch_sudo_action_settings(
        self,
        request: Request,
        body: dict,
    ):
        """
        Update the sudo action (is_enabled) setting for the current organization.
        Expects body: { "is_enabled": bool }
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            org_id = str(user_details['sys_organization_id'])

            is_enabled = body.get("is_enabled")
            if is_enabled is None:
                raise HTTPException(status_code=400, detail="is_enabled field is required.")

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
                output_data_type="default",
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": org_id},
                user=user_details,
            )

            if not data:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)

            data_instance = CfgSudoActionSetupModel(**data)
            data_instance.is_enabled = bool(is_enabled)
            await data_instance.save()

            formatted_data = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Sudo action settings updated successfully",
                    "data": formatted_data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # ─── FETCH SUDO ACTION SETTINGS ──────────────────────────────────────────

    async def fetch_sudo_action_settings(
        self,
        request: Request,
        output_data_type: Optional[OutputDataType] = OutputDataType.DEFAULT,
    ):
        """
        Fetch the sudo action configuration for the current organization.
        Returns a single CfgSudoActionSetupModel document scoped to sys_organization_id.
        """
        try:
            user_details = await self.get_user_info(request, self.accept_language)

            self.app_debug_print(f" \n\n user_details fetch_sudo_action_settings: {user_details['sys_organization_id']}\n\n",True)

            data = await self.generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.CFG_SUDO_ACTION_SETUP,
                output_data_type=OutputDataType(output_data_type).value,
                accept_language=self.accept_language,
                query={"filter__sys_organization_id": str(user_details['sys_organization_id'])},
                user=user_details,
            )

            self.app_debug_print(f" \n\n data fetch_sudo_action_settings: {data}\n\n",True)

            if not data:
                message = self.get_response_message(
                    MessageCategory.EXCEPTIONS, "NO_DATA_FOUND", self.accept_language
                )
                raise HTTPException(status_code=404, detail=message)
            data_instance = CfgSudoActionSetupModel(**data)
            data = await data_instance.get_formated_data(self.accept_language, output=FormatedOutPut.MINIMAL)

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Sudo action settings fetched successfully",
                    "data": data,
                },
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Access to this collection is not allowed.")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")

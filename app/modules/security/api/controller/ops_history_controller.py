# app/modules/security/api/controller/ops_history_controller.py
"""
Controller for OPS update / delete history endpoints.
Follows the same pattern as RlsOverviewController.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status

from app.modules.auth.services.authenticated.authenticated_service import AuthenticatedService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.history.ops_history_service import OpsHistoryService
from app.modules.core.services.response.response_service import ResponseService
from app.modules.core.types.response import CustomJSONResponse


class OpsHistoryController(DebugService, ResponseService, AuthenticatedService):
    def __init__(self, accept_language: Optional[str] = DEFAULT_LANGUAGE):
        self.accept_language = accept_language
        super().__init__(accept_language)

    # ─── PAGINATED UPDATE HISTORY ─────────────────────────────────────────

    async def fetch_update_history(
        self,
        request: Request,
        collection_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        """Return paginated update history, optionally filtered by collection_name."""
        try:
            await self.get_user_info(request, self.accept_language)

            data = await OpsHistoryService.get_update_history_paginated(
                collection_name=collection_name,
                skip=skip,
                limit=limit,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Update history fetched successfully",
                    "data": data,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    # ─── PAGINATED DELETE HISTORY ─────────────────────────────────────────

    async def fetch_delete_history(
        self,
        request: Request,
        collection_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        """Return paginated delete history, optionally filtered by collection_name."""
        try:
            await self.get_user_info(request, self.accept_language)

            data = await OpsHistoryService.get_delete_history_paginated(
                collection_name=collection_name,
                skip=skip,
                limit=limit,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Delete history fetched successfully",
                    "data": data,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    # ─── SEARCH HISTORY BY IDENTIFIER ────────────────────────────────────

    async def search_history_by_identifier(
        self,
        request: Request,
        identifier: str,
        history_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        """Search update and/or delete history by document_identifier or document_id."""
        try:
            await self.get_user_info(request, self.accept_language)

            data = await OpsHistoryService.search_history_by_identifier(
                identifier=identifier,
                history_type=history_type,
                skip=skip,
                limit=limit,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "History search completed",
                    "data": data,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    # ─── FETCH HISTORIES FOR IDENTIFIER (update + delete) ────────────────

    async def fetch_histories_for_identifier(
        self,
        request: Request,
        collection_name: str,
        identifier: str,
        skip: int = 0,
        limit: int = 50,
    ):
        """Fetch both update and delete histories for a specific identifier within a collection."""
        try:
            await self.get_user_info(request, self.accept_language)

            data = await OpsHistoryService.get_histories_for_identifier(
                collection_name=collection_name,
                identifier=identifier,
                skip=skip,
                limit=limit,
            )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Histories for identifier fetched successfully",
                    "data": data,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    # ─── RESTORE FROM DELETE HISTORY ──────────────────────────────────────

    async def restore_from_delete_history(
        self,
        request: Request,
        history_entry_id: str,
    ):
        """Restore a previously deleted document from its delete-history snapshot."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = str(user_details.get("_id", "")) if user_details else None

            restored = await OpsHistoryService.restore_from_delete_history(
                history_entry_id=history_entry_id,
                restored_by_user_id=user_id,
            )

            if restored is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Delete history entry not found or already restored.",
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Document restored successfully from delete history",
                    "data": restored,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    # ─── RESTORE FROM UPDATE HISTORY (REVERT) ─────────────────────────────

    async def restore_from_update_history(
        self,
        request: Request,
        history_entry_id: str,
    ):
        """Revert a document to its previous state using an update-history snapshot."""
        try:
            user_details = await self.get_user_info(request, self.accept_language)
            user_id = str(user_details.get("_id", "")) if user_details else None

            reverted = await OpsHistoryService.restore_from_update_history(
                history_entry_id=history_entry_id,
                restored_by_user_id=user_id,
            )

            if reverted is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Update history entry not found, already reverted, or document no longer exists.",
                )

            return CustomJSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Document reverted successfully from update history",
                    "data": reverted,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

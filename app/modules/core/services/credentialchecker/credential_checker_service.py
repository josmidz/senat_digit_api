"""
Credential Checker Service.

This service provides methods to check if an email or phone number 
is already in use across all platforms (SysUserModel, OpsEWalletModel, SysOrganizationModel).
This ensures unique credentials across the entire system.
"""

from typing import Optional, Dict, Any, List
from beanie import PydanticObjectId
from bson import ObjectId

from app.modules.core.services.debug.debug_service import DebugService


class CredentialCheckerService:
    """
    Service to check credential uniqueness across multiple models.
    
    Checks for email and phone number uniqueness in:
    - SysUserModel (user accounts)
    - SysOrganizationModel (organizations)
    """

    @staticmethod
    async def is_email_taken(
        email: str, 
        exclude_user_id: Optional[PydanticObjectId] = None,
        exclude_organization_id: Optional[PydanticObjectId] = None
    ) -> Dict[str, Any]:
        """
        Check if an email is already taken across all platforms.
        
        Args:
            email: The email address to check.
            exclude_user_id: Optional user ID to exclude from the check (for updates).
            exclude_organization_id: Optional organization ID to exclude from the check (for updates).
            
        Returns:
            Dict containing:
                - is_taken: bool - Whether the email is already in use
                - found_in: List[str] - List of models where the email was found
                - details: Dict - Detailed information about where the email was found
        """
        from app.modules.core.models.sys_user.sys_user_model import SysUserModel
        from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
        
        if not email or not email.strip():
            return {
                "is_taken": False,
                "found_in": [],
                "details": {}
            }
        
        email = email.strip().lower()
        found_in: List[str] = []
        details: Dict[str, Any] = {}
        
        # Check in SysUserModel - main email field
        user_query = {"email": {"$regex": f"^{email}$", "$options": "i"}}
        if exclude_user_id:
            user_query["_id"] = {"$ne": ObjectId(str(exclude_user_id))}
        
        user_with_email = await SysUserModel.find_one(user_query)
        if user_with_email:
            found_in.append("SysUserModel")
            details["SysUserModel"] = {
                "id": str(user_with_email.id),
                "field": "email",
                "value": user_with_email.email
            }
        
        # Check in SysUserModel - emails array field
        if not user_with_email:
            user_emails_query = {"emails.email": {"$regex": f"^{email}$", "$options": "i"}}
            if exclude_user_id:
                user_emails_query["_id"] = {"$ne": ObjectId(str(exclude_user_id))}
            
            user_with_emails_array = await SysUserModel.find_one(user_emails_query)
            if user_with_emails_array:
                found_in.append("SysUserModel")
                details["SysUserModel"] = {
                    "id": str(user_with_emails_array.id),
                    "field": "emails",
                    "value": email
                }
         
        # Check in SysOrganizationModel - emails array field
        org_query = {"emails.email": {"$regex": f"^{email}$", "$options": "i"}}
        if exclude_organization_id:
            org_query["_id"] = {"$ne": ObjectId(str(exclude_organization_id))}
        
        org_with_email = await SysOrganizationModel.find_one(org_query)
        if org_with_email:
            found_in.append("SysOrganizationModel")
            details["SysOrganizationModel"] = {
                "id": str(org_with_email.id),
                "field": "emails",
                "value": email
            }
        
        return {
            "is_taken": len(found_in) > 0,
            "found_in": found_in,
            "details": details
        }

    @staticmethod
    async def is_phone_number_taken(
        phone_number: str,
        exclude_user_id: Optional[PydanticObjectId] = None,
        exclude_organization_id: Optional[PydanticObjectId] = None
    ) -> Dict[str, Any]:
        """
        Check if a phone number is already taken across all platforms.
        
        Args:
            phone_number: The phone number to check.
            exclude_user_id: Optional user ID to exclude from the check (for updates).
            exclude_organization_id: Optional organization ID to exclude from the check (for updates).
            
        Returns:
            Dict containing:
                - is_taken: bool - Whether the phone number is already in use
                - found_in: List[str] - List of models where the phone number was found
                - details: Dict - Detailed information about where the phone number was found
        """
        from app.modules.core.models.sys_user.sys_user_model import SysUserModel
        from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
        
        if not phone_number or not phone_number.strip():
            return {
                "is_taken": False,
                "found_in": [],
                "details": {}
            }
        
        # Normalize phone number - remove spaces and common formatting
        phone_number = phone_number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        found_in: List[str] = []
        details: Dict[str, Any] = {}
        
        # Check in SysUserModel - main phone_number field
        user_query = {"username": phone_number}
        if exclude_user_id:
            user_query["_id"] = {"$ne": ObjectId(str(exclude_user_id))}
        
        user_with_phone = await SysUserModel.find_one(user_query)
        if user_with_phone:
            found_in.append("SysUserModel")
            details["SysUserModel"] = {
                "id": str(user_with_phone.id),
                "field": "username",
                "value": user_with_phone.username
            }
        
        # # Check in SysUserModel - phone_numbers array field
        # if not user_with_phone:
        #     user_phones_query = {"phone_numbers.phone_number": phone_number}
        #     if exclude_user_id:
        #         user_phones_query["_id"] = {"$ne": ObjectId(str(exclude_user_id))}
            
        #     user_with_phones_array = await SysUserModel.find_one(user_phones_query)
        #     if user_with_phones_array:
        #         found_in.append("SysUserModel")
        #         details["SysUserModel"] = {
        #             "id": str(user_with_phones_array.id),
        #             "field": "phone_numbers",
        #             "value": phone_number
        #         }
        
        # # Check in SysOrganizationModel - phone_numbers array field
        # org_query = {"phone_numbers.phone_number": phone_number}
        # if exclude_organization_id:
        #     org_query["_id"] = {"$ne": ObjectId(str(exclude_organization_id))}
        
        # org_with_phone = await SysOrganizationModel.find_one(org_query)
        # if org_with_phone:
        #     found_in.append("SysOrganizationModel")
        #     details["SysOrganizationModel"] = {
        #         "id": str(org_with_phone.id),
        #         "field": "phone_numbers",
        #         "value": phone_number
        #     }
        
        return {
            "is_taken": len(found_in) > 0,
            "found_in": found_in,
            "details": details
        }

    @staticmethod
    async def check_credentials(
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        exclude_organization_id: Optional[PydanticObjectId] = None
    ) -> Dict[str, Any]:
        """
        Check if both email and phone number are available.
        
        Args:
            email: The email address to check.
            phone_number: The phone number to check.
            exclude_organization_id: Optional organization ID to exclude from the check (for updates).
            
        Returns:
            Dict containing:
                - is_available: bool - True if both credentials are available
                - email_check: Dict - Result of email check
                - phone_check: Dict - Result of phone number check
        """
        email_result = {"is_taken": False, "found_in": [], "details": {}}
        phone_result = {"is_taken": False, "found_in": [], "details": {}}
        
        if email:
            email_result = await CredentialCheckerService.is_email_taken(
                email=email,
                exclude_organization_id=exclude_organization_id
            )
        
        if phone_number:
            phone_result = await CredentialCheckerService.is_phone_number_taken(
                phone_number=phone_number,
                exclude_organization_id=exclude_organization_id
            )
        
        is_available = not email_result["is_taken"] and not phone_result["is_taken"]
        
        return {
            "is_available": is_available,
            "email_check": email_result,
            "phone_check": phone_result
        }

    @staticmethod
    async def validate_credentials_for_registration(
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate credentials for a new registration.
        Raises an error description if credentials are already taken.
        
        Args:
            email: The email address to check.
            phone_number: The phone number to check.
            
        Returns:
            Dict containing:
                - is_valid: bool - True if credentials are valid for registration
                - errors: List[str] - List of error messages if not valid
        """
        result = await CredentialCheckerService.check_credentials(
            email=email,
            phone_number=phone_number
        )
        
        errors: List[str] = []
        
        if result["email_check"]["is_taken"]:
            errors.append(f"Email '{email}' is already registered in the system")
        
        if result["phone_check"]["is_taken"]:
            errors.append(f"Phone number '{phone_number}' is already registered in the system")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "details": result
        }

    @staticmethod
    async def validate_credentials_for_user_update(
        user_id: PydanticObjectId,
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate credentials for updating an existing user.
        Excludes the user's own credentials from the check.
        
        Args:
            user_id: The ID of the user being updated.
            email: The new email address to check.
            phone_number: The new phone number to check.
            
        Returns:
            Dict containing:
                - is_valid: bool - True if credentials are valid for update
                - errors: List[str] - List of error messages if not valid
        """
        result = await CredentialCheckerService.check_credentials(
            email=email,
            phone_number=phone_number,
            exclude_user_id=user_id
        )
        
        errors: List[str] = []
        
        if result["email_check"]["is_taken"]:
            errors.append(f"Email '{email}' is already registered by another user")
        
        if result["phone_check"]["is_taken"]:
            errors.append(f"Phone number '{phone_number}' is already registered by another user")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "details": result
        }
   
    @staticmethod
    async def validate_credentials_for_organization_update(
        organization_id: PydanticObjectId,
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate credentials for updating an existing organization.
        Excludes the organization's own credentials from the check.
        
        Args:
            organization_id: The ID of the organization being updated.
            email: The new email address to check.
            phone_number: The new phone number to check.
            
        Returns:
            Dict containing:
                - is_valid: bool - True if credentials are valid for update
                - errors: List[str] - List of error messages if not valid
        """
        result = await CredentialCheckerService.check_credentials(
            email=email,
            phone_number=phone_number,
            exclude_organization_id=organization_id
        )
        
        errors: List[str] = []
        
        if result["email_check"]["is_taken"]:
            errors.append(f"Email '{email}' is already registered by another organization")
        
        if result["phone_check"]["is_taken"]:
            errors.append(f"Phone number '{phone_number}' is already registered by another organization")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "details": result
        }

    @staticmethod
    async def find_entity_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Find which entity (user, ewallet, or organization) owns an email.
        
        Args:
            email: The email address to search for.
            
        Returns:
            Dict containing entity type and details, or None if not found.
        """
        result = await CredentialCheckerService.is_email_taken(email=email)
        
        if not result["is_taken"]:
            return None
        
        return {
            "found_in": result["found_in"],
            "details": result["details"]
        }

    @staticmethod
    async def find_entity_by_phone_number(phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Find which entity (user, ewallet, or organization) owns a phone number.
        
        Args:
            phone_number: The phone number to search for.
            
        Returns:
            Dict containing entity type and details, or None if not found.
        """
        result = await CredentialCheckerService.is_phone_number_taken(phone_number=phone_number)
        
        if not result["is_taken"]:
            return None
        
        return {
            "found_in": result["found_in"],
            "details": result["details"]
        }

    @staticmethod
    async def find_all_usages(
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find ALL places where an email and/or phone number is used across all platforms.
        Unlike other methods, this returns comprehensive results from ALL models.
        
        Args:
            email: The email address to search for.
            phone_number: The phone number to search for.
            
        Returns:
            Dict containing:
                - total_usages: int - Total number of usages found
                - email_usages: Dict - All places where the email is used
                - phone_usages: Dict - All places where the phone number is used
                - summary: List[Dict] - Summary of all usages with entity details
        """
        from app.modules.core.models.sys_user.sys_user_model import SysUserModel
        from app.modules.core.models.sys_organization.sys_organization_model import SysOrganizationModel
        
        email_usages: Dict[str, List[Dict[str, Any]]] = {
            "sys_user": [],
            "sys_organization": []
        }
        phone_usages: Dict[str, List[Dict[str, Any]]] = {
            "sys_user": [],
            "sys_organization": []
        }
        summary: List[Dict[str, Any]] = []
        
        # Normalize inputs
        if email:
            email = email.strip().lower()
        if phone_number:
            phone_number = phone_number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # ==================== EMAIL CHECKS ====================
        if email:
            # Check SysUserModel - main email field
            users_with_email = await SysUserModel.find(
                {"email": {"$regex": f"^{email}$", "$options": "i"}}
            ).to_list()
            for user in users_with_email:
                usage = {
                    "id": str(user.id),
                    "entity_type": "SysUser",
                    "field": "email",
                    "value": user.email,
                    "name": f"{user.first_name} {user.last_name}".strip()
                }
                email_usages["sys_user"].append(usage)
                summary.append({**usage, "credential_type": "email"})
            
            # Check SysUserModel - emails array field
            users_with_emails_array = await SysUserModel.find(
                {"emails.email": {"$regex": f"^{email}$", "$options": "i"}}
            ).to_list()
            for user in users_with_emails_array:
                # Avoid duplicates if already found in main email
                if not any(u["id"] == str(user.id) for u in email_usages["sys_user"]):
                    usage = {
                        "id": str(user.id),
                        "entity_type": "SysUser",
                        "field": "emails",
                        "value": email,
                        "name": f"{user.first_name} {user.last_name}".strip()
                    }
                    email_usages["sys_user"].append(usage)
                    summary.append({**usage, "credential_type": "email"})
            
            # Check SysOrganizationModel - emails array field
            orgs_with_email = await SysOrganizationModel.find(
                {"emails.email": {"$regex": f"^{email}$", "$options": "i"}}
            ).to_list()
            for org in orgs_with_email:
                usage = {
                    "id": str(org.id),
                    "entity_type": "SysOrganization",
                    "field": "emails",
                    "value": email,
                    "name": org.name
                }
                email_usages["sys_organization"].append(usage)
                summary.append({**usage, "credential_type": "email"})
        
        # ==================== PHONE NUMBER CHECKS ====================
        if phone_number:
            # Check SysUserModel - main phone_number field
            users_with_phone = await SysUserModel.find(
                {"phone_number": phone_number}
            ).to_list()
            for user in users_with_phone:
                usage = {
                    "id": str(user.id),
                    "entity_type": "SysUser",
                    "field": "phone_number",
                    "value": user.phone_number,
                    "name": f"{user.first_name} {user.last_name}".strip()
                }
                phone_usages["sys_user"].append(usage)
                summary.append({**usage, "credential_type": "phone_number"})
            
            # Check SysUserModel - phone_numbers array field
            users_with_phones_array = await SysUserModel.find(
                {"phone_numbers.phone_number": phone_number}
            ).to_list()
            for user in users_with_phones_array:
                # Avoid duplicates if already found in main phone_number
                if not any(u["id"] == str(user.id) for u in phone_usages["sys_user"]):
                    usage = {
                        "id": str(user.id),
                        "entity_type": "SysUser",
                        "field": "phone_numbers",
                        "value": phone_number,
                        "name": f"{user.first_name} {user.last_name}".strip()
                    }
                    phone_usages["sys_user"].append(usage)
                    summary.append({**usage, "credential_type": "phone_number"})
            
           
            
            # Check SysOrganizationModel - phone_numbers array field
            orgs_with_phone = await SysOrganizationModel.find(
                {"phone_numbers.phone_number": phone_number}
            ).to_list()
            for org in orgs_with_phone:
                usage = {
                    "id": str(org.id),
                    "entity_type": "SysOrganization",
                    "field": "phone_numbers",
                    "value": phone_number,
                    "name": org.name
                }
                phone_usages["sys_organization"].append(usage)
                summary.append({**usage, "credential_type": "phone_number"})
        
        # Calculate totals
        total_email_usages = sum(len(usages) for usages in email_usages.values())
        total_phone_usages = sum(len(usages) for usages in phone_usages.values())
        
        return {
            "total_usages": total_email_usages + total_phone_usages,
            "email_usages": {
                "total": total_email_usages,
                "by_entity": email_usages
            },
            "phone_usages": {
                "total": total_phone_usages,
                "by_entity": phone_usages
            },
            "summary": summary
        }

    @staticmethod
    async def find_all_email_usages(email: str) -> Dict[str, Any]:
        """
        Find ALL places where an email is used across all platforms.
        
        Args:
            email: The email address to search for.
            
        Returns:
            Dict containing all usages of the email.
        """
        result = await CredentialCheckerService.find_all_usages(email=email)
        return {
            "email": email,
            "total_usages": result["email_usages"]["total"],
            "usages": result["email_usages"]["by_entity"],
            "summary": [s for s in result["summary"] if s["credential_type"] == "email"]
        }

    @staticmethod
    async def find_all_phone_usages(phone_number: str) -> Dict[str, Any]:
        """
        Find ALL places where a phone number is used across all platforms.
        
        Args:
            phone_number: The phone number to search for.
            
        Returns:
            Dict containing all usages of the phone number.
        """
        result = await CredentialCheckerService.find_all_usages(phone_number=phone_number)
        return {
            "phone_number": phone_number,
            "total_usages": result["phone_usages"]["total"],
            "usages": result["phone_usages"]["by_entity"],
            "summary": [s for s in result["summary"] if s["credential_type"] == "phone_number"]
        }

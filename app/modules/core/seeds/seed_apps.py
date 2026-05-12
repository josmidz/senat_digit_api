# scripts/seed.py

import asyncio
from datetime import datetime
from typing import Optional
from app.modules.auth.enums.mfa import EMfaPurpose, MFaFlag
from app.db.session import init_db
from app.modules.core.enums.type_enum import AccountStatusFlag, EAppGroupFlag, ENotificationChannelFlag, ENotificationTunnelFlag, EWalletType, OutputDataType
from app.modules.core.utils.common.helpers import generate_label_to_flag
import nest_asyncio
from app.modules.core.configs.config import settings
from app.modules.auth.enums.common import EIconFlag
from app.modules.auth.services.password.password_service import PasswordService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.core.models.mapping_keys import CollectionKey
from app.modules.core.services.debug.debug_service import DebugService
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.services.hash.hash_service import HashService
from app.modules.core.services.icon.svg_icon_service import SvgIconService
from app.modules.core.seeds.core_rbac_app import get_core_sys_apps_db
from app.modules.core.seeds.standalone_menus import get_static_sys_standalone_menu_db
from app.modules.core.enums.api_consumers import EApiConsumerFlag
from app.modules.core.enums.profiles_enum import ESysProfilSuperUserRoleFlag, ESysProfileFlag


# Prevents loop errors by allowing re-entry into the same event loop
nest_asyncio.apply()


tracked_id = None
# Seed Data


async def init_data():
    """
    Initialize the database and seed default data.
    """
    await init_db()
    await create_auth_question_response_category()
    # await create_named_entities()
    await create_org_charts()
    await create_currencies()
    await seed_named_entities()  # Must run before seed_drc_geo_hierarchy
    await seed_drc_geo_hierarchy()
    await create_api_consumers()
    await create_profiles()
    await create_mfas()
    await create_app_group()
    # Apps catalogue must come AFTER api_consumers + profiles + app_group:
    # each app row references all three by flag, and create_default_application
    # resolves them at insertion time. Without this call, sysApps stays empty
    # and the Flutter shell renders no bottom-nav tabs after login.
    await create_default_application()
    # Senat-Digit module RBAC (rbac_endpoint + rbac_permission +
    # rbac_permission_target) and the role grants that satisfy
    # `permission_check_middleware`. Without these two steps every URL
    # gets a 403 because the middleware's permission aggregation finds
    # no rows linking the caller's role to the requested URL.
    await seed_senat_digit_modules_rbac()
    await create_default_notification_tunnels()
    await create_default_notification_channels()
    await seed_telephone_networks()
    await upsert_cities()


async def create_organization(ref_entity_id: str):
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default system organization.
    """
    # Find the system profile
    profil = await generic_service.fetch_one_from_collection(
        collection_key=CollectionKey.RBAC_PROFILE,
        output_data_type=OutputDataType.DEFAULT,
        query={
            "filter__flag": ESysProfileFlag.SYSTEM_PROFIL.value
        }
    )
    print(f"System profil: {profil}", True)
    if not profil:
        print("System profil not found. Skipping organization creation.", True)
        return

    new_organization = {
        "name": "System organisation",
        "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
        "is_default": True,
        "rbac_profile_id": profil['id'],
        "ref_entity_id": ref_entity_id,
        "phone_numbers": [{"phone_number": "243831642022"}],
        "emails": [{"email": "dev.senatdigit@example.com"}],
        "others": [],
        "address": "10 Mango, Ngaliema, Kinshasa, R.D. Congo, 10101",
        "contact_person": {
            "first_name": "System",
            "last_name": "System",
            "gender": "m",
            "email": "dev.senatdigit@example.com",
            "phone_number": "243831642022",
        }
    }
    # create only if env is local
    if settings.ENV == "local" or settings.ENV == "development":
        test_profil = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_PROFILE,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__flag": ESysProfileFlag.TEST_SYS_PROFIL.value
            }
        )
        new_test_org = {
            "name": "Test organization",
            "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
            "is_default": True,
            "rbac_profile_id": test_profil['id'],
            "ref_entity_id": ref_entity_id,
            "phone_numbers": [{"phone_number": "243818181818"}],
            "emails": [{"email": "test@test.com"}],
            "others": [],
            "address": "123 Main St",
            "contact_person": {
                "first_name": "test",
                "last_name": "test",
                "gender": "m",
                "email": "test@test.com",
                "phone_number": "243818181818",
            }

        }
        result_test_org = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.SYS_ORGANIZATION,
            filter_data={
                "flag": new_test_org['flag'], 'rbac_profile_id': new_test_org['rbac_profile_id']},
            update_data=new_test_org
        )
        org_saved_test_item_id = result_test_org if isinstance(
            result_test_org, str) else str(result_test_org['id'])
        print(f"Saved organization: {org_saved_test_item_id}")
        all_app_groups = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.REF_APPLICATION_GROUP,
            output_data_type=OutputDataType.DEFAULT.value,
            query={},
            all_data=True
        )
        for app_group in all_app_groups:
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                filter_data={
                    "targeted_id": org_saved_test_item_id,
                    "ref_application_group_id": app_group['id'],
                },
                update_data={
                    "targeted_id": org_saved_test_item_id,
                    "ref_application_group_id": app_group['id'],
                },
            )
        await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
            filter_data={
                "targeted_id": org_saved_test_item_id,
                "rbac_profile_id": test_profil['id']
            },
            update_data={
                "rbac_profile_id": test_profil['id'],
                "targeted_id": org_saved_test_item_id
            }
        )
    try:
        result_system = await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.SYS_ORGANIZATION,
            filter_data={
                "flag": new_organization['flag'], 'rbac_profile_id': new_organization['rbac_profile_id']},
            update_data=new_organization
        )
        org_saved_item_id = result_system if isinstance(
            result_system, str) else str(result_system['id'])
        
        # UPSERT CFG_SYSTEM_ORGANIZATION
        await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_SYSTEM_ORGANIZATION,
            filter_data={
                "sys_organization_id": org_saved_item_id
            },
            update_data={
                "sys_organization_id": org_saved_item_id
            }
        )
        await generic_service.upsert_data_to_collection(
            collection_key=CollectionKey.CFG_RELATED_SYSTEM_PROFIL,
            filter_data={
                "targeted_id": org_saved_item_id,
                "rbac_profile_id": profil['id']
            },
            update_data={
                "rbac_profile_id": profil['id'],
                "targeted_id": org_saved_item_id
            }
        )
        common_app_group = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_APPLICATION_GROUP,
            output_data_type=OutputDataType.DEFAULT.value,
            query={
                "filter__flag": EAppGroupFlag.COMMON.value
            }
        )
        if common_app_group:
            # ADD COMMON APP GROUPS
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_APPLICATION_GROUP_ACCESSIBILITY,
                filter_data={
                    "targeted_id": org_saved_item_id,
                    "ref_application_group_id": common_app_group['id'],
                },
                update_data={
                    "targeted_id": org_saved_item_id,
                    "ref_application_group_id": common_app_group['id'],
                },
            ) 
        # CREATE USERS
        await create_users()
    except ValueError as e:
        print(f"Error: {e}")
    except PermissionError as e:
        print(f"Permission Error: {e}")


async def create_users():
    try:
        generic_service = GenericService(DEFAULT_LANGUAGE)
        admin_user = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__username": settings.ADMIN_USERNAME
            }
        )
        print(f"\nAdmin user: {admin_user} \n", True)

        system_profil = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_PROFILE,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__flag": ESysProfileFlag.SYSTEM_PROFIL.value
            }
        )

        print(f"\n system_profil : {system_profil} \n", True)
        if not system_profil:
            print("No all profil found")
            return

        system_organization = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_ORGANIZATION,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__flag": ESysProfileFlag.SYSTEM_PROFIL.value
            }
        )

        print(f"\n system_organization : {system_organization} \n", True)
        if not system_organization:
            print("No system organization found")
            return

        # Check existing system default role
        existing_role = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_ROLE,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__is_default": True,
                "filter__rbac_profile_id": system_profil['id']
            }
        )

        # if env is local
        if settings.ENV == "local" or settings.ENV == "development":
            test_profil = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_PROFILE,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__flag": ESysProfileFlag.TEST_SYS_PROFIL.value
                }
            )
            print(f"\n min_fin_profil : {test_profil} \n", True)
            if not test_profil:
                print("No min_fin_profil found")
                return
            test_existing_role = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.RBAC_ROLE,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__is_default": True,
                    "filter__rbac_profile_id": test_profil['id']
                }
            )
            if not test_existing_role:
                return
            test_fin_organization = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_ORGANIZATION,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__flag": ESysProfileFlag.TEST_SYS_PROFIL.value
                }
            )
            if not test_fin_organization:
                return
            # CREATE MIN ECO NAT ADMIN USER
            test_password = PasswordService.hash_password(
                settings.TESTER_ADMIN_PASSWORD)
            test_user_data = {
                "username": settings.TESTER_ADMIN_USERNAME,
                "account_status": AccountStatusFlag.ACTIVE.value,
                "password": test_password,
                "sys_organization_id": test_fin_organization['id'],
                "email": settings.TESTER_ADMIN_EMAIL,
                "phone_number": settings.TESTER_ADMIN_PHONE_NUMBER,
                "is_default": True,
                "rbac_profile_id": test_profil['id'],
                "gender": settings.TESTER_ADMIN_GENDER,
                "first_name": settings.TESTER_ADMIN_FIRST_NAME,
                "last_name": settings.TESTER_ADMIN_LAST_NAME,
                "rbac_role_id": test_existing_role['id']
            }
            test_user = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.SYS_USER,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__username": test_user_data['username']
                }
            )
            if not test_user:
                test_user = await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.SYS_USER,
                    filter_data={"username": str(
                        test_user_data['username']).strip().lower()},
                    update_data=test_user_data
                )
            test_adm_id = test_user if  isinstance(
                test_user, str) else test_user['id']
            if test_adm_id:
                ref_totp_mfa = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_MFAS,
                    output_data_type=OutputDataType.DEFAULT,
                    query={
                        "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                    }
                )
                print(f"\n test user ref_totp_mfa : {ref_totp_mfa} \n")
                if ref_totp_mfa:
                    check_existing_cfg_user_mfa = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        output_data_type=OutputDataType.DEFAULT,
                        query={
                            "filter__sys_user_id": test_adm_id,
                            "filter__ref_mfa_id": ref_totp_mfa['id']
                        }
                    )
                    print(f"\n check_existing_cfg_user_mfa : {check_existing_cfg_user_mfa} \n", True)
                    if not check_existing_cfg_user_mfa:
                        test_user_mfa = await generic_service.add_data_to_collection(
                            collection_key=CollectionKey.CFG_USER_MFA,
                            data={
                                "sys_user_id": test_adm_id,
                                "ref_mfa_id": ref_totp_mfa['id'],
                                "is_configured": False,
                                "is_disabled":False,
                                "mfa_configuration_next_setup_at": datetime.now(),
                                "is_activated": True,
                            }
                        )
                        print(f"\n test_user_mfa : {test_user_mfa} \n", True)
                user_account_hash = HashService.generate_hash(f"{test_adm_id}")
                print(f"\n user_account_hash : {user_account_hash} \n", True)
                data_update = {
                    "user_account_hash": user_account_hash
                }
                await generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=test_adm_id, data=data_update)

                user_account_socket_hash = HashService.generate_hash(
                    f"{test_adm_id}")
                tester_data_update = {
                    "user_account_socket_hash": user_account_socket_hash
                }
                await generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=test_adm_id, data=tester_data_update)
            print(f"\n Admin user created or upserted. : {test_user} \n", True)

        print(f"\n existing_role : {existing_role} \n", True)

        if not existing_role:
            print("No default system role founded", True)
            return
        # Create Admin User
        password = PasswordService.hash_password(settings.ADMIN_PASSWORD)
        user_data = {
            "username": settings.ADMIN_USERNAME,
            "account_status": AccountStatusFlag.ACTIVE.value,
            "password": password,
            "sys_organization_id": system_organization['id'],
            "email": settings.ADMIN_EMAIL,
            "phone_number": settings.ADMIN_PHONE_NUMBER,
            "is_default": True,
            "rbac_profile_id": system_profil['id'],
            "gender": settings.ADMIN_GENDER,
            "first_name": settings.ADMIN_FIRST_NAME,
            "last_name": settings.ADMIN_LAST_NAME,
            "rbac_role_id": existing_role['id']
        }
        exist = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_USER,
            output_data_type=OutputDataType.DEFAULT,
            query={
                "filter__username": user_data['username']
            }
        )
        if not exist:
            user = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.SYS_USER,
                filter_data={"username": str(user_data['username']).strip().lower()},
                update_data=user_data
            )
        else:
            user = exist

        adm_id = user if isinstance(user, str) else user['id']
        if adm_id: 
            ref_totp_mfa = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_MFAS,
                output_data_type=OutputDataType.DEFAULT,
                query={
                    "filter__flag": MFaFlag.SYCAMORE_2FA_APP.value
                }
            )
            if ref_totp_mfa:
                check_existing_cfg_user_mfa = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.CFG_USER_MFA,
                    output_data_type=OutputDataType.DEFAULT,
                    query={
                        "filter__sys_user_id": adm_id,
                        "filter__ref_mfa_id": ref_totp_mfa['id']
                    }
                )
                if not check_existing_cfg_user_mfa:
                    await generic_service.add_data_to_collection(
                        collection_key=CollectionKey.CFG_USER_MFA,
                        data={
                            "sys_user_id": adm_id,
                            "ref_mfa_id": ref_totp_mfa['id'],
                            "is_configured": False,
                            "mfa_configuration_next_setup_at": datetime.now(),
                            "is_activated": True,
                        }
                    )

            user_account_hash = HashService.generate_hash(f"{adm_id}")
            if 'user_account_hash' not in user:
                data_update = {
                    "user_account_hash": user_account_hash
                }
                await generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=adm_id, data=data_update)

            user_account_socket_hash = HashService.generate_hash(f"{adm_id}")
            if 'user_account_socket_hash' not in user:
                data_update = {
                    "user_account_socket_hash": user_account_socket_hash
                }
                await generic_service.update_data_in_collection(collection_key=CollectionKey.SYS_USER, item_id=adm_id, data=data_update)
            language = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_LANGUAGE.value,
                output_data_type=OutputDataType.DEFAULT.value,
                accept_language=DEFAULT_LANGUAGE,
                query={
                    "filter__short_code": 'fr'
                }
            )

            # ADD USER CONFIG DEFAULT DATA
            if language:
                await generic_service.add_data_to_collection(
                    collection_key=CollectionKey.CFG_USER_CONFIG,
                    data={
                        "sys_user_id": adm_id,
                        "allowed_device_count": 1,
                        "ref_language_id": language['id'],
                    }
                )
        print(f"\n Admin user created or upserted. : {user} \n", True)
    except ValueError as e:
        print(f"Error: {e}")
    except PermissionError as e:
        print(f"Permission Error in create_users: {e}")
 
 
async def create_default_application():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    try:

        app1 = get_core_sys_apps_db()
        print(f"\n\n\n START DEFAULT APP : {app1} \n\n\n")
        await generic_service.create_default_application(app1,)


        # agent_apps = get_trans_agent_flutter_seed_app()
        # print(f"\n\n\n START AGENT APP : {agent_apps} \n\n\n")
        # await generic_service.create_default_application(agent_apps,)


        stands_menus = get_static_sys_standalone_menu_db()
        print(f"\n\n\n START STANDANONE MENUS : {len(stands_menus)} \n\n\n")
        await generic_service.on_sub_menu_save(stands_menus)
        return True
    except ValueError as e:
        print(f"\n ERROR CALLING DEFAULT APP FX : {e} \n")
        print(f"Error: {e}")
        return False


async def seed_senat_digit_modules_rbac():
    """Register every senat-digit module's URLs+permissions in the RBAC
    catalog and grant them to the right roles.

    Splits the work cleanly:
      step A — `seed_rbac_from_module(...)` per module: writes
        rbac_endpoint + rbac_permission + rbac_permission_target rows
        for every URL the module exposes (e.g. /list/session,
        /create/session, /list/sys_user_for_organization, …).

      step B — `grant_permissions_to_role(...)` per role × module:
        writes rbac_permission_role rows so
        `permission_check_middleware` finds a match and lets the
        request through. Without this, every URL is a 403.

    Role grants for MVP local dev:
      - SYSTEM_PROFIL_SUPER_ADMIN: admin_user (cross-tenant ops only).
        System admins manage tenancy, not parliamentary business.
      - MAIN_PROFILE_SUPER_ADMIN: every senat-digit feature module
        (auth_device, session, presence, agenda, document, vote,
        parole, notification, audit_security). Demo runs as one
        super-admin role; per-role narrowing (SENATEUR vs GREFFIER)
        is a Phase 2 slice.
    """
    from app.modules.admin_user.seeds.admin_user_seed_loader import (
        load_admin_user_permission_titles,
    )
    from app.modules.core.seeds.core_static.core_static_seed_loader import (
        load_core_static_permission_titles,
    )
    from app.modules.agenda.seeds.agenda_seed_loader import (
        load_agenda_permission_titles,
    )
    from app.modules.audit_security.seeds.audit_seed_loader import (
        load_audit_security_permission_titles,
    )
    from app.modules.auth.seeds.senat_seed_loader import (
        load_auth_device_permission_titles,
    )
    from app.modules.core.seeds.senat_digit_modules_rbac import (
        build_senat_digit_modules_rbac_title_db,
    )
    from app.modules.core.services.rbac_role.rbac_role_service import (
        RbacRoleService,
    )
    from app.modules.document.seeds.document_seed_loader import (
        load_document_permission_titles,
    )
    from app.modules.notification.seeds.notification_seed_loader import (
        load_notification_permission_titles,
    )
    from app.modules.parole.seeds.parole_seed_loader import (
        load_parole_permission_titles,
    )
    from app.modules.presence.seeds.presence_seed_loader import (
        load_presence_permission_titles,
    )
    from app.modules.session_meeting.seeds.session_seed_loader import (
        load_session_meeting_permission_titles,
    )
    from app.modules.vote.seeds.vote_seed_loader import (
        load_vote_permission_titles,
    )

    rbac = RbacRoleService(DEFAULT_LANGUAGE)

    # Step A — register every URL/permission the senat-digit modules expose.
    tree = build_senat_digit_modules_rbac_title_db()
    print(f"\n[senat-digit RBAC] seeding {len(tree)} module trees …")
    await rbac.seed_rbac_from_module(tree)

    # Step B — link permissions to their endpoints (rbac_permission_target).
    # The legacy step-2 seeder can't process the senat-digit loaders' flat
    # meta_data shape, so we write these rows directly here.
    all_loaders = [
        load_admin_user_permission_titles,
        load_core_static_permission_titles,
        load_auth_device_permission_titles,
        load_session_meeting_permission_titles,
        load_presence_permission_titles,
        load_agenda_permission_titles,
        load_document_permission_titles,
        load_vote_permission_titles,
        load_parole_permission_titles,
        load_notification_permission_titles,
        load_audit_security_permission_titles,
    ]
    perm_to_urls: list[tuple[str, str]] = []
    for loader in all_loaders:
        for perm in loader():
            meta = (perm.get("core_seeds") or {}).get("rbac_collection_meta_data_obj") or {}
            for row in meta.get("collection_meta_data_to_menus") or []:
                url = (row.get("rbac_endpoint") or "").strip()
                if url:
                    perm_to_urls.append((perm["flag"], url))
    print(f"[senat-digit RBAC] linking {len(perm_to_urls)} permission↔endpoint pairs …")
    await rbac.link_permissions_to_endpoints(permission_to_urls=perm_to_urls)

    # Step C — grant permissions to roles.
    #
    # Four chamber roles get distinct cuts:
    #   system_profil_super_admin  : cross-tenant. Creates main-profile
    #                                organizations + system break-glass
    #                                user-management. Doesn't run plenary
    #                                business.
    #   main_profile_super_admin   : the Sénat tenant's owner — handles
    #                                in-org user mgmt (create users, lock,
    #                                password reset, validate device
    #                                enrolment) AND has god-mode on every
    #                                feature permission. Production
    #                                accounts in this role are senior IT/
    #                                greffier leads; the role is not
    #                                pure break-glass.
    #   senateur                   : participation cut — vote.cast,
    #                                presence.sign_self, parole.request_self,
    #                                proxy.assign, document.amend_create, …
    #   greffier                   : orchestration cut — session.open/close,
    #                                vote.configure/supervise, agenda.publish,
    #                                document.publish, parole.dispatch, …
    #                                NO user management.
    #
    # See `senat_digit_role_matrix.py` for the SHARED / SENATEUR_EXTRA /
    # GREFFIER_EXTRA cut and the parliamentary-role rationale.
    from app.modules.core.seeds.senat_digit_role_matrix import (
        greffier_permission_keys,
        senateur_permission_keys,
    )

    admin_user_keys = [p["flag"] for p in load_admin_user_permission_titles()]
    # Cross-tenant operations only the system_profil should perform.
    # Everything else under admin_user.* is in-org and granted to
    # `main_profile_super_admin` too (the Sénat IT/owner role).
    _CROSS_TENANT_ADMIN_KEYS = {"admin_user.create_organization"}
    in_org_admin_keys = [
        k for k in admin_user_keys if k not in _CROSS_TENANT_ADMIN_KEYS
    ]
    # Device-validation permissions a greffier needs in addition to their
    # session-orchestration set. The greffier is on-site during plenary
    # and routinely enrols sénateur tablets — making them wait for the
    # main_profile_super_admin breaks the in-session UX. They explicitly
    # don't get user-mgmt (list_users / lock-unlock / password-reset).
    _GREFFIER_DEVICE_KEYS = [
        "admin_user.list_pending_devices",
        "admin_user.validate_device",
        "admin_user.revoke_device",
    ]
    # Shared static reads — granted to EVERY role (every authenticated user
    # needs the bottom-nav fetch, own-config read, own notifications). The
    # endpoints scope to the caller's context server-side; safe baseline.
    core_static_keys = [p["flag"] for p in load_core_static_permission_titles()]
    main_profile_keys: list[str] = []
    for loader in (
        load_auth_device_permission_titles,
        load_session_meeting_permission_titles,
        load_presence_permission_titles,
        load_agenda_permission_titles,
        load_document_permission_titles,
        load_vote_permission_titles,
        load_parole_permission_titles,
        load_notification_permission_titles,
        load_audit_security_permission_titles,
    ):
        main_profile_keys.extend(p["flag"] for p in loader())

    senateur_keys = senateur_permission_keys()
    greffier_keys = greffier_permission_keys()

    print(f"[senat-digit RBAC] granting admin_user ({len(admin_user_keys)}) + core_static ({len(core_static_keys)}) → system_profil_super_admin")
    await rbac.grant_permissions_to_role(
        role_flag="system_profil_super_admin",
        permission_keys=[*admin_user_keys, *core_static_keys],
    )
    print(f"[senat-digit RBAC] granting features ({len(main_profile_keys)}) + in-org admin ({len(in_org_admin_keys)}) + core_static → main_profile_super_admin")
    await rbac.grant_permissions_to_role(
        role_flag="main_profile_super_admin",
        # In-org admin keys are intentionally INCLUDED here so the Sénat
        # IT/owner can manage users without needing a system-profil
        # account. `admin_user.create_organization` is excluded — that's
        # cross-tenant tenancy creation, system_profil's job only.
        permission_keys=[*main_profile_keys, *in_org_admin_keys, *core_static_keys],
    )
    print(f"[senat-digit RBAC] granting senateur cut ({len(senateur_keys)}) + core_static → senateur")
    await rbac.grant_permissions_to_role(
        role_flag="senateur",
        permission_keys=[*senateur_keys, *core_static_keys],
    )
    print(f"[senat-digit RBAC] granting greffier cut ({len(greffier_keys)}) + device validation ({len(_GREFFIER_DEVICE_KEYS)}) + core_static → greffier")
    await rbac.grant_permissions_to_role(
        role_flag="greffier",
        permission_keys=[*greffier_keys, *_GREFFIER_DEVICE_KEYS, *core_static_keys],
    )

    # Step D — Home tab tile permissions (one rbac_permission per
    # sub-menu in `apps/home/senat_digit_mobile_home_sub_menus.py`).
    #
    # Each tile has `core_seeds.rbac_roles_list` declaring which roles
    # the permission is granted to (sénateur / greffier / mainadmin /
    # sysadmin). The seed pipeline writes the `rbac_permission_role`
    # rows that the `/static/data/get-application-user-submenus`
    # aggregation walks (rbac_role → rbac_permission →
    # rbac_permission_target → sys_menu) to filter tiles per role.
    #
    # Without this step, every Home tile is filtered out of the
    # response even when its profile gating matches.
    from app.modules.api_conumers_seed.senat_digit_mobile.rbac.home.senat_digit_mobile_home_all_rbac import (
        SENAT_DIGIT_MOBILE_HOME_RBAC_TREE,
    )
    print(
        f"[senat-digit RBAC] seeding {len(SENAT_DIGIT_MOBILE_HOME_RBAC_TREE[0]['permissions'])} "
        f"Home-tab tile permissions + role grants …"
    )
    await rbac.seed_rbac_from_module(SENAT_DIGIT_MOBILE_HOME_RBAC_TREE)

    # Step E — Invalidate caches for `/static/data/get-applications`
    # and `/static/data/get-application-user-submenus`.
    #
    # Why this lives in apps-seed: every time we change the apps
    # catalogue (Step A) or the RBAC chain that gates apps (Steps B-D),
    # the previously-cached rows for every existing user become stale.
    # Without invalidation, the next login serves the OLD apps tree
    # from cache and never runs the fresh aggregation — new tiles
    # silently don't appear until cache is manually purged.
    #
    # Two cache layers to handle:
    #   L1 (Redis)   — keys `{ENV}static_cache:*` (TTL'd, but holds
    #                  stale data until expiry). Delete-by-pattern.
    #   L2 (Mongo)   — `cfg_user_app_store` rows. Re-warmed by
    #                  `seed_dynamic_user_app_store()` which runs the
    #                  fresh aggregation and upserts the result; also
    #                  purges out-of-scope rows from prior wider-matrix
    #                  runs.
    #
    # Order matters: invalidate L1 FIRST so the L2 re-warm doesn't
    # short-circuit on a stale L1 hit during its own probe.
    #
    # Best-effort: a cache-flush failure must NOT break apps-seed. The
    # live endpoint still works on a cold cache, just slower.
    try:
        from app.modules.core.services.redis.redis_service import (
            AppRedisService,
        )
        deleted = await AppRedisService.delete_keys_by_pattern("static_cache:*")
        print(
            f"[senat-digit RBAC] L1 (Redis) flushed: {deleted} `static_cache:*` keys"
        )
    except Exception as flush_err:  # noqa: BLE001 — never block on Redis
        print(
            f"[senat-digit RBAC] WARN: L1 (Redis) flush failed "
            f"(non-fatal): {flush_err}"
        )

    try:
        from app.modules.core.services.user_app_store.user_app_store_dynamic_seed_service import (
            seed_dynamic_user_app_store,
        )
        print("\n[senat-digit RBAC] re-warming cfg_user_app_store (L2 cache) …")
        warm_stats = await seed_dynamic_user_app_store()
        print(f"[senat-digit RBAC] cfg_user_app_store warm: {warm_stats}")
    except Exception as warm_err:  # noqa: BLE001 — never block on cache warm
        print(
            f"[senat-digit RBAC] WARN: cfg_user_app_store re-warm failed "
            f"(non-fatal): {warm_err}"
        )


async def create_app_group():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default apps groups.
    """
    app_groups = [
        {
            "name": "Apps",
            "flag": EAppGroupFlag.COMMON.value,
            # Applications communes.
            "description_str": "Applications communes.",
            "order_by": 1,
            "icon": """<svg id="fi_11488499" enable-background="new 0 0 512 512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><linearGradient id="_23_00000100374581786982064450000002986688477376758180_" gradientTransform="matrix(1 0 0 -1 0 513.42)" gradientUnits="userSpaceOnUse" x1="31.995" x2="480.005" y1="481.435" y2="33.415"><stop offset="0" stop-color="#459dff"></stop><stop offset="1" stop-color="#0056b3"></stop></linearGradient><g id="Icon"><path id="_23" d="m175.7 233.8h-102.2c-32.3 0-58.4-26.1-58.4-58.4v-102.3c0-32.3 26.2-58.4 58.4-58.4h102.2c32.3 0 58.4 26.2 58.4 58.4v102.2c0 32.3-26.2 58.5-58.4 58.5zm321.2-58.5v-102.2c0-32.3-26.1-58.4-58.4-58.4h-102.2c-32.3 0-58.4 26.2-58.4 58.4v102.2c0 32.3 26.1 58.4 58.4 58.4h102.2c32.3.1 58.4-26.1 58.4-58.4zm-262.8 263.6v-102.2c0-32.3-26.1-58.4-58.4-58.4h-102.2c-32.3 0-58.4 26.2-58.4 58.4v102.2c0 32.3 26.2 58.4 58.4 58.4h102.2c32.2 0 58.4-26.2 58.4-58.4zm262.8 0v-102.2c0-32.3-26.1-58.4-58.4-58.4h-102.2c-32.3 0-58.4 26.2-58.4 58.4v102.2c0 32.3 26.1 58.4 58.4 58.4h102.2c32.3 0 58.4-26.2 58.4-58.4z" fill="url(#_23_00000100374581786982064450000002986688477376758180_)"></path></g>
            </svg>"""
        },
        {
            "name": "Transport urbain",
            "flag": EAppGroupFlag.URBAN_TRANSPORTATION.value,
            "description_str": "Gestion de transport urbain",  
            "order_by":2,
            "icon":"""<svg id="fi_11790238" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
                <path d="m58.86 28.24c-.13-.74-.68-1.33-1.4-1.52l-1.9-.51c-.29-1.98-.82-3.9-1.53-5.71l1.39-1.39c.53-.53.71-1.31.45-2.01-.16-.44-.4-.98-.76-1.6-.35-.62-.7-1.09-1-1.45-.48-.58-1.25-.81-1.97-.62l-1.91.51c-1.23-1.54-2.63-2.94-4.17-4.17l.51-1.91c.19-.72-.04-1.49-.62-1.97-.36-.3-.83-.65-1.45-1-.62-.36-1.16-.6-1.6-.76-.7-.26-1.48-.08-2.01.45l-1.39 1.39c-1.81-.71-3.73-1.24-5.71-1.53l-.51-1.9c-.19-.72-.78-1.27-1.52-1.4-.46-.08-1.05-.14-1.76-.14s-1.3.06-1.76.14c-.74.13-1.33.68-1.52 1.4l-.51 1.9c-1.98.29-3.9.82-5.71 1.53l-1.39-1.39c-.53-.53-1.31-.71-2.01-.45-.44.16-.98.4-1.6.76-.62.35-1.09.7-1.45 1-.58.48-.81 1.25-.62 1.97l.51 1.91c-1.54 1.23-2.94 2.63-4.17 4.17l-1.91-.51c-.72-.19-1.49.04-1.97.62-.3.36-.65.83-1 1.45-.36.62-.6 1.16-.76 1.6-.26.7-.08 1.48.45 2.01l1.39 1.39c-.71 1.81-1.24 3.73-1.53 5.71l-1.9.51c-.72.19-1.27.78-1.4 1.52-.08.46-.14 1.05-.14 1.76s.06 1.3.14 1.76c.13.74.68 1.33 1.4 1.52l1.9.51c.29 1.98.82 3.9 1.53 5.71l-1.39 1.39c-.53.53-.71 1.31-.45 2.01.16.44.4.98.76 1.6.35.62.7 1.09 1 1.45.48.58 1.25.81 1.97.62l1.91-.51c1.23 1.54 2.63 2.94 4.17 4.17l-.51 1.91c-.19.72.04 1.49.62 1.97.36.3.83.65 1.45 1 .62.36 1.16.6 1.6.76.7.26 1.48.08 2.01-.45l1.39-1.39c1.81.71 3.73 1.24 5.71 1.53l.51 1.9c.19.72.78 1.27 1.52 1.4.46.08 1.05.14 1.76.14s1.3-.06 1.76-.14c.74-.13 1.33-.68 1.52-1.4l.51-1.9c1.98-.29 3.9-.82 5.71-1.53l1.39 1.39c.53.53 1.31.71 2.01.45.44-.16.98-.4 1.6-.76.62-.35 1.09-.7 1.45-1 .58-.48.81-1.25.62-1.97l-.51-1.91c1.54-1.23 2.94-2.63 4.17-4.17l1.91.51c.72.19 1.49-.04 1.97-.62.3-.36.65-.83 1-1.45.36-.62.6-1.16.76-1.6.26-.7.08-1.48-.45-2.01l-1.39-1.39c.71-1.81 1.24-3.73 1.53-5.71l1.9-.51c.72-.19 1.27-.78 1.4-1.52.08-.46.14-1.05.14-1.76s-.06-1.3-.14-1.76zm-28.86 22.76c-11.6 0-21-9.4-21-21s9.4-21 21-21 21 9.4 21 21-9.4 21-21 21z" fill="#ef564b"/>
                <path d="m44 35v4c0 .55-.45 1-1 1h-4c-.55 0-1-.45-1-1v-4z" fill="#384149"/>
                <path d="m16 35h6v4c0 .55-.45 1-1 1h-4c-.55 0-1-.45-1-1z" fill="#384149"/>
                <g fill="#ef564b">
                    <path d="m41 26 2.888 1.296c.688.393 1.112 1.124 1.112 1.916v5.788c0 .552-.448 1-1 1h-28c-.552 0-1-.448-1-1v-5.788c0-.792.424-1.523 1.112-1.916l2.888-1.296 1-1h20z"/>
                    <path d="m17 22c1.104 0 2 .896 2 2v2h-2c-1.104 0-2-.896-2-2 0-1.104.896-2 2-2z"/>
                    <path d="m43 22h2v2c0 1.104-.896 2-2 2-1.104 0-2-.896-2-2 0-1.104.896-2 2-2z" transform="matrix(-1 0 0 -1 86 48)"/>
                </g>
                <path d="m19 26 2.359-7.268c.157-.439.573-.732 1.039-.732h15.203c.466 0 .882.293 1.039.732l2.359 7.268h-22z" fill="#3e7efc"/>
                <path d="m30 52c-12.131 0-22-9.869-22-22s9.869-22 22-22 22 9.869 22 22-9.869 22-22 22zm0-42c-11.028 0-20 8.972-20 20s8.972 20 20 20 20-8.972 20-20-8.972-20-20-20z" fill="#b73d3d"/>
                <path d="m41 32h-1c-.553 0-1-.447-1-1s.447-1 1-1h1c.553 0 1 .447 1 1s-.447 1-1 1z" fill="#fff"/>
                <path d="m20 32h-1c-.553 0-1-.447-1-1s.447-1 1-1h1c.553 0 1 .447 1 1s-.447 1-1 1z" fill="#fff"/>
                <path d="m36 32h-12c-.553 0-1-.447-1-1s.447-1 1-1h12c.553 0 1 .447 1 1s-.447 1-1 1z" fill="#cc4744"/>
                </svg>

            """
        },
        # {
        #     "name": "Transport Interurbain",
        #     "flag": EAppGroupFlag.INTER_URBAIN_TRANSPORTATION.value,
        #     "description_str": "Gestion de transport interurbain",
        #     # Transport Interurbain : Réservations et ventes, Gestion des trajets, Flotte et chauffeurs, Suivi des passagers
        #     "order_by":3,
        #     "is_activated":False,
        #     "icon":"""
        #         <svg id="fi_3124263" enable-background="new 0 0 512 512" height="512" viewBox="0 0 512 512" width="512" xmlns="http://www.w3.org/2000/svg">
        #             <g>
        #                 <g>
        #                 <g>
        #                     <path d="m428.019 415.413h-326.744c-51.708 0-93.774-42.067-93.774-93.774 0-51.708 42.067-93.775 93.774-93.775h309.451c35.165 0 63.774-28.609 63.774-63.774s-28.609-63.774-63.774-63.774h-326.744c-8.284 0-15-6.716-15-15s6.716-15 15-15h326.744c51.707 0 93.774 42.067 93.774 93.774s-42.067 93.774-93.774 93.774h-309.451c-35.166 0-63.774 28.609-63.774 63.774 0 35.166 28.609 63.775 63.774 63.775h326.744c8.284 0 15 6.716 15 15s-6.716 15-15 15z" fill="#e2dfe3"/>
        #                 </g>
        #                 <g>
        #                     <path d="m160.463 83.984c0 45.527-56.794 99.015-72.499 112.936-2.275 2.017-5.69 2.018-7.967.003-15.725-13.916-72.606-67.409-72.497-112.939.101-42.239 34.242-76.481 76.482-76.481s76.481 34.242 76.481 76.481z" fill="#d87b7b"/>
        #                     <path d="m83.981 7.503c-5.136 0-10.148.516-14.998 1.48 35.055 6.974 61.479 37.896 61.479 75.001 0 37.836-39.224 81.168-61.492 102.72 4.534 4.382 8.369 7.867 11.026 10.219 2.277 2.015 5.692 2.014 7.967-.003 15.705-13.921 72.499-67.409 72.499-112.936.001-42.239-34.241-76.481-76.481-76.481z" fill="#d06161"/>
        #                     <circle cx="83.981" cy="85.314" fill="#fff" r="39.62"/>
        #                 </g>
        #                 <g>
        #                     <path d="m504.5 390.054c0 45.527-56.794 99.015-72.499 112.936-2.275 2.017-5.69 2.018-7.967.003-15.724-13.916-72.605-67.409-72.496-112.939.101-42.239 34.242-76.481 76.481-76.481s76.481 34.241 76.481 76.481z" fill="#d87b7b"/>
        #                     <path d="m428.019 313.572c-5.136 0-10.148.516-14.998 1.48 35.055 6.974 61.479 37.897 61.479 75.001 0 37.836-39.224 81.168-61.492 102.72 4.534 4.383 8.369 7.867 11.026 10.219 2.277 2.016 5.692 2.014 7.967-.003 15.705-13.92 72.499-67.409 72.499-112.936 0-42.238-34.242-76.481-76.481-76.481z" fill="#d06161"/>
        #                     <circle cx="428.019" cy="391.384" fill="#fff" r="39.62"/>
        #                 </g>
        #                 <g>
        #                     <g>
        #                     <g>
        #                         <g>
        #                         <path d="m196 341.113c-8.284 0-15-6.716-15-15v-39.22h30v39.22c0 8.284-6.716 15-15 15z" fill="#655e67"/>
        #                         <path d="m316 341.113c-8.284 0-15-6.716-15-15v-39.22h30v39.22c0 8.284-6.716 15-15 15z" fill="#655e67"/>
        #                         <path d="m346 226.634v55.259c0 11.046-8.954 20-20 20h-140c-11.046 0-20-8.954-20-20v-55.259z" fill="#b3e59f"/>
        #                         <path d="m316 226.634v55.259c0 11.046-8.954 20-20 20h30c11.046 0 20-8.954 20-20v-55.259z" fill="#95d6a4"/>
        #                         <path d="m326 142.893h-140c-11.046 0-20 8.954-20 20v63.741h180v-63.741c0-11.046-8.954-20-20-20z" fill="#ddeafb"/>
        #                         <path d="m326 142.893h-30c11.046 0 20 8.954 20 20v63.741h30v-63.741c0-11.046-8.954-20-20-20z" fill="#cbe2ff"/>
        #                         </g>
        #                     </g>
        #                     </g>
        #                 </g>
        #                 </g>
        #                 <path d="m233.5 271.763h45c4.143 0 7.5-3.357 7.5-7.5s-3.357-7.5-7.5-7.5h-45c-4.142 0-7.5 3.357-7.5 7.5s3.358 7.5 7.5 7.5zm-102.399-186.448c0-25.982-21.138-47.12-47.12-47.12s-47.12 21.138-47.12 47.12 21.138 47.12 47.12 47.12 47.12-21.138 47.12-47.12zm-79.239 0c0-17.711 14.409-32.12 32.12-32.12s32.12 14.409 32.12 32.12-14.409 32.12-32.12 32.12-32.12-14.41-32.12-32.12zm151.638 186.448c4.136 0 7.5-3.364 7.5-7.5 0-4.135-3.364-7.5-7.5-7.5s-7.5 3.365-7.5 7.5c0 4.136 3.364 7.5 7.5 7.5zm224.519 72.501c-25.982 0-47.12 21.138-47.12 47.12s21.138 47.12 47.12 47.12 47.12-21.138 47.12-47.12-21.138-47.12-47.12-47.12zm0 79.24c-17.711 0-32.12-14.409-32.12-32.12s14.409-32.12 32.12-32.12 32.12 14.409 32.12 32.12-14.409 32.12-32.12 32.12zm0-117.432c-42.088 0-77.088 31.269-83.067 71.841h-120.352c-4.142 0-7.5 3.357-7.5 7.5s3.358 7.5 7.5 7.5h119.505c.207 4.83.961 9.832 2.26 15h-245.095c-47.569 0-86.27-38.701-86.27-86.271 0-47.574 38.701-86.279 86.27-86.279h57.23v15h-57.23c-39.298 0-71.27 31.972-71.27 71.27 0 39.304 31.972 71.28 71.27 71.28h88.33c4.142 0 7.5-3.357 7.5-7.5s-3.358-7.5-7.5-7.5h-88.33c-31.027 0-56.27-25.247-56.27-56.28 0-31.027 25.243-56.27 56.27-56.27h57.23v16.529c0 10.663 6.105 19.922 15 24.482v19.738c0 12.406 10.093 22.5 22.5 22.5s22.5-10.094 22.5-22.5v-16.721h75v16.721c0 12.406 10.094 22.5 22.5 22.5s22.5-10.094 22.5-22.5v-19.738c8.895-4.561 15-13.819 15-24.482v-16.529h57.23c55.84 0 101.27-45.43 101.27-101.271 0-55.846-45.43-101.28-101.27-101.28h-245.475c-9.408-36.091-42.277-62.81-81.273-62.81-11.348 0-22.354 2.227-32.713 6.618-3.813 1.617-5.595 6.019-3.978 9.833 1.617 3.812 6.02 5.597 9.833 3.978 8.497-3.603 17.534-5.429 26.858-5.429 38.036 0 68.981 30.945 68.981 68.981 0 33.074-35.447 76.485-68.985 106.443-33.589-29.955-69.057-73.358-68.978-106.424.04-16.633 6.046-32.692 16.913-45.22 2.714-3.129 2.378-7.865-.751-10.579s-7.865-2.378-10.58.751c-13.224 15.244-20.533 34.781-20.582 55.013-.05 21.117 10.679 45.659 31.89 72.944 16.755 21.555 35.748 39.09 43.136 45.628 2.552 2.259 5.752 3.389 8.952 3.389 3.203 0 6.407-1.132 8.96-3.396 7.377-6.538 26.342-24.072 43.087-45.626 13.645-17.563 22.951-33.987 27.855-49.094h246.851c31.027 0 56.27 25.247 56.27 56.28 0 31.027-25.242 56.271-56.27 56.271h-57.231v-57.471c0-15.163-12.337-27.5-27.5-27.5h-140c-15.164 0-27.5 12.337-27.5 27.5v57.471h-57.23c-55.84 0-101.27 45.434-101.27 101.28 0 55.841 45.43 101.271 101.27 101.271h250.194c5.321 12.559 13.484 25.945 24.463 40.068 16.756 21.554 35.749 39.089 43.136 45.626 2.552 2.26 5.752 3.39 8.953 3.39 3.203 0 6.406-1.132 8.96-3.396 7.377-6.537 26.341-24.071 43.087-45.626 21.192-27.279 31.937-51.814 31.937-72.922 0-46.308-37.674-83.982-83.981-83.982zm-74.519-70.709h57.23c39.298 0 71.27-31.972 71.27-71.271 0-39.304-31.972-71.28-71.27-71.28h-243.373c.399-3.005.606-5.949.606-8.828 0-2.078-.102-4.132-.251-6.172h243.019c47.569 0 86.27 38.705 86.27 86.28 0 47.569-38.7 86.271-86.27 86.271h-57.231zm-150 90.75c0 4.136-3.364 7.5-7.5 7.5s-7.5-3.364-7.5-7.5v-16.721h15zm120 0c0 4.136-3.364 7.5-7.5 7.5s-7.5-3.364-7.5-7.5v-16.721h15zm-150-163.22c0-6.893 5.607-12.5 12.5-12.5h140c6.893 0 12.5 5.607 12.5 12.5v56.241h-165zm0 71.241h165v47.759c0 6.893-5.607 12.5-12.5 12.5h-140c-6.893 0-12.5-5.607-12.5-12.5zm254.516 262.363c-33.589-29.956-69.057-73.358-68.978-106.426.091-38.046 31.035-68.999 68.98-68.999 38.036 0 68.981 30.945 68.981 68.981.001 33.076-35.445 76.487-68.983 106.444zm-119.516-224.734c4.136 0 7.5-3.364 7.5-7.5 0-4.135-3.364-7.5-7.5-7.5s-7.5 3.365-7.5 7.5c0 4.136 3.364 7.5 7.5 7.5z"/>
        #             </g>
        #             </svg>

        #     """
        # },
        # {
        #     "name": "Transport Scolaire",
        #     "flag": EAppGroupFlag.SCHOOL_TRANSPORTATION.value,
        #     "description_str": "Gestion de transport scolaire",
        #     # Transport Interurbain : Réservations et ventes, Gestion des trajets, Flotte et chauffeurs, Suivi des passagers
        #     "order_by":4,
        #     "is_activated":False,
        #     "icon":"""<svg version="1.1" id="fi_174237" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 512.001 512.001" style="enable-background:new 0 0 512.001 512.001;" xml:space="preserve">
        #         <g>
        #             <g>
        #             <g>
        #                 <path style="fill:#2D404E;" d="M57.089,196.933h-5.446c-7.826,0-7.826-9.588-7.826-12.738V79.553
        #                         c0-1.488-0.037-2.941-0.073-4.299c-0.15-5.833-0.24-9.354,2.507-10.49c2.489-1.027,4.684,1.287,5.622,2.28
        #                         c4.848,5.118,9.746,9.5,9.794,9.543l-3.319,3.718c-0.199-0.178-4.823-4.314-9.67-9.392c-0.027,1.29,0.013,2.888,0.047,4.213
        #                         c0.037,1.398,0.075,2.896,0.075,4.427v104.642c0,7.755,2.064,7.755,2.843,7.755h5.446V196.933L57.089,196.933z"/>
        #             </g>
        #             <path style="fill:#2D404E;" d="M47.421,171.419c0,3.669-2.975,6.645-6.644,6.645H28.318c-3.669,0-6.644-2.976-6.644-6.645V90.031
        #                     c0-3.67,2.975-6.645,6.644-6.645h12.458c3.669,0,6.644,2.975,6.644,6.645L47.421,171.419L47.421,171.419z"/>
        #             <path style="fill:#253744;" d="M36.478,172.994c-6.58,0-9.915-5.36-9.915-15.669c0-8.577,0-57.489,0-73.674
        #                     c-2.811,0.775-4.887,3.322-4.887,6.38v81.388c0,3.669,2.975,6.645,6.644,6.645h12.458c3.125,0,5.726-2.164,6.436-5.069
        #                     C44.157,172.994,40.031,172.994,36.478,172.994z"/>
        #             <polygon style="opacity:0.3;fill:#586A73;enable-background:new    ;" points="34.444,89.261 41.021,121.442 41.021,89.261 		"/>
        #             </g>
        #             <g>
        #             <g>
        #                 <path style="fill:#2D404E;" d="M454.26,196.933h5.447c7.826,0,7.826-9.588,7.826-12.738V79.553c0-1.488,0.037-2.941,0.072-4.299
        #                         c0.15-5.833,0.24-9.354-2.507-10.49c-2.489-1.027-4.684,1.287-5.622,2.28c-4.848,5.118-9.745,9.5-9.794,9.543l3.319,3.718
        #                         c0.199-0.178,4.822-4.314,9.67-9.392c0.027,1.29-0.014,2.888-0.047,4.213c-0.037,1.398-0.075,2.896-0.075,4.427v104.642
        #                         c0,7.755-2.065,7.755-2.843,7.755h-5.447L454.26,196.933L454.26,196.933z"/>
        #             </g>
        #             <path style="fill:#2D404E;" d="M463.931,171.419c0,3.669,2.975,6.645,6.644,6.645h12.457c3.67,0,6.645-2.976,6.645-6.645V90.031
        #                     c0-3.67-2.975-6.645-6.645-6.645h-12.457c-3.669,0-6.644,2.975-6.644,6.645V171.419z"/>
        #             <path style="fill:#253744;" d="M474.874,172.994c6.579,0,9.915-5.36,9.915-15.669c0-8.577,0-57.489,0-73.674
        #                     c2.811,0.775,4.887,3.322,4.887,6.38v81.388c0,3.669-2.975,6.645-6.645,6.645h-12.457c-3.124,0-5.726-2.164-6.436-5.069
        #                     C467.194,172.994,471.32,172.994,474.874,172.994z"/>
        #             <polygon style="opacity:0.3;fill:#586A73;enable-background:new    ;" points="476.907,89.261 470.329,121.442 470.329,89.261 		
        #                     "/>
        #             </g>
        #             <g>
        #             <g>
        #                 <path style="fill:#2D404E;" d="M477.957,328.462c12.218,0,12.218-14.988,12.218-35.732h-4.983
        #                         c0,20.206-0.322,30.749-7.234,30.749c-5.273,0-8.937-1.142-8.973-1.153l-1.506,4.75
        #                         C467.657,327.132,471.921,328.462,477.957,328.462z"/>
        #             </g>
        #             <path style="fill:#2D404E;" d="M475.525,259.341c5.004,0,12.159,0,12.159,0s7.154,0,12.158,0s13.259,5.538,8.301,16.886
        #                     c-4.957,11.352-8.832,19.932-20.459,20.209c-11.628-0.277-15.502-8.857-20.46-20.209
        #                     C462.266,264.879,470.52,259.341,475.525,259.341z"/>
        #             <path style="fill:#253744;" d="M487.683,289.132c11.418,0,18.065-15.327,20.685-24.602c1.566,2.771,1.976,6.658-0.226,11.696
        #                     c-4.957,11.352-8.832,19.932-20.459,20.209c-11.628-0.277-15.502-8.857-20.46-20.209c-2.142-4.901-1.812-8.714-0.351-11.468
        #                     C469.398,273.646,476.072,289.132,487.683,289.132z"/>
        #             <path style="opacity:0.3;fill:#586A73;enable-background:new    ;" d="M500.118,264.53c0,0-6.044,7.59-12.434,8.275
        #                     c-6.391,0.687-15.803-8.275-15.803-8.275H500.118z"/>
        #             </g>
        #             <path style="fill:#586A73;" d="M474.875,430.614c0,3.669-2.975,6.644-6.644,6.644H43.769c-3.669,0-6.644-2.975-6.644-6.644v-45.578
        #                 c0-3.67,2.975-6.645,6.644-6.645H468.23c3.669,0,6.644,2.975,6.644,6.645L474.875,430.614L474.875,430.614z"/>
        #             <path style="opacity:0.5;fill:#2D404E;enable-background:new    ;" d="M43.771,378.392c-3.669,0-6.644,2.975-6.644,6.645v45.578
        #                 c0,3.669,2.975,6.644,6.644,6.644h8.254v-58.866h-8.254C43.771,378.393,43.771,378.392,43.771,378.392z"/>
        #             <path style="opacity:0.5;fill:#2D404E;enable-background:new    ;" d="M468.23,378.392c3.669,0,6.644,2.975,6.644,6.645v45.578
        #                 c0,3.669-2.975,6.644-6.644,6.644h-8.254v-58.866h8.254V378.392z"/>
        #             <g>
        #             <path style="fill:#2D404E;" d="M43.705,378.392c-1.771,0-3.373,0.721-4.553,1.879c77.745,10.246,216.845,12.259,216.845,12.259
        #                     l-0.067-14.138H43.705z"/>
        #             <path style="fill:#2D404E;" d="M468.29,378.392H256.066l-0.067,14.138c0,0,139.099-2.013,216.844-12.259
        #                     C471.663,379.112,470.062,378.392,468.29,378.392z"/>
        #             </g>
        #             <path style="fill:#F2B643;" d="M474.854,355.831c-0.549-26.023-2.194-49.83-18.088-68.101l-5.482-204.302
        #                 c0,0,2.194-31.005-19.732-46.507C409.627,21.42,363.181,5.155,255.677,0C148.172,5.155,101.725,21.42,79.801,36.922
        #                 S60.068,83.429,60.068,83.429l-5.482,204.302c-15.896,18.271-17.541,42.077-18.087,68.101c-0.549,26.022,9.718,22.97,9.718,22.97
        #                 l209.46,5.09l209.46-5.09C465.135,378.801,475.402,381.854,474.854,355.831z"/>
        #             <polygon style="fill:#2D404E;" points="252.016,73.188 69.614,73.188 62.797,198.868 252.287,198.868 	"/>
        #             <polygon style="fill:#253744;" points="69.614,73.188 62.797,198.868 252.287,198.868 252.28,189.551 71.368,189.551 
        #                 75.135,73.048 	"/>
        #             <polygon style="fill:#2D404E;" points="259.271,73.188 441.67,73.188 448.486,198.868 258.997,198.868 	"/>
        #             <path style="fill:#D89932;" d="M69.704,47.16c2.611-3.764,5.915-7.283,10.096-10.238c13.989-9.892,37.962-20.095,81.409-27.521
        #                 v63.647h-91.49L69.704,47.16z"/>
        #             <polygon style="fill:#253744;" points="69.719,73.048 161.208,73.048 162.179,78.446 72.486,78.446 	"/>
        #             <polygon style="fill:#253744;" points="164.323,73.048 347.031,73.048 345.37,78.446 165.707,78.446 	"/>
        #             <path style="fill:#D89932;" d="M441.647,47.16c-2.61-3.764-5.914-7.283-10.096-10.238c-13.988-9.892-37.962-20.095-81.407-27.521
        #                 v63.647h91.49L441.647,47.16z"/>
        #             <g>
        #             <g>
        #                 <circle style="fill:#B9483E;" cx="375.854" cy="50.187" r="14.277"/>
        #                 <circle style="fill:#DF584C;" cx="375.853" cy="50.187" r="10.513"/>
        #             </g>
        #             <g>
        #                 <circle style="fill:#B9483E;" cx="408.146" cy="52.213" r="12.251"/>
        #                 <circle style="fill:#DF584C;" cx="408.146" cy="52.213" r="9.021"/>
        #             </g>
        #             </g>
        #             <g>
        #             <g>
        #                 <circle style="fill:#B9483E;" cx="135.501" cy="50.187" r="14.277"/>
        #                 <circle style="fill:#DF584C;" cx="135.501" cy="50.187" r="10.513"/>
        #             </g>
        #             <g>
        #                 <circle style="fill:#B9483E;" cx="103.208" cy="52.213" r="12.251"/>
        #                 <circle style="fill:#DF584C;" cx="103.208" cy="52.213" r="9.021"/>
        #             </g>
        #             </g>
        #             <polygon style="fill:#253744;" points="441.635,73.048 350.145,73.048 349.172,78.446 438.865,78.446 	"/>
        #             <rect x="165.153" y="22.803" style="fill:#D89932;" width="181.048" height="41.525"/>
        #             <g>
        #             <path style="fill:#253744;" d="M168.553,52.187c1.146,0.638,3.1,1.105,4.713,1.105c2.633,0,3.908-1.36,3.908-3.229
        #                     c0-2.081-1.274-3.1-3.695-4.672c-3.907-2.378-5.394-5.395-5.394-7.983c0-4.589,3.059-8.41,9.046-8.41
        #                     c1.869,0,3.653,0.511,4.503,1.019l-0.893,4.8c-0.807-0.51-2.039-0.977-3.652-0.977c-2.379,0-3.525,1.443-3.525,2.973
        #                     c0,1.698,0.849,2.591,3.95,4.459c3.779,2.294,5.182,5.182,5.182,8.197c0,5.224-3.865,8.664-9.471,8.664
        #                     c-2.293,0-4.544-0.595-5.479-1.146L168.553,52.187z"/>
        #             <path style="fill:#253744;" d="M199.646,57.453c-0.807,0.383-2.378,0.68-4.332,0.68c-7.305,0-10.788-6.031-10.788-14.143
        #                     c0-10.786,5.989-14.992,11.551-14.992c1.955,0,3.313,0.381,3.866,0.764l-0.934,4.672c-0.637-0.299-1.359-0.552-2.592-0.552
        #                     c-3.142,0-5.987,2.719-5.987,9.811c0,6.838,2.59,9.515,5.987,9.515c0.936,0,1.997-0.211,2.677-0.425L199.646,57.453z"/>
        #             <path style="fill:#253744;" d="M208.271,29.252v11.469h5.818V29.252h5.564v28.626h-5.564V45.901h-5.818v11.977h-5.564V29.252
        #                     H208.271z"/>
        #             <path style="fill:#253744;" d="M241.489,43.056c0,10.787-3.822,15.163-9.259,15.163c-6.499,0-9.047-6.881-9.047-14.737
        #                     c0-7.815,3.101-14.569,9.428-14.569C239.533,28.912,241.489,36.516,241.489,43.056z M228.958,43.565
        #                     c0,6.498,1.231,9.811,3.482,9.811c2.336,0,3.228-4.247,3.228-10.065c0-5.012-0.764-9.556-3.271-9.556
        #                     C230.191,33.755,228.958,37.408,228.958,43.565z"/>
        #             <path style="fill:#253744;" d="M261.921,43.056c0,10.787-3.823,15.163-9.258,15.163c-6.499,0-9.047-6.881-9.047-14.737
        #                     c0-7.815,3.101-14.569,9.428-14.569C259.967,28.912,261.921,36.516,261.921,43.056z M249.391,43.565
        #                     c0,6.498,1.231,9.811,3.483,9.811c2.336,0,3.228-4.247,3.228-10.065c0-5.012-0.764-9.556-3.271-9.556
        #                     C250.622,33.755,249.391,37.408,249.391,43.565z"/>
        #             <path style="fill:#253744;" d="M265.448,29.252h5.565v23.911h7.347v4.715h-12.912V29.252z"/>
        #             <path style="fill:#253744;" d="M288.345,29.678c1.698-0.383,3.907-0.554,6.327-0.554c2.677,0,5.267,0.339,7.264,2.039
        #                     c1.53,1.275,2.166,3.186,2.166,5.183c0,2.548-1.315,5.011-4.162,6.243v0.169c3.312,0.935,5.096,3.695,5.096,6.839
        #                     c0,2.378-0.764,4.204-2.123,5.605c-1.698,1.868-4.587,2.889-9.387,2.889c-2.123,0-3.906-0.128-5.181-0.297L288.345,29.678
        #                     L288.345,29.678z M293.911,41.018h1.187c1.997,0,3.525-1.698,3.525-4.034c0-2.083-0.977-3.695-3.271-3.695
        #                     c-0.594,0-1.104,0.042-1.441,0.169V41.018z M293.911,53.717c0.337,0.084,0.72,0.084,1.23,0.084c2.25,0,4.12-1.359,4.12-4.289
        #                     c0-2.847-1.954-4.334-4.164-4.375h-1.187L293.911,53.717L293.911,53.717z"/>
        #             <path style="fill:#253744;" d="M314.257,29.252v18.603c0,4.206,1.273,5.479,2.717,5.479c1.614,0,2.761-1.147,2.761-5.479V29.252
        #                     h5.565v17.626c0,7.348-2.763,11.341-8.284,11.341c-5.988,0-8.324-4.12-8.324-11.299V29.252H314.257z"/>
        #             <path style="fill:#253744;" d="M329.467,52.187c1.146,0.638,3.1,1.105,4.715,1.105c2.633,0,3.906-1.36,3.906-3.229
        #                     c0-2.081-1.273-3.1-3.695-4.672c-3.908-2.378-5.395-5.395-5.395-7.983c0-4.589,3.059-8.41,9.047-8.41
        #                     c1.869,0,3.653,0.511,4.503,1.019l-0.892,4.8c-0.807-0.51-2.039-0.977-3.653-0.977c-2.378,0-3.524,1.443-3.524,2.973
        #                     c0,1.698,0.85,2.591,3.949,4.459c3.779,2.294,5.182,5.182,5.182,8.197c0,5.224-3.865,8.664-9.472,8.664
        #                     c-2.294,0-4.545-0.595-5.478-1.146L329.467,52.187z"/>
        #             </g>
        #             <rect x="165.153" y="62.252" style="fill:#2D404E;" width="181.048" height="2.076"/>
        #             <rect x="165.153" y="22.803" style="fill:#2D404E;" width="181.048" height="2.076"/>
        #             <path style="fill:#D89932;" d="M264.181,10.265c0,2.433-1.972,4.405-4.406,4.405h-8.196c-2.433,0-4.405-1.973-4.405-4.405l0,0
        #                 c0-2.434,1.973-4.405,4.405-4.405h8.196C262.208,5.859,264.181,7.831,264.181,10.265L264.181,10.265z"/>
        #             <path style="fill:#D89932;" d="M404.574,198.868H255.677H106.781c0,0-30.118,3.974-14.364,25.287
        #                 c15.753,21.314,32.434,43.554,55.601,43.554s107.661,0,107.661,0s84.493,0,107.659,0c23.168,0,39.848-22.239,55.602-43.554
        #                 C434.691,202.842,404.574,198.868,404.574,198.868z"/>
        #             <path style="fill:#2D404E;" d="M365.952,359.601c0,7.338-5.949,13.287-13.288,13.287H158.689c-7.338,0-13.288-5.949-13.288-13.287
        #                 v-73.507c0-7.338,5.95-13.288,13.288-13.288h193.975c7.339,0,13.288,5.95,13.288,13.288V359.601z"/>
        #             <g>
        #             <g>
        #                 <rect x="221.828" y="289.132" style="fill:#F2B643;" width="67.695" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="221.828" y="304.423" style="fill:#F2B643;" width="67.695" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="221.828" y="319.714" style="fill:#F2B643;" width="67.695" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="221.828" y="335.005" style="fill:#F2B643;" width="67.695" height="6.267"/>
        #             </g>
        #             <g>
        #                 <rect x="221.828" y="350.296" style="fill:#F2B643;" width="67.695" height="6.267"/>
        #             </g>
        #             </g>
        #             <g>
        #             <g>
        #                 <rect x="168.292" y="289.132" style="fill:#F2B643;" width="38.181" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="168.292" y="304.423" style="fill:#F2B643;" width="38.181" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="168.292" y="319.714" style="fill:#F2B643;" width="38.181" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="168.292" y="335.005" style="fill:#F2B643;" width="38.181" height="6.267"/>
        #             </g>
        #             <g>
        #                 <rect x="168.292" y="350.296" style="fill:#F2B643;" width="38.181" height="6.267"/>
        #             </g>
        #             </g>
        #             <g>
        #             <g>
        #                 <rect x="304.877" y="289.132" style="fill:#F2B643;" width="38.181" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="304.877" y="304.423" style="fill:#F2B643;" width="38.181" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="304.877" y="319.714" style="fill:#F2B643;" width="38.181" height="6.266"/>
        #             </g>
        #             <g>
        #                 <rect x="304.877" y="335.005" style="fill:#F2B643;" width="38.181" height="6.267"/>
        #             </g>
        #             <g>
        #                 <rect x="304.877" y="350.296" style="fill:#F2B643;" width="38.181" height="6.267"/>
        #             </g>
        #             </g>
        #             <path style="fill:#D89932;" d="M81.759,226.472c0,0,7.876,14.363,20.387,24.558c12.511,10.193,25.947,18.068,25.947,37.53
        #                 c0,19.461,0,84.328,0,84.328s-2.78-28.264-12.047-52.357c-9.267-24.095-17.606-30.583-34.287-36.142V226.472z"/>
        #             <path style="fill:#D89932;" d="M429.592,226.472c0,0-7.877,14.363-20.388,24.558c-12.512,10.193-25.947,18.068-25.947,37.53
        #                 c0,19.461,0,84.328,0,84.328s2.781-28.264,12.048-52.357c9.267-24.095,17.605-30.583,34.287-36.142V226.472L429.592,226.472z"/>
        #             <g>
        #             <circle style="fill:#EB8923;" cx="67.86" cy="218.595" r="16.217"/>
        #             <path style="fill:#D27228;" d="M67.86,234.812c8.956,0,16.217-7.261,16.217-16.218s-7.261-16.217-16.217-16.217
        #                     c-6.275,0-11.718,3.565-14.415,8.778c0,0,12.623-12.538,23.195,1.554C87.854,227.659,67.86,234.812,67.86,234.812z"/>
        #             </g>
        #             <g>
        #             <circle style="fill:#EB8923;" cx="443.491" cy="218.595" r="16.217"/>
        #             <path style="fill:#D27228;" d="M443.493,234.812c-8.957,0-16.218-7.261-16.218-16.218s7.261-16.217,16.218-16.217
        #                     c6.275,0,11.717,3.565,14.415,8.778c0,0-12.623-12.538-23.195,1.554C423.496,227.659,443.493,234.812,443.493,234.812z"/>
        #             </g>
        #             <path style="fill:#D89932;" d="M38.589,372.894c2.864,7.324,7.628,5.907,7.628,5.907l209.46,5.09l209.46-5.09
        #                 c0,0,4.766,1.416,7.629-5.909L38.589,372.894z"/>
        #             <path style="fill:#2D404E;" d="M256.001,437.258H120.427c22.147,22.147,43.186,23.807,56.473,23.807c13.288,0,79.102,0,79.102,0
        #                 s65.812,0,79.1,0c13.287,0,34.327-1.659,56.473-23.807H256.001z"/>
        #             <polygon style="fill:#253744;" points="441.74,73.188 448.557,198.868 259.066,198.868 259.075,189.551 439.988,189.551 
        #                 436.22,73.048 	"/>
        #             <g>
        #             <g>
        #                 <path style="fill:#2D404E;" d="M34.045,328.462c-12.218,0-12.218-14.988-12.218-35.732h4.983c0,20.206,0.322,30.749,7.234,30.749
        #                         c5.273,0,8.937-1.142,8.973-1.153l1.506,4.75C44.344,327.132,40.08,328.462,34.045,328.462z"/>
        #             </g>
        #             <path style="fill:#2D404E;" d="M36.478,259.341c-5.004,0-12.159,0-12.159,0s-7.155,0-12.159,0s-13.259,5.538-8.301,16.886
        #                     c4.958,11.352,8.833,19.932,20.46,20.209c11.627-0.277,15.502-8.857,20.459-20.209C49.736,264.879,41.481,259.341,36.478,259.341z
        #                     "/>
        #             <path style="fill:#253744;" d="M24.318,289.132c-11.418,0-18.066-15.327-20.685-24.602c-1.566,2.771-1.976,6.658,0.225,11.696
        #                     c4.958,11.352,8.833,19.932,20.46,20.209c11.627-0.277,15.502-8.857,20.459-20.209c2.142-4.901,1.812-8.714,0.351-11.468
        #                     C42.604,273.646,35.931,289.132,24.318,289.132z"/>
        #             <path style="opacity:0.3;fill:#586A73;enable-background:new    ;" d="M11.884,264.53c0,0,6.045,7.59,12.435,8.275
        #                     c6.39,0.687,15.802-8.275,15.802-8.275H11.884z"/>
        #             </g>
        #             <path style="opacity:0.3;fill:#D1D5D5;enable-background:new    ;" d="M57.584,211.893c0,0-5.021,8.157,0,13.808
        #                 c5.021,5.649,13.023,3.139,13.023,3.139L57.584,211.893z"/>
        #             <path style="opacity:0.3;fill:#D1D5D5;enable-background:new    ;" d="M453.771,211.893c0,0,5.021,8.157,0,13.808
        #                 c-5.021,5.649-13.023,3.139-13.023,3.139L453.771,211.893z"/>
        #             <polygon style="opacity:0.3;fill:#586A73;enable-background:new    ;" points="74.959,78.446 71.368,189.551 87.855,189.551 
        #                 130.921,78.446 	"/>
        #             <polygon style="opacity:0.3;fill:#586A73;enable-background:new    ;" points="259.259,78.446 259.259,189.551 280.825,189.551 
        #                 314.045,78.446 	"/>
        #             <g>
        #             <path style="fill:#2D404E;" d="M43.771,437.258c0,0,1.008,29.345,1.008,45.399c0,16.056,3.091,29.344,23.981,29.344
        #                     s30.856,0.001,30.856-29.344s0-45.399,0-45.399H43.771z"/>
        #             <path style="fill:#253744;" d="M59.697,488.886c-0.393-10.786,0.61-39.724,0.61-39.724l39.31-5.976c0-3.885,0-5.929,0-5.929
        #                     H43.771c0,0,1.008,29.345,1.008,45.399C44.779,498.712,47.87,512,68.76,512c0.886,0,1.745-0.002,2.591-0.004
        #                     C60.251,507.175,59.996,497.125,59.697,488.886z"/>
        #             </g>
        #             <g>
        #             <path style="fill:#2D404E;" d="M468.23,437.258c0,0-1.008,29.345-1.008,45.399c0,16.056-3.091,29.344-23.981,29.344
        #                     s-30.856,0.001-30.856-29.344s0-45.399,0-45.399H468.23z"/>
        #             <path style="fill:#253744;" d="M452.303,488.886c0.393-10.786-0.609-39.724-0.609-39.724l-39.31-5.976c0-3.885,0-5.929,0-5.929
        #                     h55.846c0,0-1.008,29.345-1.008,45.399c0,16.056-3.091,29.344-23.981,29.344c-0.886,0-1.744-0.002-2.591-0.004
        #                     C451.75,507.175,452.005,497.125,452.303,488.886z"/>
        #             </g>
        #             <g>
        #             <polygon style="fill:#D89932;" points="67.859,310.597 56.865,318.209 99.616,347.981 104.926,310.597 		"/>
        #             <path style="fill:#586A73;" d="M99.616,347.981c0,2.753-2.231,4.983-4.983,4.983H60.306c-2.752,0-4.983-2.23-4.983-4.983v-26.175
        #                     c0-2.753,2.231-4.983,4.983-4.983h34.327c2.751,0,4.983,2.23,4.983,4.983V347.981z"/>
        #             <path style="opacity:0.3;fill:#C6CBCB;enable-background:new    ;" d="M60.307,316.823c-2.752,0-4.983,2.23-4.983,4.983v26.175
        #                     c0,2.753,2.231,4.983,4.983,4.983l34.327-36.142H60.307V316.823z"/>
        #             <path style="fill:#2D404E;" d="M59.559,347.128c0-3.473,0-15.847,0-22.94c0-3.568,1.375-5.914,2.742-7.364h-1.995
        #                     c-2.752,0-4.983,2.23-4.983,4.983v26.175c0,2.753,2.231,4.983,4.983,4.983h34.327c1.912,0,3.551-1.089,4.388-2.667
        #                     C70.194,350.311,59.559,350.494,59.559,347.128z"/>
        #             </g>
        #             <g>
        #             <polygon style="fill:#D89932;" points="444.142,310.597 455.137,318.209 412.385,347.981 407.077,310.597 		"/>
        #             <path style="fill:#586A73;" d="M412.385,347.981c0,2.753,2.231,4.983,4.983,4.983h34.326c2.752,0,4.982-2.23,4.982-4.983v-26.175
        #                     c0-2.753-2.23-4.983-4.982-4.983h-34.326c-2.752,0-4.983,2.23-4.983,4.983V347.981z"/>
        #             <path style="opacity:0.3;fill:#C6CBCB;enable-background:new    ;" d="M451.695,316.823c2.752,0,4.982,2.23,4.982,4.983v26.175
        #                     c0,2.753-2.23,4.983-4.982,4.983l-34.326-36.142h34.326V316.823z"/>
        #             <path style="fill:#2D404E;" d="M452.443,347.128c0-3.473,0-15.847,0-22.94c0-3.568-1.375-5.914-2.742-7.364h1.995
        #                     c2.752,0,4.982,2.23,4.982,4.983v26.175c0,2.753-2.23,4.983-4.982,4.983H417.37c-1.912,0-3.552-1.089-4.389-2.667
        #                     C441.807,350.311,452.443,350.494,452.443,347.128z"/>
        #             </g>
        #         </g>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         <g/>
        #         </svg>"""
        # },
        {
            "name": "Configuration",
            "flag": EAppGroupFlag.CONFIGURATION.value,
            "description_str": "Gestion des configurations",
            "order_by":5,
            "icon":"""<svg id="fi_1926354" enable-background="new 0 0 512 512" height="512" viewBox="0 0 512 512" width="512" xmlns="http://www.w3.org/2000/svg">
                <circle cx="204.666" cy="307.334" fill="#d3ced5" r="197.166"/>
                <path d="m272.168 122.027c53.979 35.175 89.663 96.074 89.663 165.307 0 108.892-88.274 197.166-197.166 197.166-23.711 0-46.445-4.186-67.502-11.859 30.92 20.149 67.844 31.859 107.502 31.859 108.892 0 197.166-88.274 197.166-197.166.001-85.18-54.016-157.744-129.663-185.307z" fill="#c3bec6"/>
                <path d="m376.832 321.059v-27.451c0-.563-.405-1.045-.959-1.143l-32.124-5.641c-.487-.086-.863-.473-.938-.962-1.552-10.07-4.173-19.787-7.754-29.027-.179-.461-.046-.982.333-1.299l24.98-20.931c.432-.362.541-.981.26-1.469l-13.725-23.773c-.282-.488-.873-.703-1.402-.51l-30.657 11.183c-.464.169-.981.023-1.291-.361-6.297-7.812-13.417-14.932-21.229-21.229-.385-.31-.531-.827-.361-1.291l11.183-30.657c.193-.529-.022-1.121-.51-1.402l-23.773-13.725c-.488-.282-1.107-.172-1.469.26l-20.931 24.98c-.318.379-.838.511-1.299.333-9.24-3.581-18.957-6.202-29.027-7.754-.489-.075-.876-.451-.962-.938l-5.641-32.124c-.097-.555-.579-.959-1.143-.959h-27.453c-.563 0-1.045.405-1.143.959l-5.641 32.124c-.086.487-.473.863-.962.938-10.07 1.552-19.787 4.173-29.027 7.754-.461.179-.982.046-1.299-.333l-20.931-24.98c-.362-.432-.981-.541-1.469-.26l-23.773 13.725c-.488.282-.703.873-.51 1.402l11.183 30.657c.169.464.023.981-.361 1.291-7.812 6.297-14.932 13.417-21.229 21.229-.31.385-.827.531-1.291.361l-30.657-11.183c-.529-.193-1.121.022-1.402.51l-13.725 23.773c-.282.488-.172 1.107.26 1.469l24.98 20.931c.379.318.511.838.333 1.299-3.581 9.24-6.202 18.957-7.754 29.027-.075.489-.451.876-.938.962l-32.124 5.641c-.555.097-.959.579-.959 1.143v27.451c0 .563.405 1.045.959 1.143l32.124 5.641c.487.086.863.473.938.962 1.552 10.07 4.173 19.787 7.754 29.027.179.461.046.982-.333 1.299l-24.98 20.931c-.432.362-.541.981-.26 1.469l13.725 23.773c.282.488.873.703 1.402.51l30.657-11.183c.464-.169.981-.023 1.291.361 6.297 7.812 13.417 14.932 21.229 21.229.385.31.531.827.361 1.291l-11.183 30.657c-.193.529.022 1.121.51 1.402l23.773 13.725c.488.282 1.107.172 1.469-.26l20.931-24.98c.318-.379.838-.511 1.299-.333 9.24 3.581 18.957 6.202 29.027 7.754.489.075.876.451.962.938l5.641 32.124c.097.555.579.959 1.143.959h27.451c.563 0 1.045-.405 1.143-.959l5.641-32.124c.086-.487.473-.863.962-.938 10.07-1.552 19.787-4.173 29.027-7.754.461-.179.982-.046 1.299.333l20.931 24.98c.362.432.981.541 1.469.26l23.773-13.725c.488-.282.703-.873.51-1.402l-11.183-30.657c-.169-.464-.023-.981.361-1.292 7.812-6.297 14.932-13.417 21.229-21.229.31-.385.827-.531 1.291-.361l30.657 11.183c.529.193 1.121-.022 1.402-.51l13.725-23.773c.282-.488.172-1.107-.26-1.469l-24.98-20.931c-.379-.318-.511-.838-.333-1.299 3.581-9.24 6.202-18.957 7.754-29.027.075-.489.451-.876.938-.962l32.124-5.641c.556-.096.961-.578.961-1.142z" fill="#93c8a5"/>
                <path d="m375.872 293.526-32.124-5.641c-.487-.086-.863-.473-.938-.962-1.552-10.07-4.173-19.787-7.754-29.027-.179-.461-.046-.982.333-1.299l24.98-20.931c.432-.362.541-.981.26-1.469l-13.725-23.773c-.282-.488-.873-.703-1.402-.51l-30.657 11.183c-.464.169-.981.023-1.292-.361-6.297-7.812-13.417-14.932-21.229-21.229-.385-.31-.531-.827-.361-1.292l11.183-30.657c.193-.529-.022-1.121-.51-1.402l-23.773-13.725c-.488-.282-1.108-.172-1.469.26l-20.931 24.98c-.318.379-.838.511-1.299.333-4.496-1.742-9.104-3.256-13.812-4.532 37.056 24.776 61.459 67 61.459 114.922 0 76.295-61.849 138.144-138.144 138.144-16.589 0-32.494-2.925-47.23-8.285-.007.107-.028.214-.067.319l-11.183 30.657c-.193.529.022 1.121.51 1.402l23.773 13.725c.488.282 1.107.172 1.469-.26l20.931-24.98c.318-.379.838-.511 1.299-.333 9.24 3.581 18.957 6.202 29.027 7.754.489.075.876.451.962.938l5.641 32.124c.097.555.579.959 1.143.959h27.451c.563 0 1.045-.405 1.143-.959l5.641-32.124c.086-.487.473-.863.962-.938 10.07-1.552 19.787-4.173 29.027-7.754.461-.179.982-.046 1.299.333l20.931 24.98c.362.432.981.541 1.469.26l23.773-13.725c.488-.282.703-.873.51-1.402l-11.183-30.657c-.169-.464-.023-.981.361-1.292 7.812-6.297 14.932-13.417 21.229-21.229.31-.385.827-.531 1.291-.361l30.657 11.183c.529.193 1.121-.022 1.402-.51l13.725-23.773c.282-.488.172-1.107-.26-1.469l-24.98-20.931c-.379-.318-.511-.838-.333-1.3 3.58-9.24 6.202-18.957 7.754-29.026.075-.489.451-.876.938-.962l32.124-5.641c.555-.097.959-.579.959-1.143v-27.45c0-.563-.405-1.045-.96-1.142z" fill="#80bc93"/>
                <circle cx="453.525" cy="58.475" fill="#d3ced5" r="50.975"/>
                <path d="m204.666 110.168c13.55 0 26.781 1.367 39.562 3.971l158.435-59.069c1.306-19.81 13.929-36.527 31.463-43.749-30.74 11.461-295.942 110.336-295.942 110.336 20.771-7.437 43.153-11.489 66.482-11.489z" fill="#958b95"/>
                <path d="m456.93 109.337-59.069 158.435c2.604 12.781 3.971 26.012 3.971 39.562 0 23.328-4.052 45.71-11.49 66.481l110.335-295.94c-7.221 17.534-23.938 30.156-43.747 31.462z" fill="#958b95"/>
                <circle cx="204.666" cy="307.334" fill="#69af81" r="105.13"/>
                <path d="m300.782 264.678c1.333 7.705 2.028 15.629 2.028 23.716 0 51.608-28.299 96.606-70.226 120.323 44.511-12.229 77.212-52.987 77.212-101.382 0-15.187-3.22-29.62-9.014-42.657z" fill="#69af81"/>
                <circle cx="204.666" cy="307.334" fill="#93c8a5" r="50.975"/>
                <path d="m223.103 317.014v-19.359c0-.597-.319-1.149-.836-1.448l-16.765-9.679c-.517-.299-1.155-.299-1.672 0l-16.765 9.679c-.517.299-.836.851-.836 1.448v19.359c0 .597.319 1.149.836 1.448l16.765 9.68c.517.299 1.155.299 1.672 0l16.765-9.68c.518-.299.836-.851.836-1.448z" fill="#d3ced5"/>
                <path d="m471.963 68.154v-19.359c0-.597-.319-1.149-.836-1.448l-16.765-9.679c-.517-.299-1.155-.299-1.672 0l-16.765 9.679c-.517.299-.836.851-.836 1.448v19.359c0 .597.319 1.149.836 1.448l16.765 9.679c.517.299 1.155.299 1.672 0l16.765-9.679c.517-.299.836-.851.836-1.448z" fill="#b4acb7"/>
                <path d="m512 58.475c0-32.244-26.231-58.475-58.475-58.475-7.712 0-15.08 1.501-21.828 4.226-.064.022-.128.044-.192.068l-294.425 109.771c-27.682 9.664-53.164 25.298-74.779 46.23-2.976 2.882-3.052 7.63-.17 10.605 2.881 2.975 7.629 3.052 10.605.17 19.708-19.085 42.885-33.418 68.061-42.405l.007.019 1.106-.412c19.927-6.972 41.086-10.604 62.755-10.604 104.582 0 189.666 85.084 189.666 189.666s-85.083 189.666-189.665 189.666-189.666-85.084-189.666-189.666c0-40.078 12.346-78.388 35.702-110.788 2.422-3.36 1.662-8.048-1.698-10.47-3.357-2.42-8.047-1.662-10.47 1.698-25.209 34.971-38.534 76.314-38.534 119.56 0 112.854 91.813 204.666 204.666 204.666 88.621 0 164.304-56.602 192.704-135.564l37.125-99.576c1.447-3.881-.526-8.2-4.407-9.647-3.879-1.449-8.2.525-9.647 4.407l-11.187 30.005c-.312-11.318-1.547-22.409-3.632-33.201l56.722-152.138c6.489-.986 12.631-3.042 18.24-5.982l-47.636 127.77c-1.447 3.881.526 8.2 4.407 9.647 3.881 1.449 8.201-.528 9.647-4.407 61.845-168.531 64.998-166.925 64.998-184.839zm-15 0c0 24.631-20.242 43.475-43.475 43.475-24.288 0-44.932-20.261-43.374-46.44 1.53-22.595 20.399-40.51 43.374-40.51 23.972 0 43.475 19.503 43.475 43.475zm-95.303-27.059c-2.94 5.609-4.996 11.751-5.982 18.24l-152.14 56.721c-10.791-2.085-21.882-3.32-33.199-3.631zm-132.863 81.553 126.667-47.224c3.294 26.443 24.312 47.461 50.754 50.754l-47.225 126.665c-20.298-61.328-68.868-109.897-130.196-130.195z"/>
                <path d="m204.666 419.964c62.104 0 112.63-50.525 112.63-112.63s-50.525-112.63-112.63-112.63c-4.143 0-7.5 3.357-7.5 7.5s3.357 7.5 7.5 7.5c53.833 0 97.63 43.797 97.63 97.63s-43.797 97.63-97.63 97.63-97.63-43.797-97.63-97.63c0-41.003 25.895-77.912 64.437-91.844 3.896-1.408 5.912-5.708 4.504-9.604-1.409-3.896-5.709-5.908-9.604-4.504-44.463 16.073-74.337 58.651-74.337 105.951 0 62.105 50.526 112.631 112.63 112.631z"/>
                <path d="m146.191 307.334c0 32.243 26.231 58.475 58.475 58.475s58.475-26.231 58.475-58.475-26.231-58.475-58.475-58.475-58.475 26.232-58.475 58.475zm58.475-43.475c23.972 0 43.475 19.503 43.475 43.475s-19.503 43.475-43.475 43.475-43.475-19.503-43.475-43.475 19.503-43.475 43.475-43.475z"/>
                <path d="m183.314 324.957 16.77 9.682c1.411.814 2.994 1.222 4.579 1.222s3.171-.408 4.589-1.224l16.771-9.683c2.826-1.635 4.581-4.677 4.581-7.94v-19.359c0-3.269-1.759-6.313-4.586-7.942l-16.766-9.68c-2.83-1.635-6.348-1.635-9.172 0l-16.757 9.675c-2.834 1.631-4.595 4.676-4.595 7.947v19.359c.001 3.266 1.757 6.31 4.586 7.943zm10.415-23.937 10.938-6.314 10.938 6.314v12.63l-10.938 6.314-10.938-6.314z"/>
                <path d="m432.174 76.098 16.766 9.679c2.828 1.633 6.344 1.633 9.172 0l16.766-9.679c2.829-1.633 4.586-4.677 4.586-7.943v-19.36c0-3.267-1.757-6.311-4.586-7.943l-16.766-9.679c-2.828-1.633-6.344-1.633-9.172 0l-16.766 9.679c-2.829 1.633-4.586 4.677-4.586 7.943v19.359c0 3.267 1.757 6.311 4.586 7.944zm10.414-23.939 10.938-6.313 10.938 6.313v12.631l-10.938 6.313-10.938-6.313z"/>
                <path d="m44.146 240.356 21.552 18.058c-2.491 7.087-4.441 14.387-5.822 21.799l-27.718 4.866c-4.147.73-7.158 4.317-7.158 8.529v27.451c0 4.212 3.011 7.799 7.162 8.529l27.714 4.866c1.381 7.413 3.331 14.714 5.822 21.8l-21.55 18.056c-3.231 2.705-4.048 7.318-1.94 10.97l13.722 23.767c2.106 3.656 6.51 5.259 10.472 3.813l26.458-9.651c4.896 5.702 10.232 11.039 15.933 15.933l-9.648 26.451c-1.45 3.961.15 8.366 3.803 10.475l23.774 13.727c3.649 2.105 8.264 1.289 10.967-1.939l18.059-21.552c7.086 2.491 14.385 4.441 21.799 5.822l4.866 27.718c.73 4.147 4.317 7.158 8.529 7.158h27.451c4.212 0 7.799-3.011 8.529-7.162l4.866-27.714c7.411-1.381 14.711-3.33 21.799-5.822l18.057 21.55c2.703 3.229 7.313 4.047 10.97 1.94l23.766-13.722c3.65-2.103 5.256-6.503 3.813-10.472l-9.652-26.458c5.701-4.894 11.036-10.229 15.933-15.933l26.456 9.65c3.954 1.445 8.355-.151 10.471-3.805l13.727-23.774c2.106-3.65 1.29-8.264-1.939-10.967l-21.553-18.059c2.493-7.088 4.443-14.391 5.822-21.799l27.718-4.866c4.148-.73 7.159-4.317 7.159-8.529v-27.451c0-4.212-3.011-7.799-7.163-8.529l-27.714-4.866c-1.38-7.411-3.33-14.711-5.822-21.798l21.559-18.063c3.222-2.704 4.036-7.313 1.933-10.964l-13.728-23.775c-2.108-3.648-6.509-5.249-10.466-3.803l-26.458 9.651c-4.895-5.701-10.229-11.037-15.934-15.934l9.65-26.455c1.445-3.957-.153-8.36-3.805-10.471l-23.779-13.729c-3.643-2.098-8.251-1.286-10.962 1.942l-18.059 21.553c-7.089-2.493-14.391-4.443-21.798-5.822l-4.865-27.705c-.725-4.155-4.313-7.172-8.531-7.172h-27.45c-4.212 0-7.799 3.011-8.529 7.163l-4.866 27.714c-7.414 1.38-14.717 3.331-21.799 5.822l-18.057-21.551c-2.706-3.232-7.317-4.049-10.97-1.94l-23.782 13.73c-3.644 2.11-5.24 6.512-3.797 10.463l9.651 26.458c-5.702 4.895-11.038 10.231-15.933 15.934l-26.455-9.65c-3.964-1.449-8.369.154-10.471 3.805l-13.729 23.779c-2.102 3.643-1.287 8.251 1.94 10.96zm22.116-22.63 25.659 9.359c3.472 1.268 7.371.183 9.698-2.702 5.952-7.385 12.713-14.146 20.09-20.092 2.893-2.327 3.979-6.231 2.706-9.705l-9.358-25.656 14.552-8.401 17.512 20.899c2.374 2.836 6.294 3.849 9.759 2.51 8.819-3.418 18.058-5.886 27.47-7.336 3.661-.57 6.552-3.402 7.195-7.053l4.721-26.881h16.803l4.719 26.872c.637 3.652 3.529 6.49 7.208 7.063 9.4 1.449 18.639 3.917 27.471 7.34 3.454 1.333 7.372.32 9.746-2.515l17.512-20.899 14.552 8.401-9.359 25.66c-1.268 3.479-.18 7.378 2.702 9.697 7.384 5.951 14.145 12.712 20.092 20.091 2.323 2.888 6.221 3.975 9.705 2.706l25.656-9.358 8.401 14.552-20.899 17.512c-2.841 2.38-3.85 6.302-2.51 9.758 3.418 8.82 5.886 18.059 7.336 27.47.571 3.668 3.409 6.561 7.053 7.195l26.881 4.721v16.803l-26.887 4.722c-3.645.643-6.477 3.533-7.048 7.205-1.449 9.401-3.917 18.64-7.335 27.458-1.34 3.457-.332 7.38 2.51 9.76l20.899 17.512-8.401 14.552-25.646-9.354c-3.484-1.276-7.387-.19-9.71 2.696-5.952 7.384-12.714 14.146-20.102 20.1-2.877 2.322-3.962 6.216-2.696 9.698l9.359 25.654-14.553 8.402-17.518-20.907c-2.381-2.834-6.298-3.842-9.752-2.501-8.82 3.417-18.06 5.885-27.456 7.334-3.675.565-6.573 3.403-7.209 7.054l-4.722 26.878h-16.805l-4.721-26.887c-.644-3.651-3.541-6.484-7.205-7.047-9.401-1.45-18.64-3.918-27.458-7.335-3.459-1.341-7.381-.331-9.76 2.509l-17.512 20.899-14.552-8.401 9.354-25.646c1.274-3.479.192-7.38-2.696-9.711-7.384-5.952-14.145-12.713-20.1-20.101-2.326-2.882-6.224-3.965-9.698-2.696l-25.655 9.358-8.401-14.552 20.901-17.51c2.839-2.378 3.848-6.298 2.509-9.759-3.417-8.819-5.885-18.059-7.334-27.456-.563-3.667-3.396-6.564-7.054-7.209l-26.881-4.72v-16.805l26.872-4.718c3.659-.638 6.497-3.536 7.062-7.208 1.45-9.399 3.918-18.639 7.335-27.458 1.34-3.457.332-7.379-2.509-9.759l-20.9-17.511z"/>
                </svg>"""
        },
        
    ]
    for appg in app_groups:
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_APPLICATION_GROUP, filter_data={"flag": appg['flag']}, update_data=appg)
            print(f"upserted app group result : {result}.")
        except ValueError as e:
            print(f"Error: {e}")
        except PermissionError as e:
            print(f"Permission Error: {e}")


async def create_api_consumers():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default API consumers if they do not already exist.
    """
    # Make sure to `await` find_one()
    api_consumers = [
        # Senat-Digit first-party consumers
        {
            "name": "Senat-Digit Mobile (Flutter)",
            "restricted": False,
            "flag": EApiConsumerFlag.SENAT_DIGIT_MOBILE.value,
            "meta": "Dart",
            "can_receive_totp_validation_push": True,
            "is_default": False,
        },
        {
            "name": "Senat-Digit Admin (Angular)",
            "restricted": False,
            "flag": EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
            "meta": "Web",
            "is_default": True,
        },
        {
            "name": "Senat-Digit FS (Server-to-Server)",
            "restricted": True,
            "flag": EApiConsumerFlag.SENAT_DIGIT_FS.value,
            "meta": "server",
            "is_default": False,
        },
        # Utility consumers
        {
            "name": "postman",
            "restricted": False,
            "flag": EApiConsumerFlag.CLIENT_POSTMAN.value,
            "meta": "PostmanRuntime",
            "is_default": False,
        },
        {
            "name": "Senat-Digit MFA validation (Flutter)",
            "flag": EApiConsumerFlag.FLUTTER_VALIDATION_AND_TOTP_MFA_APPS.value,
            "restricted": False,
            "can_receive_totp_validation_push": True,
            "meta": "mobile",
            "is_default": False,
        },
    ]
    for index, api in enumerate(api_consumers):
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_API_CONSUMER, filter_data={"flag": api['flag']}, update_data=api)
            print(f"upserted result : {result}. index : {index}")
        except ValueError as e:
            print(f"Error ADDING CONSUMER 1: {e}")
        except PermissionError as e:
            print(f"Error ADDING CONSUMER 2 : {e}")

 
async def create_mfas():
    from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
    rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default mfas records if they do not already exist.
    """
    mfas = [
        {
            "name": "Vérification par e-mail",
            "usage_description": "Un e-mail d'autentification vous sera envoyé à votre boîte e-mail",
            "config_description": "Configurez une adresse e-mail pour recevoir le code d'autentification",
            "is_default": True,
            "purpose": EMfaPurpose.LOGIN_AND_RESET_PASSWORD.value,
            "flag": MFaFlag.EMAIL.value,
            "svg_icon": """<svg version="1.1" id="fi_482138" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 512 512" style="enable-background:new 0 0 512 512;" xml:space="preserve">
                <g>
                    <g>
                        <path d="M405.333,213.874V106.667c0-23.531-19.135-42.667-42.667-42.667h-320C19.135,64,0,83.135,0,106.667V320
                            c0,23.531,19.135,42.667,42.667,42.667h239.215C295.858,411.84,341.073,448,394.667,448c20.625,0,40.906-5.427,58.677-15.708
                            c5.094-2.948,6.844-9.469,3.885-14.573c-2.948-5.104-9.479-6.865-14.573-3.885c-14.521,8.396-31.115,12.833-47.99,12.833
                            c-52.938,0-96-43.063-96-96s43.063-96,96-96s96,43.063,96,96v10.667c0,11.76-9.573,21.333-21.333,21.333
                            c-11.76,0-21.333-9.573-21.333-21.333v-42.667c0-5.896-4.771-10.667-10.667-10.667c-2.869,0-5.447,1.161-7.362,3
                            c-9.428-8.401-21.714-13.667-35.305-13.667c-29.406,0-53.333,23.927-53.333,53.333S365.26,384,394.667,384
                            c15.896,0,30.03-7.131,39.81-18.202c7.727,10.977,20.44,18.202,34.857,18.202C492.865,384,512,364.865,512,341.333v-10.667
                            C512,269.569,465.044,219.288,405.333,213.874z M42.667,85.333h320c0.444,0,0.816,0.227,1.254,0.254L211.438,210.75
                            c-5.427,3.417-13.292,2.708-16.823,0.542L41.426,85.585C41.859,85.559,42.227,85.333,42.667,85.333z M384,213.874
                            c-59.711,5.414-106.667,55.695-106.667,116.793c0,3.6,0.221,7.148,0.54,10.667H42.667c-11.76,0-21.333-9.573-21.333-21.333
                            V106.667c0-3.021,0.667-5.874,1.805-8.48l158.883,130.293c6.208,4.052,13.344,6.188,20.646,6.188
                            c7.021,0,13.885-1.979,19.927-5.729c0.604-0.323,1.177-0.708,1.719-1.156l157.88-129.598c1.139,2.608,1.807,5.461,1.807,8.483
                            V213.874z M394.667,362.667c-17.646,0-32-14.354-32-32c0-17.646,14.354-32,32-32s32,14.354,32,32
                            C426.667,348.313,412.313,362.667,394.667,362.667z"></path>
                    </g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                <g>
                </g>
                </svg>
            """
        },
        {
            "name": "Vérification par SMS",
            "usage_description": "Un code d'autentification vous sera envoyé à votre numéro de téléphone",
            "config_description": "Configurez un numéro de téléphone pour recevoir le code d'autentification",
            "is_default": True,
            "purpose": EMfaPurpose.LOGIN_AND_RESET_PASSWORD.value,
            "flag": MFaFlag.PHONE_NUMBER.value,
            "svg_icon": """<svg xmlns="http://www.w3.org/2000/svg" id="fi_4121823" data-name="Layer 1" viewBox="0 0 256 256" width="512" height="512"><path d="M71.215,215.155a4,4,0,0,1-3.94-4.719c7.832-42.887-9.4-68.372-9.579-68.624a4.015,4.015,0,0,1-.066-4.477c2.561-3.918,4.416-15.276,4.511-27.622.116-15.27-2.375-22.627-3.53-23.639A10.582,10.582,0,0,0,48.681,85a7.355,7.355,0,0,0-4.61,5.935c-.778,5.062-3.188,12.234-5.978,20.54-3.078,9.163-6.568,19.548-8.211,28.386a177.97,177.97,0,0,0-2.689,32.232,4,4,0,0,1-1.015,2.761L10.508,192.4a4,4,0,1,1-5.967-5.329l14.636-16.386a184.2,184.2,0,0,1,2.84-32.284c1.747-9.39,5.331-20.058,8.493-29.471,2.561-7.625,4.98-14.826,5.655-19.209a15.375,15.375,0,0,1,9.427-12.1,18.6,18.6,0,0,1,17.727,1.985c9.464,6.835,8.189,46.059,2.258,59.724,4.276,7.283,16.812,32.877,9.568,72.542A4,4,0,0,1,71.215,215.155Z"></path><path d="M64.388,251.1a4,4,0,0,1-2.881-6.775l13.644-14.168A4,4,0,0,1,78.77,229c.147.028,15.7,2.785,28.959-3.844.2-.1,13.562-6.608,18.228-17.945a4,4,0,0,1,7.4,3.045c-5.857,14.232-21.459,21.777-22.121,22.091-12.606,6.3-26.455,5.471-31.744,4.838l-12.221,12.69A3.99,3.99,0,0,1,64.388,251.1Z"></path><path d="M175.661,118.532a4,4,0,0,1-4-4v-96.8c0-5.3-5.111-9.607-11.394-9.607h-83.9c-6.284,0-11.4,4.31-11.4,9.607V82.85a4,4,0,0,1-8,0V17.729c0-9.708,8.7-17.607,19.4-17.607h83.9c10.694,0,19.394,7.9,19.394,17.607v96.8A4,4,0,0,1,175.661,118.532Z"></path><path d="M106.063,207.485H73.8a4,4,0,0,1,0-8h32.268a4,4,0,0,1,0,8Z"></path><path d="M175.028,29.673H61.258a4,4,0,0,1,0-8h113.77a4,4,0,0,1,0,8Z"></path><path d="M93.553,184.747H74.683a4,4,0,1,1,0-8h18.87a4,4,0,0,1,0,8Z"></path><path d="M178.769,255.879a4,4,0,0,1-3.665-2.392l-3.542-8.064-21.128-9.642a4.036,4.036,0,0,1-1.227-.871l-40.348-42.092q-.064-.068-.126-.138c-.545-.624-5.264-6.266-3.379-12.162,1.209-3.786,4.615-6.373,10.12-7.689,9.744-2.329,21.675,4.472,29.541,10.167l-32.4-73.751a14.877,14.877,0,0,1-.359-11.207,14.155,14.155,0,0,1,7.623-8.129,14.624,14.624,0,0,1,19.153,7.731,4,4,0,0,1-7.324,3.218,6.622,6.622,0,0,0-8.612-3.625,6.228,6.228,0,0,0-3.338,3.584,6.915,6.915,0,0,0,.181,5.21l35.233,80.207a4,4,0,0,1,.26,2.4l-.962,4.79a4,4,0,0,1-6.64,2.148c-5.32-4.916-21.179-17.2-30.5-14.958-2.875.687-4.136,1.658-4.357,2.337-.355,1.087.791,3.274,1.746,4.426l39.73,41.448,21.819,9.957a4,4,0,0,1,2,2.031l4.157,9.46a4,4,0,0,1-3.66,5.61Z"></path><path d="M165.188,171.117a4,4,0,0,1-3.665-2.392l-29.812-67.867a4,4,0,0,1,7.324-3.218l29.813,67.867a4,4,0,0,1-3.66,5.61Z"></path><path d="M155.483,149.026a4,4,0,0,1-3.664-2.391,14.877,14.877,0,0,1-.359-11.207,14.186,14.186,0,0,1,18.766-8.244,14.879,14.879,0,0,1,8.009,7.846,4,4,0,1,1-7.324,3.217,6.914,6.914,0,0,0-3.714-3.658,6.187,6.187,0,0,0-8.235,3.618,6.908,6.908,0,0,0,.182,5.209,4,4,0,0,1-3.661,5.61Z"></path><path d="M185.02,164.416a4,4,0,0,1-3.665-2.393l-10.444-23.775a4,4,0,0,1,7.324-3.218l10.445,23.776a4,4,0,0,1-3.66,5.61Z"></path><path d="M178.353,149.236a4,4,0,0,1-3.665-2.391,14.877,14.877,0,0,1-.359-11.207,14.184,14.184,0,0,1,18.766-8.244,14.876,14.876,0,0,1,8.009,7.846,4,4,0,1,1-7.324,3.217,6.914,6.914,0,0,0-3.714-3.658,6.185,6.185,0,0,0-8.235,3.618,6.908,6.908,0,0,0,.182,5.209,4,4,0,0,1-3.66,5.61Z"></path><path d="M205.992,160.307a4,4,0,0,1-3.664-2.392l-8.548-19.457a4,4,0,0,1,7.324-3.218l8.548,19.457a4,4,0,0,1-3.66,5.61Z"></path><path d="M201.059,149.076a4,4,0,0,1-3.664-2.392,14.431,14.431,0,1,1,26.417-11.6,4,4,0,1,1-7.325,3.219,6.436,6.436,0,1,0-11.768,5.169,4,4,0,0,1-3.66,5.609Z"></path><path d="M248.478,226.778a4,4,0,0,1-3.665-2.392l-3.854-8.775a4,4,0,0,1-.33-1.865l1.147-17.877L216.487,138.3a4,4,0,0,1,7.325-3.217l25.681,58.463a4,4,0,0,1,.33,1.866l-1.147,17.877,3.462,7.882a4,4,0,0,1-3.66,5.61Z"></path>
                    </svg>
            """
        },
        {
            "name": "pass code",
            "usage_description": "Le code à usage unique d'autentification",
            "config_description": "Télécharger les codes à usage unique à utiliser lors de l'autentification",
            "is_default": False,
            "purpose": EMfaPurpose.LOGIN_ONLY.value,
            "flag": MFaFlag.PASS_CODE.value,
            "is_activated": False,
            "svg_icon": """<svg height="512" viewBox="0 0 60 60" width="512" xmlns="http://www.w3.org/2000/svg" id="fi_3257787"><g id="Page-1" fill="none" fill-rule="evenodd"><g id="010---Secure-Password" fill="rgb(0,0,0)" fill-rule="nonzero"><path id="Shape" d="m3 49h5v6c.00330612 2.7600532 2.2399468 4.9966939 5 5h34c2.7600532-.0033061 4.9966939-2.2399468 5-5v-6h5c1.6568542 0 3-1.3431458 3-3v-10c0-1.6568542-1.3431458-3-3-3h-5v-6c-.0033061-2.7600532-2.2399468-4.9966939-5-5v-5c0-9.38884075-7.6111593-17-17-17s-17 7.61115925-17 17v5c-2.7600532.0033061-4.99669388 2.2399468-5 5v6h-5c-1.65685425 0-3 1.3431458-3 3v10c0 1.6568542 1.34314575 3 3 3zm47 6c0 1.6568542-1.3431458 3-3 3h-34c-1.6568542 0-3-1.3431458-3-3v-6h40zm-35-38c0-8.28427125 6.7157288-15 15-15s15 6.71572875 15 15v5h-4v-5c0-6.0751322-4.9248678-11-11-11s-11 4.9248678-11 11v5h-4zm6 5v-5c0-4.9705627 4.0294373-9 9-9s9 4.0294373 9 9v5zm-11 5c0-1.6568542 1.3431458-3 3-3h34c1.6568542 0 3 1.3431458 3 3v6h-40zm-8 9c0-.5522847.44771525-1 1-1h54c.5522847 0 1 .4477153 1 1v10c0 .5522847-.4477153 1-1 1h-54c-.55228475 0-1-.4477153-1-1z"></path><path id="Shape" d="m4.168 43.555c.1471733.2206869.37599843.3738581.63612132.4258077.26012289.0519495.53022847-.0015795.75087868-.1488077l1.445-.964v1.132c0 .5522847.44771525 1 1 1s1-.4477153 1-1v-1.132l1.445.964c.297245.1982824.6776931.2229246.9980332.0646441s.5319049-.4754371.555-.832-.1457882-.6983617-.4430332-.8966441l-1.755-1.168 1.752-1.168c.297245-.1982824.4661283-.5400812.4430332-.8966441s-.2346599-.6737195-.555-.832-.7007882-.1336383-.9980332.0646441l-1.442.964v-1.132c0-.5522847-.44771525-1-1-1s-1 .4477153-1 1v1.132l-1.445-.964c-.45950091-.306518-1.08048193-.1825009-1.38699996.277s-.18250092 1.080482.27699996 1.387l1.755 1.168-1.755 1.168c-.22068687.1471733-.37385812.3759984-.42580768.6361213s.00157944.5302285.14880768.7508787z"></path><path id="Shape" d="m15.168 43.555c.1471733.2206869.3759984.3738581.6361213.4258077.2601229.0519495.5302285-.0015795.7508787-.1488077l1.445-.964v1.132c0 .5522847.4477153 1 1 1s1-.4477153 1-1v-1.132l1.445.964c.297245.1982824.6776931.2229246.9980332.0646441s.5319049-.4754371.555-.832-.1457882-.6983617-.4430332-.8966441l-1.755-1.168 1.752-1.168c.297245-.1982824.4661283-.5400812.4430332-.8966441s-.2346599-.6737196-.555-.832c-.3203401-.1582805-.7007882-.1336383-.9980332.0646441l-1.442.964v-1.132c0-.5522847-.4477153-1-1-1s-1 .4477153-1 1v1.132l-1.445-.964c-.4595009-.306518-1.0804819-.1825009-1.387.277-.306518.4595009-.1825009 1.080482.277 1.387l1.755 1.168-1.752 1.168c-.2211743.1467018-.3749585.3753094-.4274774.6354656s.0005358.5305193.1474774.7515344z"></path><path id="Shape" d="m37.168 43.555c.1471733.2206869.3759984.3738581.6361213.4258077.2601229.0519495.5302285-.0015795.7508787-.1488077l1.445-.964v1.132c0 .5522847.4477153 1 1 1s1-.4477153 1-1v-1.132l1.445.964c.297245.1982824.6776931.2229246.9980332.0646441.32034-.1582805.5319049-.4754371.555-.832s-.1457882-.6983617-.4430332-.8966441l-1.755-1.168 1.752-1.168c.297245-.1982824.4661283-.5400812.4430332-.8966441s-.23466-.6737195-.555-.832c-.3203401-.1582805-.7007882-.1336383-.9980332.0646441l-1.442.964v-1.132c0-.5522847-.4477153-1-1-1s-1 .4477153-1 1v1.132l-1.445-.964c-.4595009-.306518-1.0804819-.1825009-1.3869999.277-.3065181.4595009-.182501 1.0804819.2769999 1.387l1.755 1.168-1.752 1.168c-.2211743.1467018-.3749585.3753094-.4274774.6354656s.0005358.5305193.1474774.7515344z"></path><path id="Shape" d="m26.168 43.555c.1471733.2206869.3759984.3738581.6361213.4258077.2601229.0519495.5302285-.0015795.7508787-.1488077l1.445-.964v1.132c0 .5522847.4477153 1 1 1s1-.4477153 1-1v-1.132l1.445.964c.297245.1982824.6776931.2229246.9980332.0646441.3203401-.1582804.5319049-.4754371.555-.832s-.1457882-.6983617-.4430332-.8966441l-1.755-1.168 1.752-1.168c.297245-.1982824.4661283-.5400812.4430332-.8966441s-.2346599-.6737196-.555-.832c-.3203401-.1582805-.7007882-.1336383-.9980332.0646441l-1.442.964v-1.132c0-.5522847-.4477153-1-1-1s-1 .4477153-1 1v1.132l-1.445-.964c-.4595009-.306518-1.0804819-.1825009-1.387.277-.306518.4595009-.1825009 1.080482.277 1.387l1.755 1.168-1.752 1.168c-.2211743.1467018-.3749585.3753094-.4274774.6354656s.0005358.5305193.1474774.7515344z"></path><path id="Shape" d="m16 26h-3c-.5522847 0-1 .4477153-1 1v3c0 .5522847.4477153 1 1 1s1-.4477153 1-1v-2h2c.5522847 0 1-.4477153 1-1s-.4477153-1-1-1z"></path><path id="Shape" d="m49 45h6c.5522847 0 1-.4477153 1-1s-.4477153-1-1-1h-6c-.5522847 0-1 .4477153-1 1s.4477153 1 1 1z"></path></g></g>
                    </svg>
            """
        },
        {
            "name": "application tierse d'authentification à deux facteurs",
            "usage_description": "L'application d'autentification tierce Ex=GOOGLE AUTHENTIFICATION",
            "config_description": "Configurer l'application d'autentification tierce Ex=GOOGLE AUTHENTIFICATION",
            "is_default": False,
            "purpose": EMfaPurpose.LOCKED_SCREEN_AND_LOGIN.value,
            "flag": MFaFlag.COMMON_2FA_APP.value,
            "is_activated": False,
            "svg_icon": """<svg clip-rule="evenodd" fill-rule="evenodd" stroke-linejoin="round" stroke-miterlimit="2" viewBox="0 0 510 510" xmlns="http://www.w3.org/2000/svg" id="fi_17363445"><g><g><path d="m255 283.831c-38.722-12.119-81.822-53.388-81.822-95.799 0 0 0-52.178.008-67.36 0-2.366 1.661-4.407 3.977-4.887 19.403-4.166 37.679-12.688 54.157-23.851h47.373c16.465 11.163 34.741 19.685 54.145 23.843 2.321.481 3.984 2.526 3.984 4.895v67.36c0 42.424-43.1 83.68-81.822 95.799zm44.031-110.558c0-1.326-.527-2.598-1.464-3.536-.938-.937-2.21-1.464-3.536-1.464h-78.062c-1.326 0-2.598.527-3.536 1.464-.937.938-1.464 2.21-1.464 3.536v32.52c0 9.262 3.916 18.144 10.885 24.694 6.97 6.549 16.424 10.228 26.28 10.228h13.732c9.856 0 19.31-3.679 26.28-10.228 6.969-6.55 10.885-15.432 10.885-24.694z" fill="#a4d4ff"></path><g><circle cx="255" cy="204.494" fill="#a4d4ff" r="11.183"></circle></g><g fill="#a4d4ff"><circle cx="34.925" cy="102.641" r="19.925"></circle><circle cx="475.075" cy="102.641" r="19.925"></circle><circle cx="475.075" cy="179.085" r="19.925"></circle><circle cx="475.075" cy="255.529" r="19.925"></circle><circle cx="34.925" cy="179.085" r="19.925"></circle><circle cx="34.925" cy="255.529" r="19.925"></circle></g><g><path d="m348.151 318.008c0-2.527-1.004-4.951-2.791-6.738-1.787-1.786-4.211-2.79-6.738-2.79-31.979 0-135.265 0-167.244 0-2.527 0-4.951 1.004-6.738 2.79-1.787 1.787-2.791 4.211-2.791 6.738v52.907c0 2.527 1.004 4.95 2.791 6.737s4.211 2.791 6.738 2.791h167.244c2.527 0 4.951-1.004 6.738-2.791s2.791-4.21 2.791-6.737c0-13.78 0-39.127 0-52.907z" fill="#a4d4ff"></path></g></g><path d="m60.929 109.641c-3.085 11.471-13.565 19.924-26.004 19.924-14.86 0-26.925-12.064-26.925-26.924s12.065-26.925 26.925-26.925c12.439 0 22.919 8.454 26.004 19.925h35.198c3.866 0 7 3.134 7 7v24.046h24.217v-50.038c0-20.505 16.806-37.284 37.325-37.284h180.637c20.548 0 37.35 16.781 37.35 37.284v50.038h24.19l-.09-24.02c-.007-1.861.727-3.648 2.041-4.967 1.313-1.318 3.098-2.059 4.959-2.059h35.315c3.085-11.471 13.565-19.925 26.004-19.925 14.86 0 26.925 12.065 26.925 26.925s-12.065 26.924-26.925 26.924c-12.439 0-22.919-8.453-26.004-19.924h-28.289l.091 24.019c.007 1.861-.728 3.649-2.041 4.967-1.314 1.318-3.098 2.06-4.959 2.06h-31.217v31.527h66.381c3.04-11.536 13.553-20.054 26.038-20.054 14.86 0 26.925 12.065 26.925 26.925s-12.065 26.924-26.925 26.924c-12.392 0-22.84-8.39-25.969-19.795h-66.45v31.786h31.217c1.862 0 3.647.742 4.96 2.061 1.314 1.32 2.048 3.109 2.04 4.97l-.106 23.498h28.304c3.085-11.471 13.565-19.925 26.004-19.925 14.86 0 26.925 12.065 26.925 26.925s-12.065 26.924-26.925 26.924c-12.439 0-22.919-8.453-26.004-19.924h-35.336c-1.862 0-3.647-.742-4.96-2.062-1.314-1.319-2.048-3.108-2.04-4.97l.106-23.497h-24.185v201.351c0 20.503-16.802 37.284-37.35 37.284h-180.637c-20.519 0-37.325-16.779-37.325-37.284v-201.351h-24.217v23.529c0 3.866-3.134 7-7 7h-35.198c-3.085 11.471-13.565 19.924-26.004 19.924-14.86 0-26.925-12.064-26.925-26.924s12.065-26.925 26.925-26.925c12.439 0 22.919 8.454 26.004 19.925h28.198v-23.529c0-3.866 3.134-7 7-7h31.217v-31.786h-66.45c-3.129 11.405-13.577 19.795-25.969 19.795-14.86 0-26.925-12.064-26.925-26.924s12.065-26.925 26.925-26.925c12.485 0 22.998 8.518 26.038 20.054h66.381v-31.527h-31.217c-3.866 0-7-3.134-7-7v-24.046zm-13.08-7c0-7.133-5.791-12.925-12.924-12.925-7.134 0-12.925 5.792-12.925 12.925s5.791 12.924 12.925 12.924c7.133 0 12.924-5.791 12.924-12.924zm320.807 24.046v-50.038c0-12.811-10.511-23.284-23.35-23.284h-180.637c-12.818 0-23.325 10.474-23.325 23.284v50.038h24.834v-10.111c0-3.382 2.418-6.281 5.745-6.887 19.933-3.632 38.674-12.171 55.471-23.55 1.158-.785 2.526-1.205 3.926-1.205h47.373c1.401 0 2.769.42 3.928 1.206 16.784 11.379 35.524 19.917 55.456 23.549 3.327.606 5.745 3.505 5.745 6.887v10.111zm93.495-24.046c0 7.133 5.791 12.924 12.924 12.924 7.134 0 12.925-5.791 12.925-12.924s-5.791-12.925-12.925-12.925c-7.133 0-12.924 5.792-12.924 12.925zm-93.495 69.573v-31.527h-24.834v31.527zm93.495 7c.07 7.074 5.834 12.795 12.924 12.795 7.134 0 12.925-5.791 12.925-12.924s-5.791-12.925-12.925-12.925c-7.133 0-12.925 5.792-12.925 12.925.001.043.001.086.001.129zm-93.495 38.786v-31.786h-24.834v1.818c0 10.15-2.233 20.254-6.195 29.968zm93.495 37.529c0 7.133 5.791 12.924 12.924 12.924 7.134 0 12.925-5.791 12.925-12.924s-5.791-12.925-12.925-12.925c-7.133 0-12.924 5.792-12.924 12.925zm-320.807-23.529v201.351c0 12.81 10.507 23.284 23.325 23.284h180.637c12.839 0 23.35-10.473 23.35-23.284v-201.351h-38.061c-1.773 2.962-3.698 5.867-5.758 8.704-17.021 23.435-43.23 42.135-67.746 49.808-1.361.426-2.821.426-4.182 0-24.516-7.673-50.725-26.378-67.746-49.814-2.059-2.835-3.982-5.738-5.755-8.698zm-93.495 23.529c0-7.133-5.791-12.925-12.924-12.925-7.134 0-12.925 5.792-12.925 12.925s5.791 12.924 12.925 12.924c7.133 0 12.924-5.791 12.924-12.924zm93.495-69.315v31.786h31.031c-3.963-9.715-6.197-19.819-6.197-29.968v-1.818zm-93.494-7.129c0-7.133-5.792-12.925-12.925-12.925-7.134 0-12.925 5.792-12.925 12.925s5.791 12.924 12.925 12.924c7.09 0 12.854-5.721 12.924-12.795 0-.043 0-.086.001-.129zm93.494-38.398v31.527h24.834v-31.527zm38.834-18.399v65.744c0 15.545 6.459 30.872 16.313 44.439 14.757 20.319 37.174 36.739 58.509 43.997 21.335-7.258 43.752-23.674 58.509-43.991 9.854-13.567 16.313-28.895 16.313-44.445v-65.744c-19.004-4.308-36.96-12.573-53.256-23.354h-43.12c-16.308 10.781-34.265 19.046-53.268 23.354zm114.787 38.985h4.066c3.866 0 7 3.134 7 7v37.52c0 11.169-4.687 21.897-13.092 29.795-8.244 7.746-19.414 12.127-31.073 12.127h-13.732c-11.659 0-22.829-4.381-31.073-12.127-8.405-7.898-13.092-18.626-13.092-29.795v-37.52c0-3.866 3.134-7 7-7h4.066v-8.723c0-9.061 3.685-17.756 10.268-24.162 6.515-6.339 15.344-9.914 24.557-9.914h10.28c9.213 0 18.042 3.575 24.557 9.914 6.583 6.406 10.268 15.101 10.268 24.162zm-2.934 14h-74.062v30.52c0 7.354 3.144 14.392 8.679 19.592 5.695 5.352 13.432 8.33 21.486 8.33h13.732c8.054 0 15.791-2.978 21.486-8.33 5.535-5.2 8.679-12.238 8.679-19.592zm-11.066-14v-8.723c0-5.302-2.179-10.38-6.032-14.129-3.922-3.816-9.246-5.947-14.793-5.947h-10.28c-5.547 0-10.871 2.131-14.793 5.947-3.853 3.749-6.032 8.827-6.032 14.129v8.723zm-25.965 25.038c10.035 0 18.183 8.147 18.183 18.183 0 10.035-8.148 18.183-18.183 18.183s-18.183-8.148-18.183-18.183c0-10.036 8.148-18.183 18.183-18.183zm0 14c-2.309 0-4.183 1.874-4.183 4.183s1.874 4.183 4.183 4.183 4.183-1.874 4.183-4.183-1.874-4.183-4.183-4.183zm100.151 117.697v52.907c0 4.383-1.742 8.587-4.841 11.687-3.1 3.1-7.304 4.841-11.688 4.841h-167.244c-4.384 0-8.588-1.741-11.688-4.841-3.099-3.1-4.841-7.304-4.841-11.687v-52.907c0-4.384 1.742-8.588 4.841-11.687 3.1-3.1 7.304-4.841 11.688-4.841h167.244c4.384 0 8.588 1.741 11.688 4.841 3.099 3.099 4.841 7.303 4.841 11.687zm-14 0c0-.671-.267-1.314-.741-1.788s-1.117-.74-1.788-.74h-167.244c-.671 0-1.314.266-1.788.74s-.741 1.117-.741 1.788v52.907c0 .67.267 1.313.741 1.787.474.475 1.117.741 1.788.741h167.244c.671 0 1.314-.266 1.788-.741.474-.474.741-1.117.741-1.787zm-34.857 14.344v-7.155c0-3.864 3.137-7 7-7 3.864 0 7 3.136 7 7v7.155l6.102-3.523c3.346-1.932 7.631-.784 9.563 2.562 1.931 3.346.783 7.63-2.563 9.562l-6.102 3.523 6.102 3.523c3.346 1.932 4.494 6.217 2.563 9.562-1.932 3.346-6.217 4.494-9.563 2.563l-6.102-3.523v7.155c0 3.863-3.136 7-7 7-3.863 0-7-3.137-7-7v-7.155l-6.102 3.523c-3.345 1.931-7.63.783-9.562-2.563-1.932-3.345-.783-7.63 2.562-9.562l6.102-3.523-6.102-3.523c-3.345-1.932-4.494-6.216-2.562-9.562s6.217-4.494 9.562-2.562zm-115.377 0v-7.155c0-3.864 3.137-7 7-7 3.864 0 7 3.136 7 7v7.155l6.102-3.523c3.346-1.932 7.631-.784 9.562 2.562 1.932 3.346.784 7.63-2.562 9.562l-6.102 3.523 6.102 3.523c3.346 1.932 4.494 6.217 2.562 9.562-1.931 3.346-6.216 4.494-9.562 2.563l-6.102-3.523v7.155c0 3.863-3.136 7-7 7-3.863 0-7-3.137-7-7v-7.155l-6.102 3.523c-3.346 1.931-7.63.783-9.562-2.563-1.932-3.345-.784-7.63 2.562-9.562l6.102-3.523-6.102-3.523c-3.346-1.932-4.494-6.216-2.562-9.562s6.216-4.494 9.562-2.562zm57.159 0v-7.155c0-3.864 3.137-7 7-7s7 3.136 7 7v7.155l6.102-3.523c3.346-1.932 7.631-.784 9.562 2.562 1.932 3.346.784 7.63-2.562 9.562l-6.102 3.523 6.102 3.523c3.346 1.932 4.494 6.217 2.562 9.562-1.931 3.346-6.216 4.494-9.562 2.563l-6.102-3.523v7.155c0 3.863-3.137 7-7 7s-7-3.137-7-7v-7.155l-6.102 3.523c-3.346 1.931-7.63.783-9.562-2.563-1.932-3.345-.784-7.63 2.562-9.562l6.102-3.523-6.102-3.523c-3.346-1.932-4.494-6.216-2.562-9.562s6.216-4.494 9.562-2.562zm-9.572 96.27c-3.863 0-7-3.137-7-7s3.137-7 7-7h32.992c3.863 0 7 3.137 7 7s-3.137 7-7 7z" fill="#1f4571"></path></g>
            </svg>
            """
        },
        {
            "name": "question réponse",
            "usage_description": "Utiliser les questions et réponse pour vous authentifier",
            "config_description": "Configurer les questions et réponses à utiliser lors de votre autentification",
            "is_default": False,
            "purpose": EMfaPurpose.RESET_PASSWORD_ONLY.value,
            "flag": MFaFlag.QUESTION_RESPONSE.value,
            "is_activated": False,
            "svg_icon": """<svg clip-rule="evenodd" fill-rule="evenodd" stroke-linejoin="round" stroke-miterlimit="2" viewBox="0 0 510 510" xmlns="http://www.w3.org/2000/svg" id="fi_17363445"><g><g><path d="m255 283.831c-38.722-12.119-81.822-53.388-81.822-95.799 0 0 0-52.178.008-67.36 0-2.366 1.661-4.407 3.977-4.887 19.403-4.166 37.679-12.688 54.157-23.851h47.373c16.465 11.163 34.741 19.685 54.145 23.843 2.321.481 3.984 2.526 3.984 4.895v67.36c0 42.424-43.1 83.68-81.822 95.799zm44.031-110.558c0-1.326-.527-2.598-1.464-3.536-.938-.937-2.21-1.464-3.536-1.464h-78.062c-1.326 0-2.598.527-3.536 1.464-.937.938-1.464 2.21-1.464 3.536v32.52c0 9.262 3.916 18.144 10.885 24.694 6.97 6.549 16.424 10.228 26.28 10.228h13.732c9.856 0 19.31-3.679 26.28-10.228 6.969-6.55 10.885-15.432 10.885-24.694z" fill="#a4d4ff"></path><g><circle cx="255" cy="204.494" fill="#a4d4ff" r="11.183"></circle></g><g fill="#a4d4ff"><circle cx="34.925" cy="102.641" r="19.925"></circle><circle cx="475.075" cy="102.641" r="19.925"></circle><circle cx="475.075" cy="179.085" r="19.925"></circle><circle cx="475.075" cy="255.529" r="19.925"></circle><circle cx="34.925" cy="179.085" r="19.925"></circle><circle cx="34.925" cy="255.529" r="19.925"></circle></g><g><path d="m348.151 318.008c0-2.527-1.004-4.951-2.791-6.738-1.787-1.786-4.211-2.79-6.738-2.79-31.979 0-135.265 0-167.244 0-2.527 0-4.951 1.004-6.738 2.79-1.787 1.787-2.791 4.211-2.791 6.738v52.907c0 2.527 1.004 4.95 2.791 6.737s4.211 2.791 6.738 2.791h167.244c2.527 0 4.951-1.004 6.738-2.791s2.791-4.21 2.791-6.737c0-13.78 0-39.127 0-52.907z" fill="#a4d4ff"></path></g></g><path d="m60.929 109.641c-3.085 11.471-13.565 19.924-26.004 19.924-14.86 0-26.925-12.064-26.925-26.924s12.065-26.925 26.925-26.925c12.439 0 22.919 8.454 26.004 19.925h35.198c3.866 0 7 3.134 7 7v24.046h24.217v-50.038c0-20.505 16.806-37.284 37.325-37.284h180.637c20.548 0 37.35 16.781 37.35 37.284v50.038h24.19l-.09-24.02c-.007-1.861.727-3.648 2.041-4.967 1.313-1.318 3.098-2.059 4.959-2.059h35.315c3.085-11.471 13.565-19.925 26.004-19.925 14.86 0 26.925 12.065 26.925 26.925s-12.065 26.924-26.925 26.924c-12.439 0-22.919-8.453-26.004-19.924h-28.289l.091 24.019c.007 1.861-.728 3.649-2.041 4.967-1.314 1.318-3.098 2.06-4.959 2.06h-31.217v31.527h66.381c3.04-11.536 13.553-20.054 26.038-20.054 14.86 0 26.925 12.065 26.925 26.925s-12.065 26.924-26.925 26.924c-12.392 0-22.84-8.39-25.969-19.795h-66.45v31.786h31.217c1.862 0 3.647.742 4.96 2.061 1.314 1.32 2.048 3.109 2.04 4.97l-.106 23.498h28.304c3.085-11.471 13.565-19.925 26.004-19.925 14.86 0 26.925 12.065 26.925 26.925s-12.065 26.924-26.925 26.924c-12.439 0-22.919-8.453-26.004-19.924h-35.336c-1.862 0-3.647-.742-4.96-2.062-1.314-1.319-2.048-3.108-2.04-4.97l.106-23.497h-24.185v201.351c0 20.503-16.802 37.284-37.35 37.284h-180.637c-20.519 0-37.325-16.779-37.325-37.284v-201.351h-24.217v23.529c0 3.866-3.134 7-7 7h-35.198c-3.085 11.471-13.565 19.924-26.004 19.924-14.86 0-26.925-12.064-26.925-26.924s12.065-26.925 26.925-26.925c12.439 0 22.919 8.454 26.004 19.925h28.198v-23.529c0-3.866 3.134-7 7-7h31.217v-31.786h-66.45c-3.129 11.405-13.577 19.795-25.969 19.795-14.86 0-26.925-12.064-26.925-26.924s12.065-26.925 26.925-26.925c12.485 0 22.998 8.518 26.038 20.054h66.381v-31.527h-31.217c-3.866 0-7-3.134-7-7v-24.046zm-13.08-7c0-7.133-5.791-12.925-12.924-12.925-7.134 0-12.925 5.792-12.925 12.925s5.791 12.924 12.925 12.924c7.133 0 12.924-5.791 12.924-12.924zm320.807 24.046v-50.038c0-12.811-10.511-23.284-23.35-23.284h-180.637c-12.818 0-23.325 10.474-23.325 23.284v50.038h24.834v-10.111c0-3.382 2.418-6.281 5.745-6.887 19.933-3.632 38.674-12.171 55.471-23.55 1.158-.785 2.526-1.205 3.926-1.205h47.373c1.401 0 2.769.42 3.928 1.206 16.784 11.379 35.524 19.917 55.456 23.549 3.327.606 5.745 3.505 5.745 6.887v10.111zm93.495-24.046c0 7.133 5.791 12.924 12.924 12.924 7.134 0 12.925-5.791 12.925-12.924s-5.791-12.925-12.925-12.925c-7.133 0-12.924 5.792-12.924 12.925zm-93.495 69.573v-31.527h-24.834v31.527zm93.495 7c.07 7.074 5.834 12.795 12.924 12.795 7.134 0 12.925-5.791 12.925-12.924s-5.791-12.925-12.925-12.925c-7.133 0-12.925 5.792-12.925 12.925.001.043.001.086.001.129zm-93.495 38.786v-31.786h-24.834v1.818c0 10.15-2.233 20.254-6.195 29.968zm93.495 37.529c0 7.133 5.791 12.924 12.924 12.924 7.134 0 12.925-5.791 12.925-12.924s-5.791-12.925-12.925-12.925c-7.133 0-12.924 5.792-12.924 12.925zm-320.807-23.529v201.351c0 12.81 10.507 23.284 23.325 23.284h180.637c12.839 0 23.35-10.473 23.35-23.284v-201.351h-38.061c-1.773 2.962-3.698 5.867-5.758 8.704-17.021 23.435-43.23 42.135-67.746 49.808-1.361.426-2.821.426-4.182 0-24.516-7.673-50.725-26.378-67.746-49.814-2.059-2.835-3.982-5.738-5.755-8.698zm-93.495 23.529c0-7.133-5.791-12.925-12.924-12.925-7.134 0-12.925 5.792-12.925 12.925s5.791 12.924 12.925 12.924c7.133 0 12.924-5.791 12.924-12.924zm93.495-69.315v31.786h31.031c-3.963-9.715-6.197-19.819-6.197-29.968v-1.818zm-93.494-7.129c0-7.133-5.792-12.925-12.925-12.925-7.134 0-12.925 5.792-12.925 12.925s5.791 12.924 12.925 12.924c7.09 0 12.854-5.721 12.924-12.795 0-.043 0-.086.001-.129zm93.494-38.398v31.527h24.834v-31.527zm38.834-18.399v65.744c0 15.545 6.459 30.872 16.313 44.439 14.757 20.319 37.174 36.739 58.509 43.997 21.335-7.258 43.752-23.674 58.509-43.991 9.854-13.567 16.313-28.895 16.313-44.445v-65.744c-19.004-4.308-36.96-12.573-53.256-23.354h-43.12c-16.308 10.781-34.265 19.046-53.268 23.354zm114.787 38.985h4.066c3.866 0 7 3.134 7 7v37.52c0 11.169-4.687 21.897-13.092 29.795-8.244 7.746-19.414 12.127-31.073 12.127h-13.732c-11.659 0-22.829-4.381-31.073-12.127-8.405-7.898-13.092-18.626-13.092-29.795v-37.52c0-3.866 3.134-7 7-7h4.066v-8.723c0-9.061 3.685-17.756 10.268-24.162 6.515-6.339 15.344-9.914 24.557-9.914h10.28c9.213 0 18.042 3.575 24.557 9.914 6.583 6.406 10.268 15.101 10.268 24.162zm-2.934 14h-74.062v30.52c0 7.354 3.144 14.392 8.679 19.592 5.695 5.352 13.432 8.33 21.486 8.33h13.732c8.054 0 15.791-2.978 21.486-8.33 5.535-5.2 8.679-12.238 8.679-19.592zm-11.066-14v-8.723c0-5.302-2.179-10.38-6.032-14.129-3.922-3.816-9.246-5.947-14.793-5.947h-10.28c-5.547 0-10.871 2.131-14.793 5.947-3.853 3.749-6.032 8.827-6.032 14.129v8.723zm-25.965 25.038c10.035 0 18.183 8.147 18.183 18.183 0 10.035-8.148 18.183-18.183 18.183s-18.183-8.148-18.183-18.183c0-10.036 8.148-18.183 18.183-18.183zm0 14c-2.309 0-4.183 1.874-4.183 4.183s1.874 4.183 4.183 4.183 4.183-1.874 4.183-4.183-1.874-4.183-4.183-4.183zm100.151 117.697v52.907c0 4.383-1.742 8.587-4.841 11.687-3.1 3.1-7.304 4.841-11.688 4.841h-167.244c-4.384 0-8.588-1.741-11.688-4.841-3.099-3.1-4.841-7.304-4.841-11.687v-52.907c0-4.384 1.742-8.588 4.841-11.687 3.1-3.1 7.304-4.841 11.688-4.841h167.244c4.384 0 8.588 1.741 11.688 4.841 3.099 3.099 4.841 7.303 4.841 11.687zm-14 0c0-.671-.267-1.314-.741-1.788s-1.117-.74-1.788-.74h-167.244c-.671 0-1.314.266-1.788.74s-.741 1.117-.741 1.788v52.907c0 .67.267 1.313.741 1.787.474.475 1.117.741 1.788.741h167.244c.671 0 1.314-.266 1.788-.741.474-.474.741-1.117.741-1.787zm-34.857 14.344v-7.155c0-3.864 3.137-7 7-7 3.864 0 7 3.136 7 7v7.155l6.102-3.523c3.346-1.932 7.631-.784 9.563 2.562 1.931 3.346.783 7.63-2.563 9.562l-6.102 3.523 6.102 3.523c3.346 1.932 4.494 6.217 2.563 9.562-1.932 3.346-6.217 4.494-9.563 2.563l-6.102-3.523v7.155c0 3.863-3.136 7-7 7-3.863 0-7-3.137-7-7v-7.155l-6.102 3.523c-3.345 1.931-7.63.783-9.562-2.563-1.932-3.345-.783-7.63 2.562-9.562l6.102-3.523-6.102-3.523c-3.345-1.932-4.494-6.216-2.562-9.562s6.217-4.494 9.562-2.562zm-115.377 0v-7.155c0-3.864 3.137-7 7-7 3.864 0 7 3.136 7 7v7.155l6.102-3.523c3.346-1.932 7.631-.784 9.562 2.562 1.932 3.346.784 7.63-2.562 9.562l-6.102 3.523 6.102 3.523c3.346 1.932 4.494 6.217 2.562 9.562-1.931 3.346-6.216 4.494-9.562 2.563l-6.102-3.523v7.155c0 3.863-3.136 7-7 7-3.863 0-7-3.137-7-7v-7.155l-6.102 3.523c-3.346 1.931-7.63.783-9.562-2.563-1.932-3.345-.784-7.63 2.562-9.562l6.102-3.523-6.102-3.523c-3.346-1.932-4.494-6.216-2.562-9.562s6.216-4.494 9.562-2.562zm57.159 0v-7.155c0-3.864 3.137-7 7-7s7 3.136 7 7v7.155l6.102-3.523c3.346-1.932 7.631-.784 9.562 2.562 1.932 3.346.784 7.63-2.562 9.562l-6.102 3.523 6.102 3.523c3.346 1.932 4.494 6.217 2.562 9.562-1.931 3.346-6.216 4.494-9.562 2.563l-6.102-3.523v7.155c0 3.863-3.137 7-7 7s-7-3.137-7-7v-7.155l-6.102 3.523c-3.346 1.931-7.63.783-9.562-2.563-1.932-3.345-.784-7.63 2.562-9.562l6.102-3.523-6.102-3.523c-3.346-1.932-4.494-6.216-2.562-9.562s6.216-4.494 9.562-2.562zm-9.572 96.27c-3.863 0-7-3.137-7-7s3.137-7 7-7h32.992c3.863 0 7 3.137 7 7s-3.137 7-7 7z" fill="#1f4571"></path></g>
                        </svg>
            """
        },
        {
            "name": "Sycamore Authenticator",
            "usage_description": "Utiliser l'application Sycamore Authenticator pour vous authentifier",
            "config_description": "Configurer l'application Sycamore Authenticator pour sécuriser votre compte",
            "is_default": False,
            "purpose": EMfaPurpose.LOCKED_SCREEN_AND_LOGIN.value,
            "flag": MFaFlag.SYCAMORE_2FA_APP.value,
            "is_activated": True,
            "svg_icon": """<svg id="fi_17840568" enable-background="new 0 0 500 500" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg"><path clip-rule="evenodd" d="m341.493 328.5c-.462.679.492 1.554-.599 2.031-.467.204-.366 1.113-.871 1.476-.882.633-.708.962-1.198 2.004-.327.071-.272.594-.381.964l-.545.507c-.932 1.829-1.198 1.353-2.124 2.32-.272.272-.599.474-.98.626l-2.178 1.792c1.41.894 2.627 2.055 3.812 3.23l.708.795c1.866 1.492.592.395 1.961 1.928.054.049.109.103.109.147 1.52 1.486.927 2.255 1.362 3.622.285.897.398 3.666-.055 4.34-1.264 2.379-.121 1.983-1.906 2.875-.312-.133-.571.522-.98.37-.714-.264-1.381.918-2.069.011-.285-.375-1.17-.058-1.688-.457-1.118-.862-1.456-.306-1.743-.507-.109-.076-.218-.207-.436-.087-.054.011-.054.016-.054 0-.164-.283-.654-.104-1.035-.076l-.653-.381c-1.094-.127-3.185-1.532-3.703-2.179l-6.099-4.226-10.075 6.154c-.29.449-.581-.13-.817-.032-.163.087-.327.212-.599.223-.109 0-.164.158-.272.212-1.867.839-1.855.266-2.396.871-.379.425-.311.828-.708.452-.476-.452-.917.342-1.307.463-.126.039-1.762-.302-1.579-1.111v-.381c-.264-.08-.215-.35-.49-.746-.26-.374-.871.237-.49-1.726l1.307-5.517c.41-1.322 2.698-2.98 2.832-3.284.245-.557.419-.079.436-.321l3.812-3.801-7.025-6.268c-.273-.048-.164-.421-.164-.784-.213-.213-1.626-1.883-1.743-2.494-.112-.588-1.361-.136-1.035-.855.272-.6-.496-.704-.817-1.155-.106-.15-.192-1.669.653-1.776.109-.016.218-.022.327-.038 0-.353.369-.472.599-.784.183-.249-.272-.876 1.525-.931 2.361-.072 5.099-.837 7.298.267l2.287 1.274c.572.058.276.363.436.354.381-.043.545.223.763.354.217-1.821-.611-1.964-.055-3.926.456-1.608 1.035-3.176 1.035-4.809 0-.115.327-1.061.327-2.32 0-.122.212-.151.054-.338-.192-.228.527-.266.545-.343.623-1.863 1.378-1.363.708-2.238-.013-.017.991-.339.708-.512-.566-.346 1.243-1.027 1.797-.664.109.049.164.087.272.131 0-.006.054-.006.054-.016 1.671.049 1.48-.345 2.56.397.875.601 4.094 2.225 4.194 3.311l.381 1.459c.219.247-.054.213-.054.311.4.2 1.063 6.208 1.089 6.301l.272.594c-.197.205.109.358.109.654 0-.005.054-.005.054-.016.794-.477.62-.551 1.525-.822.575-.281.497-.619 2.505-1.422 0-.049 1.83-.866 2.723-.517.65.254 2.251-.023 4.411.8 1.174.447 2.128 1.741 3.05 2.217zm-69.709 1.286c-.434.609.459 1.595-.545 1.972-.514.193-.29 1.041-.871 1.405 0 0-.85.744-.762 1.029.152.495-.327.301-.327.888-.327.06-.272.577-.327.931l-.545.479c-.886 1.709-1.528 1.57-2.069 2.178l-2.396 1.786c.418.387 2.815 2.399 2.886 2.848 1.029.618 3.168 3.044 3.05 4.27-.122 1.266.339 1.242.272 2.391-.035.611.12 2.446-.327 3.082l-1.035 2.38-.926.496c-.215-.113-.584.506-.871.392-.677-.268-1.388.949-2.069.076-.298-.381-1.112-.006-1.579-.392-.954-.789-1.366-.263-1.634-.43-.109-.071-.163-.201-.436-.071 0 .006-.054.016-.054 0-.109-.272-.599-.076-.98-.043l-.599-.343c-.99-.065-2.96-1.392-3.431-2.01-.109-.142-.327-.169-.49-.272-1.459-.997-2.877-2.295-4.466-3.121l-3.594 1.922-5.882 3.633c-.29.421-.6-.148-.817-.065-.163.076-.327.196-.545.191-.163 0-.163.153-.272.202-1.634.652-1.959.276-2.342.762-.799 1.015.338.426-1.361.387 0 .013-.322.758-1.144.256-.93-.568-.926-.33-.926-1.362-.277-.083-.234-.375-.49-.757-.25-.372-.874.209-.49-1.705.341-1.698.769-5.166 1.797-6.421l2.069-2.042c.054-.152.109-.31.381-.239 0 .016.054-.022.054-.06l3.213-3.18-6.481-5.887c-.448-.059-.082-.521-.163-.768-.123-.374-1.358-1.28-1.579-2.38-.107-.53-1.29-.117-.98-.79.391-.852-1.108-.623-.763-1.721.305-.97-.018-1.024 1.035-1.182l.272-.457c1.191-1.074-1.13-1.039 4.901-1.628 2.93-.287 3.037-.116 5.174 1.046l.871.485c.507.025.221.348.381.321.381-.049.49.201.708.321l.054-.839c.272-.229-.109-.485 0-.73.203-.499-.546-.64.054-2.685l1.035-3.317.545-2.886c.055-.239.055-.479.055-.73.054-.06.109-.131.109-.19.164-.132-.403-.301.327-.392.359-.045.441-.834.708-1.105.625-.635.689-.601.272-1.127l.599-.18c0-.071.109-.147.109-.223.054-.022.054-.038.054-.06-.574-.44 1.394-.95 1.797-.588.916.551 1.569-.389 2.886.61 1.922 1.457 4.05 2.118 4.248 4.281.078.854.336.733.054.817l.654 2.99v2.679l.436 1.214c-.173.166.055.335.055.458 0-.011 0-.022 0-.022.272-.147.49-.349.817-.349.054 0 .109-.027.109-.054 1.044-.747 3.666-2.193 4.956-1.634.635.275 2.016.037 4.248.953 1.177.483 2.066 1.798 2.995 2.309zm-106.361 26.212c0-.115.054-.218.054-.321-.329-.097-.378-.564-.599-.806-.236-.258-.884-.014-.545-1.683.416-2.044.53-5.289 1.851-6.595l1.688-1.737c.241-.521.365-.059.381-.294l3.431-3.496-6.699-6.002c-.361-.057-.163-.382-.163-.773-.07-.203-1.576-1.758-1.688-2.44-.121-.618-1.388-.095-.98-.822.333-.594-.597-.792-.817-1.133l.272-1.58.763-.234c0-.429.354-.435.599-.779.206-.289-.302-.858 1.47-.942 2.083-.099 5.264-.911 7.134.142l2.287 1.231c.504.038.223.361.381.338.272-.027.381.076.545.191v-.664c.3-.282-.585-1.539-.054-3.529.813-3.047 1.111-4.481 1.416-7.581-.395-.364.549.172.708-.904.095-.641.856-.982.762-1.378-.062-.26-.613-.388.054-.452.315-.03.436-.294.436-.398-.645-.355.941-.728 1.144-.784 0-.061.557-.044.871.24.647.253 1.457-.53 2.669.381.696.524 3.858 2.283 4.139 3.126l.381 1.721c.297.266-.175.227 0 .321l.599 2.287c.284 1.684-.079 3.153.762 4.711-.179.545.109.062.109 1.204.931-.726 3.512-2.028 4.684-1.514.884.388 2.171-.167 5.011 1.448l2.178 1.786.327 1.977c-.234.423.054.884.054 1.514-1.399 1.167-.62 1.385-1.253 1.819-.756.518-.688.937-1.035 1.884-.327.054-.218.556-.327.915-.042.28-.386.268-.436.468-.28 1.133-2.46 2.368-3.486 3.316l2.505 2.059 1.47 1.628c2.141 1.678 1.182 1.172 1.906 1.879.055.038.109.092.109.136.504.487 1.131 1.462 1.089 2.309-.037.759.864 2.934.109 5.544l-1.035 2.402c-.805.289-.738.572-.926.474-.272-.143-.59.502-.926.387-.706-.243-1.404.916-2.069.038-.291-.384-1.167-.034-1.634-.43-.895-.76-1.487-.332-1.688-.468-.109-.076-.218-.207-.436-.087-.054.022-.054.022-.054 0-.163-.272-.654-.087-1.035-.06l-.599-.359c-1.121-.121-2.952-1.342-3.595-2.102l-5.664-3.883c-.054.027-.109.043-.109.065l-3.703 2.01-5.609 3.562c-.12.406-.763-.143-.763-.065-.326.152-2.063.923-2.668.855-.571-.064-.471 1.219-1.035.67-.456-.445-.855.284-1.198.398l-1.47-.675c-.104-.298-.05-.363-.05-.466zm-9.694-155.24c.81-4.71 2.106-16.381 2.396-21.065.218-3.202.436-6.415.926-9.509 1.39-9.382 1.485-43.146 1.579-53.85l.381-21.664.109-18.135 24.997-25.259 52.772-.653c1.797 0 3.594-.12 5.392-.136l20.368-.12c2.56-.087 5.119-.163 7.679-.054l10.783-.272 35.889-.267 24.344 24.055.381 25.635c.054 2.93-.109 5.893.163 8.801 0 .365.054.779 0 1.122-.261 1.722.047 4.993.054 7.205l.327 27.987c.241 11.527 1.958 32.441 3.159 44.222.303 2.975 1.384 17.85 1.852 19.671.109.31.109.768.381.637.218-.626.055-1.645.436-2.146 1.058 1.269.391 1.615.98.202.054.752.163 1.481.218 2.222l-33.439-1.688c.307-.538.367-.187.599-.888 1.447-4.368 1.661-8.038 2.505-12.569.795-4.263.91-10.148 1.688-13.631.871-3.898 1.487-23.903 1.579-29.746l.055-10.702.545-35.976-.055-6.307c-.054-1.906-.762-3.812-2.233-5.25l-18.952-18.576c-1.307-1.263-3.104-2.031-5.065-2.004-12.466.184-24.736.639-37.197.621-1.361 0-2.723.131-4.03.147l-15.303.12c-1.96.076-3.867.164-5.773.044l-8.115.283c-2.777.06-5.664-.027-8.441.18l-14.486.06c-1.47.016-2.996.594-4.139 1.748l-19.878 20.128c-2.146 2.181-1.512 4.893-1.47 8.006l.218 10.696.708 44.086c.157 4.526.131 7.12.599 11.998l3.758 34.805-30.062-.24c.274-1.316.655-2.607.818-3.974zm138.765 5.958c6.535.463 13.343.664 20.205.877-.217-1.062-.626-.648-.762-2.952-.245-4.13-1.177-6.119-1.198-7.467-.055-3.571.013-6.757-.327-10.326l-.545-15.407c-.093-1.882-.49-1.992-.49-4.477 0-1.067.055-2.14-.218-3.175 0-.104 0-.223 0-.338.109-2.244-.327-4.368-.545-6.524-.214-1.871.006-4.211-.109-5.571-.671-7.946-.394-15.741-.545-23.582-.054-2.881 0-5.767.055-8.654.054-1.465-.055-2.941-.055-4.417l-.054-13.68-14.268-14.176-23.309.016c-2.015 0-4.084.12-6.099-.033-3.377-.25-6.753.136-10.13.049-2.015-.06-4.084 0-6.099.043l-16.828.185-25.053-.437-16.175 15.505-.436 52.315c0 .904-.109 1.797-.109 2.701 0 1.878.309 3.951-.327 5.626-.305.803-.195 4.137-.327 5.538-.109.937 0 1.917 0 2.876l-.763 14.541c-.358 2.946.678 9.035-.054 10.037-.651.89-.322 7.754-.381 9.166 5.936 0 11.872.011 17.809.054 26.644.248 54.37.538 80.874 1.367 2.124.064 4.248.173 6.263.32zm138.819 202.081-.436-67.144c-.154-16.231-.691-33.307-1.253-49.542l-1.416-36.554c-.011-.568-.096-.998-.599-1.454l-26.522-24.42c-2.624-2.449-14.702-13.79-14.105-12.477.817 1.187 2.505 2.614 3.05 3.692-.327-.153-.653-.3-1.035-.447-.685-.393-1.651-1.373-.163.403.163.207.327.403.49.626l-7.679-6.922c4.441 6.35 15.506 17.993 21.294 23.478 1.773 1.699 9.465 9.59 10.293 10.984 1.077 1.812 6.555 6.832 8.333 8.534 0 4.322.177 8.805 0 13.038-.272 7.009-.327 14.094-.436 21.141l-.49 39.086c-.837-.045-5.279.292-5.882-.365-.704-.767-4.688.326-7.026-.06-3.682-.608-11.141-.681-15.412-.931-1.061-.062-1.01-.735-3.322-.517-3.342.314-3.613-1.028-7.352 2.576l-4.901 5.168c-6.381 6.576-13.515 13.479-19.715 20.194l-4.302 4.313-24.507 24.474-9.258 10.064c-.98 1.067-1.906 2.14-2.941 3.142-1.688 1.661-2.995 3.643-4.847 5.201l-4.466 4.678-7.842.033c-1.906.027-3.812.136-5.718.163l-26.359.076c-1.035.011-2.069.114-3.05.071l-17.754.12-6.045.371c-.926.032-1.852-.087-2.723.071-1.525.245-2.995.686-4.575.55-.109-.011-.163.005-.218.033-.989.407-2.86-.024-4.248.49-.741.275-6.377.368-6.971.365-3.28-.017-5.88.747-8.55.632-4.965-.215-3.957.362-6.753.986-.415-6.223-5.417-13.703-10.837-16.741-4.997-2.801-10.539-4.219-16.284-3.502l-4.248 1.008c-2.059.803-4.935 2.425-6.753 3.796-5.407 4.077-9.204 10.38-9.204 17.248 0 1.602-.003 3.522.436 5.065.163.574.141 1.561.653 2.407.299.493-.209.546.436 1.52l1.307 2.701c5.782 11.477 19.779 7.678 19.279 6.579-.164-.256-.381-.104-.436-.463.02-.199.383-.722.163-.899 0-.016-.054-.06-.054-.092l.926-.594c-.375-.827-1.424-1.921-2.396-1.628-.051.015-1.035-.202-1.035-.681 0-.796-1.468-.084-1.961-.806-.442-.649-3.355-3.014-3.104-3.611.261-.62-.181-.626-.436-1.024-1.656-2.591-1.851-3.992-1.851-6.77l.49-2.952 1.144-2.102c2.38-2.562 2.088-2.558 5.391-3.839 1.024-.397 3.531-1.065 4.52-.931.756.102 1.178-.149 1.634.223.406.332 4.599 1.104 6.59 5.114.599 1.182.98 2.472 1.089 3.807 0 .251.163.501.109.757-.342 1.265-.047 1.636-.708 3.513l-.436 1.939c-.043.354-.49.546-.49.871 0 1.615-.399 1.135-.381 1.356.053.65-.49.405-.49 1.165 0 .613-1.741 1.534-2.505 2.5-.725.917-1.981.607-2.233 1.307-.481 1.335-1.358.9-1.688 1.71-.297.728-.551.268-.654.583-.109.49-.327.599-.599.822l1.634 2.647c1.568 1.241 2.589 1.269 4.575 1.628 1.766.32 3.468-.377 5.283-.474 3.408-.182 8.806-5.376 10.347-8.828 1.2-2.688 2.066-4.112 2.505-7.161.054-.365.163-.719.272-1.078 2.734.695 7.007 1.69 9.694 2.031 1.688.213 3.377.403 5.011.888 4.443 1.326 22.428 1.584 27.775 1.59.218 0 .381-.005.599.022l25.215.539c11.945-.112 24.307-.168 36.216-.697 3.638-.162 5.267-2.977 7.897-5.931 1.797-1.999 3.649-3.97 5.5-5.925.654-.692 1.253-1.465 1.906-2.162l7.243-7.88c1.555-1.886 2.499-2.541 3.649-3.932 7.672-9.115 16.536-18.026 24.562-26.735l19.225-21.414c.915-.578 1.701-1.869 2.56-2.799l6.045-6.655c8.347-.082 22.732-2.803 31.587-4.264 0 .697-.054 1.4-.109 1.966-.687 6.185-.265 10.413-.327 16.387l-.218 52.571-44.603 44.265-164.252-.969c-29.235-.205-58.277-.285-87.518-.027-3.431-3.398-6.916-6.813-10.293-10.255-6.917-7.036-14.105-13.691-20.913-20.864l-12.58-12.618-.054-66.964s.054 0 .054-.011c.355-.035 3.302.033 3.703.43.792.783 4.62-.327 7.08.071l10.184.735c1.011.037 5.338.047 5.882.349 1.24.686 2.858.221 4.847.37 2.027.152 3.775-1.137 5.119-2.592 5.441-5.888 11.851-12.084 17.536-17.999l11.382-11.665c10.255-10.367 20.972-20.684 30.988-31.326 1.923-2.104 3.561-4.265 5.718-6.361 1.688-1.655 3.05-3.638 4.847-5.196l4.52-4.678 7.788-.038c1.906-.016 3.812-.142 5.718-.158l26.359-.076c1.035-.011 2.07-.114 3.104-.071l17.754-.12 6.045-.371c.871-.032 1.797.076 2.723-.071 1.47-.245 2.995-.686 4.575-.55.055 0 .164-.005.218-.033.964-.411 2.595.036 4.194-.501l7.025-.359c3.193.028 5.895-.742 8.496-.632 5.048.213 3.919-.348 6.753-.98.907 6.805 4.975 13.121 10.838 16.741 4.678 2.888 12.411 4.53 17.645 3.24 3.035-.748 2.274-.433 5.174-1.803 3.676-1.737 7.697-5.051 9.912-8.294 3.813-5.583 4.464-11.439 3.159-17.994-.198-.997-.57-1.043-.545-1.481.04-.681-1.372-3.35-1.688-3.91-2.598-4.592-5.825-7.264-11.11-7.924-1.769-.221-6.474-.201-8.005 1.018-.595.474.692.362.163 1.231-.022.037-.293.311 0 .457 0 .016 0 .06.054.087-.441.206-.788.233-.98.599.347.729 1.456 1.93 2.451 1.617.001 0 .98.206.98.692 0 .748 1.464.103 2.015.801.487.617 3.236 3.02 3.104 3.616-.225 1.016.214.527.436 1.024.674 1.511 1.668 2.613 1.797 5.125.122 2.359-.022 3.578-.98 5.669-.554 1.209-2.54 3.303-3.812 3.916-2.686 1.294-2.803 1.139-5.718 1.868-1.497.375-4.278-.465-6.481-2.168-2.492-1.926-3.418-3.573-3.812-6.971-.24-1.59.108-1.019.109-2.211l.871-3.997.49-.866c0-.474 0-1.051.381-1.285 0-.848.56-.455.49-1.231-.048-.53 1.968-1.731 2.56-2.5.761-.988 1.92-.591 2.178-1.307.508-1.41 1.403-.865 1.688-1.721.214-.642.607-.291.653-.577.163-.485.381-.594.599-.822-2.057-3.326-1.684-3.507-6.208-4.27-1.918-.323-3.343.395-5.228.479-2.868.128-7.05 3.899-8.714 6.165-1.952 2.659-2.128 4.05-2.614 4.82-.866 1.372-1.54 4.403-1.797 6.072-3.218-.735-6.513-1.627-9.748-2.026-1.688-.212-3.376-.403-5.01-.887-3.015-.9-16.535-1.462-20.858-1.569l-7.461-.038-25.215-.545c-12.162.125-24.116.209-36.27.686-1.688.082-3.322.811-4.52 2.173l-21.621 23.663c-.98 1.111-1.852 2.255-2.832 3.344-7.077 7.927-14.563 15.599-21.73 23.391l-13.016 14.41-5.827 6.579c-.322.481-.915.583-2.069 2.14l-6.971 7.744c-8.213 0-21.125 2.624-29.517 3.943l-.163-75.52 39.211-39.326c6.045.044 12.145.06 18.244.016 22.617-.17 45.301.062 68.021-.604 5.156-.151 10.809.114 16.066-.098 6.263-.261 12.471-.708 18.898-.583.327 0 .708-.016.98-.033 5.89-.424 11.482-.019 17.427-.517l10.729-.229c12.91-.118 25.9-.165 38.776-.604 4.902-.164 9.858-.294 14.704-.251 4.43.039 15.314.11 19.551-.327 5.664-.577 11.654-.85 17.754-.948 2.396-.033 4.683-.12 6.535-.436 2.688-.456 7.642-.345 8.387-.517 1.851-.446 4.52-.545 7.298-.741-3.431-.31-3.431-.31-6.263-.975-2.406-.563-5.183-.549-6.917-1.378-.887-.424-16.214-1.412-18.571-1.541.257-2.079.584-2.601.708-5.441.109-2.189.164-4.357 0-6.535-.044-1.168.059-6.355.436-7.053.699-1.296-.195-10 .054-13.348.433-5.185.718-14.085.763-19.377l.327-11.192c.719-3.42.327-4.193.327-7.494 0-1.198.109-2.391.109-3.6l.49-63.986c.011-3.264-2.059-4.749-4.193-6.889l-24.075-24.798c-1.699-1.75-3.043-2.946-5.882-2.963-15.025-.087-30.038-.592-45.093-.577l-14.214.027c-5.435.011-10.818.312-16.284.196-4.52-.093-8.986.305-13.506.043-2.668-.147-5.391-.027-8.115-.033l-41.444.18c-2.403.022-3.899 1.053-5.5 2.679l-28.919 28.989c-1.252 1.296-2.069 3.077-2.069 5.038l.054 9.138c0 1.966.109 3.927.054 5.871-.109 3.85-.163 7.684-.109 11.535.164 7.379-.109 14.775.218 22.16l.381 11.48c.055 1.726-.109 3.447.055 5.168.272 2.875.708 5.691.545 8.686 0 .147 0 .311.054.447.387 1.303.037 5.332.49 7.995l.381 13.266c-.05 5.774.724 10.912.599 16.18-.044 1.839-.113 7.225.327 8.926 1.081 4.174.74 8.654 1.307 10.554l-32.785-.196c-1.906-.011-3.867.713-5.337 2.168v.032l-43.623 43.47c-1.362 1.378-2.233 3.273-2.233 5.364l.436 112.978.381 40.6c0 2.754 1.405 4.121 3.104 5.811 7.951 7.908 15.902 15.81 23.799 23.728 2.832 2.788 5.664 5.484 8.496 8.273l14.977 14.895v.038c2.374 2.331 4.997 1.903 8.278 1.895 6.59-.022 13.234.016 19.823-.082 5.609-.087 11.165-.163 16.774-.049 1.797.033 3.595-.011 5.392-.027 6.045-.087 12.09-.212 18.135-.25 63.838-.37 127.585-.174 191.428-.686 2.342-.019 4.31.255 6.154-1.617l25.869-26.152c4.52-4.591 9.204-9.035 13.506-13.735.545-.588 1.198-1.225 1.743-1.732l7.025-7.009c.918-.942 1.307-2.241 1.307-3.635z" fill-rule="evenodd"></path></svg>
            """
        }
    ]
    for index, mfa in enumerate(mfas):
        try:
            svg_icon = mfa.get('svg_icon', "")
            mfa_data = {
                field_name: field_value
                for field_name, field_value in mfa.items()
                if field_name not in ('svg_icon')
            }
            processed_mfa = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_MFAS,
                filter_data={"flag": mfa_data['flag']},
                update_data=mfa_data
            )
            # DebugService.app_debug_print("upserted result.",result)
            processed_mfa_id = str(processed_mfa['id'])
            # MFA ICON
            mfa_flag = mfa.get("flag", '')
            mfa_icon_data = {
                "is_default": False,
                "flag": EIconFlag.STANDARD_SVG.value,
                "icon": svg_icon,
                "name": f"icône du mfa {mfa_flag.lower()}"
            }
            mfa_icon_data = {
                **mfa_icon_data,
                "hard_code_flag": generate_label_to_flag(f"icon_mfa_{mfa_flag}")
            }
            saved_icon = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_ICON,
                filter_data={
                    "hard_code_flag": mfa_icon_data['hard_code_flag']
                },
                update_data=mfa_icon_data
            )
            saved_icon_id = saved_icon if isinstance(
                saved_icon, str) else saved_icon['id']
            icon_relation = {
                "targeted_id": processed_mfa_id,
                "ref_icon_id": saved_icon_id,
                "restricted_api_consumer_list": [
                    EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                ],
            }
            result_icon_relation = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                filter_data={
                    "targeted_id": icon_relation['targeted_id'], 'ref_icon_id': icon_relation['ref_icon_id']},
                update_data=icon_relation
            )
            processed_icon_relation_id = result_icon_relation if isinstance(
                result_icon_relation, str) else str(result_icon_relation['id'])
            icon_restricted_platform = icon_relation.get(
                'restricted_api_consumer_list', [])

            for api_consumer_flag in icon_restricted_platform:
                api_consumer_info = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_API_CONSUMER,
                    output_data_type=OutputDataType.DEFAULT,
                    query={
                        "flag": api_consumer_flag
                    }
                )
                if api_consumer_info:
                    await rbac_role_service.create_restricted_api_consumer(targeted_id=processed_icon_relation_id, ref_api_consumer_id=api_consumer_info['id'])
        except ValueError as e:
            print(f"Error: {e}")
        except PermissionError as e:
            print(f"Permission Error: {e}")
    print("Default mfas created or updated")


async def create_profiles():
    try:
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
        rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
        generic_service = GenericService(DEFAULT_LANGUAGE)
        """
        Create default profiles if they do not already exist in the database.
        """
        DebugService.app_debug_print("Starting rbac profil process", True)
        print(f"\nin profil fx init \n")
        profils = [
            {
                "name": "Profil système par defaut",
                "flag": ESysProfileFlag.SYSTEM_PROFIL.value,
                "description_str": "Profil Système par defaut",
                "is_default": True,
                "system_reserved_actions": True,
                "profil_system_roles": [
                    {
                        "flag": ESysProfilSuperUserRoleFlag.SYSTEM_PROFIL_SUPER_ADMIN.value,
                        "is_default": True,
                        "system_reserved_actions": True,
                        "name": "Administrateur du profil système",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },

                ],
                "svg_icon": """<svg id="Layer_2" data-name="Layer 2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 786 782">
                        <defs>
                            <style>
                            .cls-1 {
                                fill: #96cdd3;
                            }

                            .cls-2 {
                                fill: #058996;
                            }

                            .cls-3 {
                                fill: #9cd0d5;
                            }

                            .cls-4 {
                                fill: #fdfefe;
                            }
                            </style>
                        </defs>
                        <g id="Layer_1-2" data-name="Layer 1">
                            <g>
                            <path class="cls-4" d="M786,0v782H0V0h786ZM577,604c-5.94-1.82-22.48-8.97-21.99-16.43.46-7.01,17.92-12.92,23.74-15.32,53.18-21.95,104.97-31.97,150.27-70.73,13.98-11.96,31.3-27.98,34.98-46.51-15.38,3.8-30.27,11.01-46.45,12.04-16.31,1.04-40.07.69-31.42-22.42,12.11-32.35,49.68-76.2,49.59-111.41,0-1.65-.56-6.78-2.29-7.16-40.39,13.04-68.79,86.31-115.92,81.92-21.8-2.03-23.2-18.4-19.22-36.2.69-3.07,3.45-6.88,3.39-10.11-.07-4.3-2.79-11.05-7.97-9.5-2.59.78-16.27,19.56-19.68,23.34-10.7,11.88-25.05,24.4-37.55,34.45-17.78,14.28-38.41,29.49-60.42,35.99-6.28-41.81-5.33-87.67,8.49-127.93,9.23-26.91,29.74-54.43,47.07-76.93,4.6-5.98,31.46-36.52,31.37-40.63-.17-7.54-14.78-3.28-19.18-2.18-23.62,5.9-45.23,24.95-70.76,15.18-4.77-1.83-5.28-2.98-5.91-8.09-7.14-57.6,13.62-135.67,57.87-174.89,2.49-2.21,21.5-13.25,11.31-16.28-8.51-2.53-25.83,5.96-33.97,9.62-51.16,22.97-96.09,50.28-134.84,91.16-21.02,22.17-66.42,86.67-94.03,34.06-8.15-15.54-5.42-28.14-9.9-42.1-.18-.55-5.32-7.49-5.73-7.74-3.33-1.94-2.54,1.26-3.3,2.76-39.8,78.6-34.02,178.1-8.23,260.24,4.65,14.82,11.91,29.13,14.43,44.57s4.55,22.69-13.17,17.17c-34.62-10.79-58.16-63.78-75.38-92.62-7.36-12.32-16.06-27.27-30.16-32.33-6.53,21.25,9.4,39.86-2.64,60.88-5.84,10.2-14.3,7.1-23.35,3.6-21.09-8.16-49.92-26.23-65.57-42.47-1.5-1.56-.91-3.89-3.78-2.88s-4.68,7.41-4.75,10.37c-.35,14.55,18.4,36.13,25.46,49.62,9.93,18.99,29.41,67.2.91,78.67-13.95,5.61-22.41,1.11-35.8.22-1.12-.07-6.49-.9-5.48,1.47.75,1.75,11.37,14.24,13.48,16.53,27.86,30.27,71.99,54.76,110.55,68.45s84.6,19.99,122.15,37.85c3.56,1.69,18.53,8.03,13.36,12.72-5.54,5.02-27.88,14.47-35.54,16.48l-22,3.48c31.3,5.41,63.8,2.58,95.48,2,18.75-.34,38.16-2.16,57.05-1.03,10.13.6,20.3,2.65,29.45,7.04-1.21-32.78-7.52-66.46-19.51-96.98-10.35-26.33-25.73-47.58-34.5-75.5-24.19-76.99-20.65-160.78,14.02-233.52l1,1c-.26.44.07,3.82,0,5-3.95-.38-1.06,1.47-1,2,.07.62.1,2.89,0,3-.58.66-1.62-1.7-2,2-.2,1.91.09,4.03,0,6-4.07-.5-1.07,2.13-1,3,.1,1.3.04,2.69,0,4-3-.62-1.88,1.49-2,4-.12,2.65.19,5.36,0,8-2.91-.97-2.74,3.31-1,5-.33,2.66-.68,5.35-1,8-.41,3.36-.85,6.31-1,10-.33,8.21-.37,17.8,0,26,.15,3.35.63,6.01,1,9,.33,2.67.7,5.29,1,8-1.69,1.76-2.01,7.08,1,6,9.35,72.46,43.82,130.37,62.71,199.79,20.26,74.46,26.11,152.52-8.86,223.56-3.11,6.33-7.28,12.08-9.85,18.65h30c14.51-26.72,24.06-56.32,27.88-86.62,2.71-21.47-2.83-56.52,25.12-62.38,3.86-.81,1.23-1.4,2-2,.39-.3,3,.24,4,0,1.46-.35,1.89-.97,2-1,1.28-.38,2.69-.72,4-1,1.72,1.91,4.84,1.67,4-1,5.44-.45,11.45.22,17,0,5.43,2.12,11.7,1.12,17,0,1.34-.28,2.66-.69,4-1,2.26,2.77,6.18.23,8,0,3.27-.42,6.7-.59,10-1,1.69,1.74,5.97,1.91,5-1,1.99-.09,4.01.04,6,0,.12,0,.66.89,2.17.82,2.01-.1,3.53-1.49,4.83-1.82s2.83-.97,4-1c.32,0,5.92,2.6,4.99-1.49-.64-2.81-3.9-.67-4.99-.51-.46.07-1.93.07-2,0-.66-.72,1.67-1.58-2-2-1.26-.14-2.87.24-4,0,.3-2.36-.27-2.71-2-1Z"/>
                            <path class="cls-2" d="M371,216c-34.67,72.74-38.21,156.53-14.02,233.52,8.77,27.92,24.15,49.16,34.5,75.5,11.99,30.52,18.3,64.19,19.51,96.98-9.16-4.39-19.32-6.43-29.45-7.04-18.9-1.13-38.3.69-57.05,1.03-31.68.57-64.19,3.41-95.48-2l22-3.48c7.66-2.01,30-11.47,35.54-16.48,5.17-4.68-9.8-11.02-13.36-12.72-37.55-17.86-82.84-23.89-122.15-37.85s-82.69-38.17-110.55-68.45c-2.11-2.29-12.73-14.77-13.48-16.53-1.01-2.37,4.36-1.55,5.48-1.47,13.39.89,21.85,5.39,35.8-.22,28.5-11.47,9.02-59.68-.91-78.67-7.06-13.49-25.81-35.07-25.46-49.62.07-2.96,1.79-9.33,4.75-10.37s2.27,1.32,3.78,2.88c15.66,16.23,44.48,34.31,65.57,42.47,9.05,3.5,17.51,6.6,23.35-3.6,12.04-21.02-3.89-39.63,2.64-60.88,14.1,5.06,22.8,20,30.16,32.33,17.23,28.84,40.76,81.83,75.38,92.62,17.71,5.52,15.58-2.43,13.17-17.17s-9.78-29.75-14.43-44.57c-25.79-82.14-31.57-181.65,8.23-260.24.76-1.5-.03-4.7,3.3-2.76.42.24,5.56,7.19,5.73,7.74,4.49,13.96,1.75,26.56,9.9,42.1,27.61,52.61,73.01-11.88,94.03-34.06,38.75-40.88,83.68-68.19,134.84-91.16,8.15-3.66,25.47-12.15,33.97-9.62,10.19,3.03-8.82,14.07-11.31,16.28-44.25,39.22-65.01,117.29-57.87,174.89.63,5.11,1.14,6.26,5.91,8.09,25.53,9.77,47.14-9.28,70.76-15.18,4.4-1.1,19.01-5.36,19.18,2.18.09,4.11-26.76,34.65-31.37,40.63-17.32,22.51-37.83,50.03-47.07,76.93-13.81,40.26-14.76,86.11-8.49,127.93,22.02-6.5,42.65-21.71,60.42-35.99,12.51-10.05,26.86-22.57,37.55-34.45,3.41-3.79,17.1-22.57,19.68-23.34,5.18-1.56,7.91,5.2,7.97,9.5.05,3.23-2.71,7.04-3.39,10.11-3.99,17.8-2.58,34.17,19.22,36.2,47.13,4.39,75.53-68.88,115.92-81.92,1.73.38,2.29,5.51,2.29,7.16.09,35.21-37.48,79.06-49.59,111.41-8.65,23.11,15.11,23.46,31.42,22.42,16.17-1.03,31.07-8.25,46.45-12.04-3.68,18.53-21,34.55-34.98,46.51-45.3,38.76-97.09,48.78-150.27,70.73-5.82,2.4-23.28,8.31-23.74,15.32-.49,7.46,16.05,14.61,21.99,16.43.11.03.47.67,2,1,1.13.24,2.74-.14,4,0-.24,2.13-.12,2.24,2,2,.07.07,1.54.07,2,0v2c-1.17.03-2.76.69-4,1-1.32-1.88-5.47-.2-7,1-1.99.04-4.01-.09-6,0-2.53.11-3.69.84-5,1-3.3.41-6.73.58-10,1-2.37-2.59-5.8-.52-8,0-1.34.31-2.66.72-4,1-3.67-1.64-9.55-1.25-13.57-1.05-2.22.11-3.26,1.05-3.43,1.05-5.55.22-11.56-.45-17,0-2.27.19-2.75.73-4,1s-2.72.62-4,1c-1.73-1.71-2.3-1.37-2,1-1,.24-3.61-.3-4,0-2.12-.24-2.24-.13-2,2-27.95,5.85-22.42,40.91-25.12,62.38-3.82,30.3-13.37,59.9-27.88,86.62h-30c2.57-6.57,6.74-12.32,9.85-18.65,34.97-71.04,29.12-149.1,8.86-223.56-18.89-69.42-53.36-127.33-62.71-199.79-.27-2.07-.83-4.46-1-6-.3-2.71-.67-5.33-1-8,1.56-2.03,2.24-10.2-1-9-.37-8.2-.33-17.79,0-26,3.31,1.17,2.51-7.85,1-10,.32-2.65.67-5.34,1-8,.16-1.31.83-2.63,1-5,.19-2.64-.12-5.35,0-8,2.95.63,1.93-1.48,2-4,.04-1.31.1-2.7,0-4,1.31-.48.95-1.91,1-3,.09-1.97-.2-4.09,0-6,2.13.24,2.24.12,2-2,.1-.11.07-2.38,0-3,.96-.26.95-1.15,1-2,.07-1.18-.26-4.56,0-5,.05-.09,1.34.43,1.95-.74.32-.62,1.24-6,1.04-6.25-1.87-2.38-3.69,5.36-4,5.99Z"/>
                            <path class="cls-1" d="M543,614c-5.3,1.12-11.57,2.12-17,0,.18,0,1.22-.94,3.43-1.05,4.01-.2,9.9-.59,13.57,1.05Z"/>
                            <path class="cls-3" d="M364,267c1.51,2.15,2.31,11.17-1,10,.15-3.69.59-6.64,1-10Z"/>
                            <path class="cls-3" d="M363,303c3.24-1.2,2.56,6.97,1,9-.37-2.99-.85-5.65-1-9Z"/>
                            <path class="cls-3" d="M371,216c.3-.64,2.12-8.37,4-5.99.2.25-.72,5.64-1.04,6.25-.61,1.18-1.9.65-1.95.74l-1-1Z"/>
                            <path class="cls-1" d="M587,609v-2c1.1-.16,4.35-2.3,4.99.51.93,4.08-4.67,1.48-4.99,1.49Z"/>
                            <path class="cls-1" d="M555,613c-1.82.23-5.74,2.77-8,0,2.2-.52,5.63-2.59,8,0Z"/>
                            <path class="cls-1" d="M583,610c-1.3.32-2.82,1.71-4.83,1.82-1.51.08-2.06-.82-2.17-.82,1.53-1.2,5.68-2.88,7-1Z"/>
                            <path class="cls-3" d="M366,326c-3.01,1.08-2.69-4.24-1-6,.17,1.54.73,3.93,1,6Z"/>
                            <path class="cls-3" d="M366,254c-.17,2.37-.84,3.69-1,5-1.74-1.69-1.91-5.97,1-5Z"/>
                            <path class="cls-1" d="M570,611c.97,2.91-3.31,2.74-5,1,1.31-.16,2.47-.89,5-1Z"/>
                            <path class="cls-3" d="M368,242c-.07,2.52.95,4.63-2,4,.12-2.51-1-4.62,2-4Z"/>
                            <path class="cls-1" d="M509,614c.84,2.67-2.28,2.91-4,1,1.25-.27,1.73-.81,4-1Z"/>
                            <path class="cls-3" d="M369,235c-.05,1.09.31,2.52-1,3-.07-.87-3.07-3.5,1-3Z"/>
                            <path class="cls-3" d="M372,222c-.05.85-.04,1.74-1,2-.06-.53-2.95-2.38,1-2Z"/>
                            <path class="cls-3" d="M371,227c.24,2.12.13,2.24-2,2,.38-3.7,1.42-1.34,2-2Z"/>
                            <path class="cls-1" d="M577,604c1.73-1.71,2.3-1.36,2,1-1.53-.33-1.89-.97-2-1Z"/>
                            <path class="cls-1" d="M583,605c3.67.42,1.34,1.28,2,2-2.12.24-2.24.13-2-2Z"/>
                            <path class="cls-1" d="M501,616c-.11.03-.54.65-2,1-.3-2.37.27-2.71,2-1Z"/>
                            <path class="cls-1" d="M495,617c-.77.6,1.86,1.19-2,2-.24-2.13-.12-2.24,2-2Z"/>
                            </g>
                        </g>
                        </svg>
                """
            },
            {
                "name": "Profil senat_digit",
                "flag": ESysProfileFlag.MAIN_PROFILE.value,
                "description_str": "Profil principal senat_digit",
                "is_default": True,
                "system_reserved_actions": True,
                "profil_system_roles": [
                    {
                        "flag": ESysProfilSuperUserRoleFlag.MAIN_PROFILE_SUPER_ADMIN.value,
                        "is_default": True,
                        "system_reserved_actions": True,
                        "name": "Administrateur du profil système",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    # Sénat-Digit chamber roles. Granted distinct permission
                    # cuts in `seed_senat_digit_modules_rbac` so a sénateur
                    # can vote but not open a session, and a greffier can
                    # orchestrate a session but cannot cast a ballot.
                    {
                        "flag": ESysProfilSuperUserRoleFlag.SENATEUR.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Sénateur",
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.GREFFIER.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Greffier",
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TRANS_RH_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Ressources humaines",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TRANS_FINANCER_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Financier",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TRANS_EXPENSE_TYPE_PERSON_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Opérateur de saisie de dépense",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TRANS_ACCOUTANT_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Comptable",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.OPERATION_STAFF_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Enrôlement & ventes",
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.DISTRIBUTOR_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Distributeur",
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.CONTROLLER_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Contrôleur",
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.REGULATOR_OF_LINE_LAUNCHING_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Commis lanceur - Régulateur de lancement",
                        # meta data
                        "is_activated": True,
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    }, 
                    {
                        "flag": ESysProfilSuperUserRoleFlag.REGULATOR_OF_LINE_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Régulateur de line",
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.DRIVER_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Chauffeur | Conducteur",
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                    {
                        "flag": ESysProfilSuperUserRoleFlag.PERCEPTOR_TRANS_ROLE.value,
                        "is_default": False,
                        "system_reserved_actions": True,
                        "name": "Percepteur",
                        "cfg_organism_chart_id":"69cd4550c6639f659c77cfeb",
                        "rbac_profile_id":"69c28784830030b918bcea08",
                        "sys_organization_id":"69c28d482d49176f0fb5710f",
                        # meta data
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                ],
                "svg_icon": """<svg id="Layer_2" data-name="Layer 2" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 786 782">
                        <defs>
                            <style>
                            .cls-1 {
                                fill: #96cdd3;
                            }

                            .cls-2 {
                                fill: #058996;
                            }

                            .cls-3 {
                                fill: #9cd0d5;
                            }

                            .cls-4 {
                                fill: #fdfefe;
                            }
                            </style>
                        </defs>
                        <g id="Layer_1-2" data-name="Layer 1">
                            <g>
                            <path class="cls-4" d="M786,0v782H0V0h786ZM577,604c-5.94-1.82-22.48-8.97-21.99-16.43.46-7.01,17.92-12.92,23.74-15.32,53.18-21.95,104.97-31.97,150.27-70.73,13.98-11.96,31.3-27.98,34.98-46.51-15.38,3.8-30.27,11.01-46.45,12.04-16.31,1.04-40.07.69-31.42-22.42,12.11-32.35,49.68-76.2,49.59-111.41,0-1.65-.56-6.78-2.29-7.16-40.39,13.04-68.79,86.31-115.92,81.92-21.8-2.03-23.2-18.4-19.22-36.2.69-3.07,3.45-6.88,3.39-10.11-.07-4.3-2.79-11.05-7.97-9.5-2.59.78-16.27,19.56-19.68,23.34-10.7,11.88-25.05,24.4-37.55,34.45-17.78,14.28-38.41,29.49-60.42,35.99-6.28-41.81-5.33-87.67,8.49-127.93,9.23-26.91,29.74-54.43,47.07-76.93,4.6-5.98,31.46-36.52,31.37-40.63-.17-7.54-14.78-3.28-19.18-2.18-23.62,5.9-45.23,24.95-70.76,15.18-4.77-1.83-5.28-2.98-5.91-8.09-7.14-57.6,13.62-135.67,57.87-174.89,2.49-2.21,21.5-13.25,11.31-16.28-8.51-2.53-25.83,5.96-33.97,9.62-51.16,22.97-96.09,50.28-134.84,91.16-21.02,22.17-66.42,86.67-94.03,34.06-8.15-15.54-5.42-28.14-9.9-42.1-.18-.55-5.32-7.49-5.73-7.74-3.33-1.94-2.54,1.26-3.3,2.76-39.8,78.6-34.02,178.1-8.23,260.24,4.65,14.82,11.91,29.13,14.43,44.57s4.55,22.69-13.17,17.17c-34.62-10.79-58.16-63.78-75.38-92.62-7.36-12.32-16.06-27.27-30.16-32.33-6.53,21.25,9.4,39.86-2.64,60.88-5.84,10.2-14.3,7.1-23.35,3.6-21.09-8.16-49.92-26.23-65.57-42.47-1.5-1.56-.91-3.89-3.78-2.88s-4.68,7.41-4.75,10.37c-.35,14.55,18.4,36.13,25.46,49.62,9.93,18.99,29.41,67.2.91,78.67-13.95,5.61-22.41,1.11-35.8.22-1.12-.07-6.49-.9-5.48,1.47.75,1.75,11.37,14.24,13.48,16.53,27.86,30.27,71.99,54.76,110.55,68.45s84.6,19.99,122.15,37.85c3.56,1.69,18.53,8.03,13.36,12.72-5.54,5.02-27.88,14.47-35.54,16.48l-22,3.48c31.3,5.41,63.8,2.58,95.48,2,18.75-.34,38.16-2.16,57.05-1.03,10.13.6,20.3,2.65,29.45,7.04-1.21-32.78-7.52-66.46-19.51-96.98-10.35-26.33-25.73-47.58-34.5-75.5-24.19-76.99-20.65-160.78,14.02-233.52l1,1c-.26.44.07,3.82,0,5-3.95-.38-1.06,1.47-1,2,.07.62.1,2.89,0,3-.58.66-1.62-1.7-2,2-.2,1.91.09,4.03,0,6-4.07-.5-1.07,2.13-1,3,.1,1.3.04,2.69,0,4-3-.62-1.88,1.49-2,4-.12,2.65.19,5.36,0,8-2.91-.97-2.74,3.31-1,5-.33,2.66-.68,5.35-1,8-.41,3.36-.85,6.31-1,10-.33,8.21-.37,17.8,0,26,.15,3.35.63,6.01,1,9,.33,2.67.7,5.29,1,8-1.69,1.76-2.01,7.08,1,6,9.35,72.46,43.82,130.37,62.71,199.79,20.26,74.46,26.11,152.52-8.86,223.56-3.11,6.33-7.28,12.08-9.85,18.65h30c14.51-26.72,24.06-56.32,27.88-86.62,2.71-21.47-2.83-56.52,25.12-62.38,3.86-.81,1.23-1.4,2-2,.39-.3,3,.24,4,0,1.46-.35,1.89-.97,2-1,1.28-.38,2.69-.72,4-1,1.72,1.91,4.84,1.67,4-1,5.44-.45,11.45.22,17,0,5.43,2.12,11.7,1.12,17,0,1.34-.28,2.66-.69,4-1,2.26,2.77,6.18.23,8,0,3.27-.42,6.7-.59,10-1,1.69,1.74,5.97,1.91,5-1,1.99-.09,4.01.04,6,0,.12,0,.66.89,2.17.82,2.01-.1,3.53-1.49,4.83-1.82s2.83-.97,4-1c.32,0,5.92,2.6,4.99-1.49-.64-2.81-3.9-.67-4.99-.51-.46.07-1.93.07-2,0-.66-.72,1.67-1.58-2-2-1.26-.14-2.87.24-4,0,.3-2.36-.27-2.71-2-1Z"/>
                            <path class="cls-2" d="M371,216c-34.67,72.74-38.21,156.53-14.02,233.52,8.77,27.92,24.15,49.16,34.5,75.5,11.99,30.52,18.3,64.19,19.51,96.98-9.16-4.39-19.32-6.43-29.45-7.04-18.9-1.13-38.3.69-57.05,1.03-31.68.57-64.19,3.41-95.48-2l22-3.48c7.66-2.01,30-11.47,35.54-16.48,5.17-4.68-9.8-11.02-13.36-12.72-37.55-17.86-82.84-23.89-122.15-37.85s-82.69-38.17-110.55-68.45c-2.11-2.29-12.73-14.77-13.48-16.53-1.01-2.37,4.36-1.55,5.48-1.47,13.39.89,21.85,5.39,35.8-.22,28.5-11.47,9.02-59.68-.91-78.67-7.06-13.49-25.81-35.07-25.46-49.62.07-2.96,1.79-9.33,4.75-10.37s2.27,1.32,3.78,2.88c15.66,16.23,44.48,34.31,65.57,42.47,9.05,3.5,17.51,6.6,23.35-3.6,12.04-21.02-3.89-39.63,2.64-60.88,14.1,5.06,22.8,20,30.16,32.33,17.23,28.84,40.76,81.83,75.38,92.62,17.71,5.52,15.58-2.43,13.17-17.17s-9.78-29.75-14.43-44.57c-25.79-82.14-31.57-181.65,8.23-260.24.76-1.5-.03-4.7,3.3-2.76.42.24,5.56,7.19,5.73,7.74,4.49,13.96,1.75,26.56,9.9,42.1,27.61,52.61,73.01-11.88,94.03-34.06,38.75-40.88,83.68-68.19,134.84-91.16,8.15-3.66,25.47-12.15,33.97-9.62,10.19,3.03-8.82,14.07-11.31,16.28-44.25,39.22-65.01,117.29-57.87,174.89.63,5.11,1.14,6.26,5.91,8.09,25.53,9.77,47.14-9.28,70.76-15.18,4.4-1.1,19.01-5.36,19.18,2.18.09,4.11-26.76,34.65-31.37,40.63-17.32,22.51-37.83,50.03-47.07,76.93-13.81,40.26-14.76,86.11-8.49,127.93,22.02-6.5,42.65-21.71,60.42-35.99,12.51-10.05,26.86-22.57,37.55-34.45,3.41-3.79,17.1-22.57,19.68-23.34,5.18-1.56,7.91,5.2,7.97,9.5.05,3.23-2.71,7.04-3.39,10.11-3.99,17.8-2.58,34.17,19.22,36.2,47.13,4.39,75.53-68.88,115.92-81.92,1.73.38,2.29,5.51,2.29,7.16.09,35.21-37.48,79.06-49.59,111.41-8.65,23.11,15.11,23.46,31.42,22.42,16.17-1.03,31.07-8.25,46.45-12.04-3.68,18.53-21,34.55-34.98,46.51-45.3,38.76-97.09,48.78-150.27,70.73-5.82,2.4-23.28,8.31-23.74,15.32-.49,7.46,16.05,14.61,21.99,16.43.11.03.47.67,2,1,1.13.24,2.74-.14,4,0-.24,2.13-.12,2.24,2,2,.07.07,1.54.07,2,0v2c-1.17.03-2.76.69-4,1-1.32-1.88-5.47-.2-7,1-1.99.04-4.01-.09-6,0-2.53.11-3.69.84-5,1-3.3.41-6.73.58-10,1-2.37-2.59-5.8-.52-8,0-1.34.31-2.66.72-4,1-3.67-1.64-9.55-1.25-13.57-1.05-2.22.11-3.26,1.05-3.43,1.05-5.55.22-11.56-.45-17,0-2.27.19-2.75.73-4,1s-2.72.62-4,1c-1.73-1.71-2.3-1.37-2,1-1,.24-3.61-.3-4,0-2.12-.24-2.24-.13-2,2-27.95,5.85-22.42,40.91-25.12,62.38-3.82,30.3-13.37,59.9-27.88,86.62h-30c2.57-6.57,6.74-12.32,9.85-18.65,34.97-71.04,29.12-149.1,8.86-223.56-18.89-69.42-53.36-127.33-62.71-199.79-.27-2.07-.83-4.46-1-6-.3-2.71-.67-5.33-1-8,1.56-2.03,2.24-10.2-1-9-.37-8.2-.33-17.79,0-26,3.31,1.17,2.51-7.85,1-10,.32-2.65.67-5.34,1-8,.16-1.31.83-2.63,1-5,.19-2.64-.12-5.35,0-8,2.95.63,1.93-1.48,2-4,.04-1.31.1-2.7,0-4,1.31-.48.95-1.91,1-3,.09-1.97-.2-4.09,0-6,2.13.24,2.24.12,2-2,.1-.11.07-2.38,0-3,.96-.26.95-1.15,1-2,.07-1.18-.26-4.56,0-5,.05-.09,1.34.43,1.95-.74.32-.62,1.24-6,1.04-6.25-1.87-2.38-3.69,5.36-4,5.99Z"/>
                            <path class="cls-1" d="M543,614c-5.3,1.12-11.57,2.12-17,0,.18,0,1.22-.94,3.43-1.05,4.01-.2,9.9-.59,13.57,1.05Z"/>
                            <path class="cls-3" d="M364,267c1.51,2.15,2.31,11.17-1,10,.15-3.69.59-6.64,1-10Z"/>
                            <path class="cls-3" d="M363,303c3.24-1.2,2.56,6.97,1,9-.37-2.99-.85-5.65-1-9Z"/>
                            <path class="cls-3" d="M371,216c.3-.64,2.12-8.37,4-5.99.2.25-.72,5.64-1.04,6.25-.61,1.18-1.9.65-1.95.74l-1-1Z"/>
                            <path class="cls-1" d="M587,609v-2c1.1-.16,4.35-2.3,4.99.51.93,4.08-4.67,1.48-4.99,1.49Z"/>
                            <path class="cls-1" d="M555,613c-1.82.23-5.74,2.77-8,0,2.2-.52,5.63-2.59,8,0Z"/>
                            <path class="cls-1" d="M583,610c-1.3.32-2.82,1.71-4.83,1.82-1.51.08-2.06-.82-2.17-.82,1.53-1.2,5.68-2.88,7-1Z"/>
                            <path class="cls-3" d="M366,326c-3.01,1.08-2.69-4.24-1-6,.17,1.54.73,3.93,1,6Z"/>
                            <path class="cls-3" d="M366,254c-.17,2.37-.84,3.69-1,5-1.74-1.69-1.91-5.97,1-5Z"/>
                            <path class="cls-1" d="M570,611c.97,2.91-3.31,2.74-5,1,1.31-.16,2.47-.89,5-1Z"/>
                            <path class="cls-3" d="M368,242c-.07,2.52.95,4.63-2,4,.12-2.51-1-4.62,2-4Z"/>
                            <path class="cls-1" d="M509,614c.84,2.67-2.28,2.91-4,1,1.25-.27,1.73-.81,4-1Z"/>
                            <path class="cls-3" d="M369,235c-.05,1.09.31,2.52-1,3-.07-.87-3.07-3.5,1-3Z"/>
                            <path class="cls-3" d="M372,222c-.05.85-.04,1.74-1,2-.06-.53-2.95-2.38,1-2Z"/>
                            <path class="cls-3" d="M371,227c.24,2.12.13,2.24-2,2,.38-3.7,1.42-1.34,2-2Z"/>
                            <path class="cls-1" d="M577,604c1.73-1.71,2.3-1.36,2,1-1.53-.33-1.89-.97-2-1Z"/>
                            <path class="cls-1" d="M583,605c3.67.42,1.34,1.28,2,2-2.12.24-2.24.13-2-2Z"/>
                            <path class="cls-1" d="M501,616c-.11.03-.54.65-2,1-.3-2.37.27-2.71,2-1Z"/>
                            <path class="cls-1" d="M495,617c-.77.6,1.86,1.19-2,2-.24-2.13-.12-2.24,2-2Z"/>
                            </g>
                        </g>
                        </svg>
                """
            },
            {
                "name": "Profil par defaut pour le test",
                "flag": ESysProfileFlag.TEST_SYS_PROFIL.value,
                "description_str": "Profil par defaut pour le test",
                "is_default": True,
                "system_reserved_actions": True,
                "profil_system_roles": [
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TEST_PROFIL_SUPER_ADMIN.value,
                        "is_default": True,
                        "system_reserved_actions": True,
                        "name": "Administrateur (test)",
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                ],
                "svg_icon": """<svg id="fi_11495468" enable-background="new 0 0 512 512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg"><path d="m503.954 493.069c-3.682-34.414-26.675-62.332-57.555-73.56 11.151-8.923 18.312-22.633 18.312-37.992 0-24.146-17.683-44.23-40.777-48.006v-27.054c0-4.418-3.582-8-8-8h-97.194c-9.083-8.368-19.835-14.909-31.683-19.11 11.953-9.288 19.666-23.786 19.666-40.061 0-3.043-.284-6.019-.801-8.916h187.808c4.418 0 8-3.582 8-8s-3.582-8-8-8h-43.428c.004-26.317.024-44.303.045-62.285.021-17.989.042-35.977.045-62.305h14.425c4.535 0 8.534-2.555 10.438-6.667s1.262-8.815-1.673-12.271l-48.147-56.708c-2.189-2.577-5.384-4.054-8.766-4.053-3.381 0-6.574 1.479-8.761 4.055l-48.145 56.704c-2.936 3.456-3.577 8.158-1.674 12.271 1.902 4.113 5.902 6.668 10.438 6.668h14.425c.003 26.329.024 44.316.045 62.305.021 17.982.042 35.968.045 62.285h-17.917v-90.868c0-4.418-3.582-8-8-8h-51.26c-4.418 0-8 3.582-8 8v87.184c-4.588-6.695-10.737-12.239-17.921-16.102v-33.241c0-4.418-3.582-8-8-8h-51.261c-4.418 0-8 3.582-8 8v51.581c-.29.475-.563.961-.837 1.446h-16.569c-4.418 0-8 3.582-8 8s3.582 8 8 8h10.802c-.516 2.897-.801 5.873-.801 8.916 0 16.275 7.713 30.773 19.667 40.061-11.848 4.202-22.601 10.742-31.684 19.11h-97.321c-4.418 0-8 3.582-8 8v27.076c-23.033 3.828-40.652 23.881-40.652 47.983 0 15.359 7.162 29.069 18.313 37.992-30.88 11.228-53.873 39.146-57.555 73.56-.242 2.257.486 4.51 2.004 6.199 1.518 1.688 3.681 2.652 5.95 2.652h159.88c2.27 0 4.433-.964 5.95-2.653 1.518-1.688 2.246-3.941 2.004-6.199-3.683-34.413-26.676-62.331-57.554-73.559 11.151-8.923 18.313-22.633 18.313-37.993 0-24.102-17.62-44.155-40.652-47.983v-19.076h75.525c-8.282 12.187-13.761 26.504-15.431 42.107-.242 2.257.486 4.51 2.004 6.199 1.518 1.688 3.681 2.652 5.95 2.652h168.023c2.27 0 4.433-.964 5.95-2.652 1.518-1.688 2.246-3.942 2.004-6.199-1.669-15.602-7.148-29.919-15.431-42.106h75.399v19.099c-22.971 3.88-40.526 23.903-40.526 47.961 0 15.359 7.162 29.07 18.313 37.992-30.879 11.228-53.872 39.146-57.554 73.56-.242 2.257.486 4.51 2.004 6.198s3.681 2.653 5.95 2.653h159.879c2.27 0 4.433-.964 5.95-2.652 1.518-1.687 2.246-3.941 2.004-6.198zm-337.528-7.149h-140.973c7.55-32.339 36.426-55.752 70.487-55.752 34.06 0 62.936 23.413 70.486 55.752zm-37.833-104.403c0 18.004-14.647 32.652-32.652 32.652s-32.652-14.647-32.652-32.652 14.647-32.652 32.652-32.652 32.652 14.647 32.652 32.652zm139.054-55.445-11.647 13.151-11.647-13.151 11.469-36.06c.056 0 .112-.004.169-.004h.01.01c.056 0 .111.003.167.004zm131.349-174.006c-.023-19.749-.046-39.497-.046-70.287 0-4.418-3.582-8-8-8h-12.694l38.416-45.245 38.416 45.245h-12.694c-4.418 0-8 3.582-8 8 0 30.79-.022 50.538-.046 70.287-.02 17.988-.042 35.978-.045 62.304h-35.261c-.004-26.326-.025-44.316-.046-62.304zm-49.872-20.565v82.868h-35.26v-82.868zm-85.181 37.841v19.847c-2.589-.409-5.24-.626-7.942-.626-10.054 0-19.426 2.953-27.318 8.019v-27.239h35.26zm-42.666 69.944c0-19.146 15.577-34.723 34.724-34.723s34.723 15.577 34.723 34.723c0 19.143-15.571 34.717-34.712 34.723-.003 0-.007 0-.01 0s-.007 0-.01 0c-19.143-.006-34.715-15.58-34.715-34.723zm17.106 52.767-10.654 33.499c-.854 2.685-.232 5.62 1.635 7.729l14.29 16.135h-62.242c6.489-28.661 28.811-50.76 56.971-57.363zm29.964 57.362 14.29-16.134c1.867-2.109 2.488-5.044 1.635-7.729l-10.654-33.499c28.159 6.603 50.482 28.702 56.972 57.362zm115.061 32.102c0-18.004 14.647-32.652 32.652-32.652 18.004 0 32.651 14.648 32.651 32.652s-14.647 32.652-32.651 32.652c-18.004-.001-32.652-14.648-32.652-32.652zm-37.834 104.403c7.55-32.339 36.426-55.751 70.486-55.751s62.937 23.413 70.486 55.752zm-332.448-357.598 11.187 4.306c1.735 5.947 4.111 11.678 7.097 17.116l-4.869 10.961c-1.343 3.025-.686 6.564 1.654 8.904l17.326 17.326c2.341 2.34 5.878 2.998 8.904 1.655l10.967-4.871c5.438 2.985 11.166 5.359 17.11 7.094l4.308 11.19c1.188 3.088 4.156 5.126 7.466 5.126h24.502c3.31 0 6.277-2.038 7.466-5.126l4.306-11.187c5.947-1.735 11.678-4.11 17.116-7.096l10.962 4.869c3.023 1.343 6.563.686 8.904-1.654l17.326-17.327c2.34-2.34 2.997-5.879 1.654-8.904l-4.87-10.966c2.983-5.437 5.358-11.166 7.093-17.11l11.19-4.307c3.089-1.188 5.127-4.156 5.127-7.466v-24.501c0-3.31-2.038-6.277-5.126-7.466l-11.187-4.306c-1.735-5.948-4.111-11.678-7.097-17.116l4.869-10.962c1.343-3.024.686-6.564-1.655-8.904l-17.326-17.326c-2.339-2.34-5.878-2.999-8.903-1.654l-10.967 4.87c-5.438-2.985-11.166-5.359-17.11-7.094l-4.307-11.19c-1.188-3.088-4.156-5.126-7.466-5.126h-24.502c-3.31 0-6.277 2.038-7.466 5.126l-4.309 11.19c-5.943 1.735-11.672 4.11-17.109 7.094l-10.967-4.87c-3.026-1.345-6.564-.685-8.904 1.654l-17.326 17.326c-2.34 2.34-2.997 5.879-1.654 8.904l4.87 10.965c-2.985 5.438-5.36 11.167-7.095 17.112l-11.189 4.307c-3.088 1.189-5.126 4.156-5.126 7.466v24.502c0 3.31 2.038 6.278 5.126 7.466zm10.874-26.475 9.875-3.801c2.462-.947 4.298-3.048 4.909-5.614 1.704-7.166 4.533-13.989 8.407-20.28 1.384-2.247 1.57-5.031.5-7.442l-4.299-9.68 9.558-9.558 9.681 4.3c2.409 1.07 5.194.884 7.441-.5 6.292-3.874 13.115-6.703 20.28-8.408 2.565-.611 4.666-2.447 5.613-4.909l3.802-9.875h13.517l3.801 9.875c.947 2.462 3.048 4.298 5.613 4.909 7.166 1.705 13.989 4.534 20.281 8.408 2.247 1.384 5.032 1.57 7.441.499l9.681-4.299 9.558 9.558-4.298 9.676c-1.071 2.411-.884 5.196.5 7.442 3.874 6.29 6.703 13.115 8.41 20.285.61 2.566 2.446 4.667 4.908 5.614l9.872 3.8v13.517l-9.875 3.801c-2.462.948-4.299 3.048-4.909 5.614-1.706 7.166-4.534 13.99-8.408 20.281-1.383 2.247-1.569 5.03-.499 7.441l4.299 9.68-9.558 9.559-9.676-4.297c-2.409-1.071-5.194-.885-7.442.499-6.291 3.875-13.116 6.704-20.285 8.41-2.566.611-4.667 2.447-5.614 4.909l-3.8 9.872h-13.515l-3.802-9.875c-.947-2.461-3.048-4.298-5.613-4.909-7.165-1.705-13.989-4.534-20.281-8.408-2.249-1.384-5.032-1.568-7.441-.499l-9.681 4.299-9.558-9.558 4.298-9.676c1.07-2.412.884-5.196-.5-7.443-3.874-6.291-6.704-13.115-8.41-20.285-.61-2.566-2.446-4.667-4.908-5.614l-9.872-3.8v-13.518zm82.525 57.489c27.974 0 50.732-22.758 50.732-50.731 0-27.974-22.759-50.732-50.732-50.732s-50.731 22.758-50.731 50.732 22.758 50.731 50.731 50.731zm0-85.462c19.151 0 34.732 15.581 34.732 34.732s-15.581 34.731-34.732 34.731-34.731-15.58-34.731-34.731c0-19.152 15.58-34.732 34.731-34.732z"></path>
                    </svg>
                """
            },
            {
                "name": "Profil client senat_digit",
                "flag": ESysProfileFlag.TRANS_CUSTOMER.value,
                "description_str": "Profil client senat_digit",
                "is_default": True,
                "system_reserved_actions": True,
                "profil_system_roles": [
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TRANS_CUSTOMER_ROLE.value,
                        "is_default": True,
                        "system_reserved_actions": True,
                        "name": "Client senat_digit",
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                ],
                "svg_icon": """<svg id="fi_11495468" enable-background="new 0 0 512 512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg"><path d="m503.954 493.069c-3.682-34.414-26.675-62.332-57.555-73.56 11.151-8.923 18.312-22.633 18.312-37.992 0-24.146-17.683-44.23-40.777-48.006v-27.054c0-4.418-3.582-8-8-8h-97.194c-9.083-8.368-19.835-14.909-31.683-19.11 11.953-9.288 19.666-23.786 19.666-40.061 0-3.043-.284-6.019-.801-8.916h187.808c4.418 0 8-3.582 8-8s-3.582-8-8-8h-43.428c.004-26.317.024-44.303.045-62.285.021-17.989.042-35.977.045-62.305h14.425c4.535 0 8.534-2.555 10.438-6.667s1.262-8.815-1.673-12.271l-48.147-56.708c-2.189-2.577-5.384-4.054-8.766-4.053-3.381 0-6.574 1.479-8.761 4.055l-48.145 56.704c-2.936 3.456-3.577 8.158-1.674 12.271 1.902 4.113 5.902 6.668 10.438 6.668h14.425c.003 26.329.024 44.316.045 62.305.021 17.982.042 35.968.045 62.285h-17.917v-90.868c0-4.418-3.582-8-8-8h-51.26c-4.418 0-8 3.582-8 8v87.184c-4.588-6.695-10.737-12.239-17.921-16.102v-33.241c0-4.418-3.582-8-8-8h-51.261c-4.418 0-8 3.582-8 8v51.581c-.29.475-.563.961-.837 1.446h-16.569c-4.418 0-8 3.582-8 8s3.582 8 8 8h10.802c-.516 2.897-.801 5.873-.801 8.916 0 16.275 7.713 30.773 19.667 40.061-11.848 4.202-22.601 10.742-31.684 19.11h-97.321c-4.418 0-8 3.582-8 8v27.076c-23.033 3.828-40.652 23.881-40.652 47.983 0 15.359 7.162 29.069 18.313 37.992-30.88 11.228-53.873 39.146-57.555 73.56-.242 2.257.486 4.51 2.004 6.199 1.518 1.688 3.681 2.652 5.95 2.652h159.88c2.27 0 4.433-.964 5.95-2.653 1.518-1.688 2.246-3.941 2.004-6.199-3.683-34.413-26.676-62.331-57.554-73.559 11.151-8.923 18.313-22.633 18.313-37.993 0-24.102-17.62-44.155-40.652-47.983v-19.076h75.525c-8.282 12.187-13.761 26.504-15.431 42.107-.242 2.257.486 4.51 2.004 6.199 1.518 1.688 3.681 2.652 5.95 2.652h168.023c2.27 0 4.433-.964 5.95-2.652 1.518-1.688 2.246-3.942 2.004-6.199-1.669-15.602-7.148-29.919-15.431-42.106h75.399v19.099c-22.971 3.88-40.526 23.903-40.526 47.961 0 15.359 7.162 29.07 18.313 37.992-30.879 11.228-53.872 39.146-57.554 73.56-.242 2.257.486 4.51 2.004 6.198s3.681 2.653 5.95 2.653h159.879c2.27 0 4.433-.964 5.95-2.652 1.518-1.687 2.246-3.941 2.004-6.198zm-337.528-7.149h-140.973c7.55-32.339 36.426-55.752 70.487-55.752 34.06 0 62.936 23.413 70.486 55.752zm-37.833-104.403c0 18.004-14.647 32.652-32.652 32.652s-32.652-14.647-32.652-32.652 14.647-32.652 32.652-32.652 32.652 14.647 32.652 32.652zm139.054-55.445-11.647 13.151-11.647-13.151 11.469-36.06c.056 0 .112-.004.169-.004h.01.01c.056 0 .111.003.167.004zm131.349-174.006c-.023-19.749-.046-39.497-.046-70.287 0-4.418-3.582-8-8-8h-12.694l38.416-45.245 38.416 45.245h-12.694c-4.418 0-8 3.582-8 8 0 30.79-.022 50.538-.046 70.287-.02 17.988-.042 35.978-.045 62.304h-35.261c-.004-26.326-.025-44.316-.046-62.304zm-49.872-20.565v82.868h-35.26v-82.868zm-85.181 37.841v19.847c-2.589-.409-5.24-.626-7.942-.626-10.054 0-19.426 2.953-27.318 8.019v-27.239h35.26zm-42.666 69.944c0-19.146 15.577-34.723 34.724-34.723s34.723 15.577 34.723 34.723c0 19.143-15.571 34.717-34.712 34.723-.003 0-.007 0-.01 0s-.007 0-.01 0c-19.143-.006-34.715-15.58-34.715-34.723zm17.106 52.767-10.654 33.499c-.854 2.685-.232 5.62 1.635 7.729l14.29 16.135h-62.242c6.489-28.661 28.811-50.76 56.971-57.363zm29.964 57.362 14.29-16.134c1.867-2.109 2.488-5.044 1.635-7.729l-10.654-33.499c28.159 6.603 50.482 28.702 56.972 57.362zm115.061 32.102c0-18.004 14.647-32.652 32.652-32.652 18.004 0 32.651 14.648 32.651 32.652s-14.647 32.652-32.651 32.652c-18.004-.001-32.652-14.648-32.652-32.652zm-37.834 104.403c7.55-32.339 36.426-55.751 70.486-55.751s62.937 23.413 70.486 55.752zm-332.448-357.598 11.187 4.306c1.735 5.947 4.111 11.678 7.097 17.116l-4.869 10.961c-1.343 3.025-.686 6.564 1.654 8.904l17.326 17.326c2.341 2.34 5.878 2.998 8.904 1.655l10.967-4.871c5.438 2.985 11.166 5.359 17.11 7.094l4.308 11.19c1.188 3.088 4.156 5.126 7.466 5.126h24.502c3.31 0 6.277-2.038 7.466-5.126l4.306-11.187c5.947-1.735 11.678-4.11 17.116-7.096l10.962 4.869c3.023 1.343 6.563.686 8.904-1.654l17.326-17.327c2.34-2.34 2.997-5.879 1.654-8.904l-4.87-10.966c2.983-5.437 5.358-11.166 7.093-17.11l11.19-4.307c3.089-1.188 5.127-4.156 5.127-7.466v-24.501c0-3.31-2.038-6.277-5.126-7.466l-11.187-4.306c-1.735-5.948-4.111-11.678-7.097-17.116l4.869-10.962c1.343-3.024.686-6.564-1.655-8.904l-17.326-17.326c-2.339-2.34-5.878-2.999-8.903-1.654l-10.967 4.87c-5.438-2.985-11.166-5.359-17.11-7.094l-4.307-11.19c-1.188-3.088-4.156-5.126-7.466-5.126h-24.502c-3.31 0-6.277 2.038-7.466 5.126l-4.309 11.19c-5.943 1.735-11.672 4.11-17.109 7.094l-10.967-4.87c-3.026-1.345-6.564-.685-8.904 1.654l-17.326 17.326c-2.34 2.34-2.997 5.879-1.654 8.904l4.87 10.965c-2.985 5.438-5.36 11.167-7.095 17.112l-11.189 4.307c-3.088 1.189-5.126 4.156-5.126 7.466v24.502c0 3.31 2.038 6.278 5.126 7.466zm10.874-26.475 9.875-3.801c2.462-.947 4.298-3.048 4.909-5.614 1.704-7.166 4.533-13.989 8.407-20.28 1.384-2.247 1.57-5.031.5-7.442l-4.299-9.68 9.558-9.558 9.681 4.3c2.409 1.07 5.194.884 7.441-.5 6.292-3.874 13.115-6.703 20.28-8.408 2.565-.611 4.666-2.447 5.613-4.909l3.802-9.875h13.517l3.801 9.875c.947 2.462 3.048 4.298 5.613 4.909 7.166 1.705 13.989 4.534 20.281 8.408 2.247 1.384 5.032 1.57 7.441.499l9.681-4.299 9.558 9.558-4.298 9.676c-1.071 2.411-.884 5.196.5 7.442 3.874 6.29 6.703 13.115 8.41 20.285.61 2.566 2.446 4.667 4.908 5.614l9.872 3.8v13.517l-9.875 3.801c-2.462.948-4.299 3.048-4.909 5.614-1.706 7.166-4.534 13.99-8.408 20.281-1.383 2.247-1.569 5.03-.499 7.441l4.299 9.68-9.558 9.559-9.676-4.297c-2.409-1.071-5.194-.885-7.442.499-6.291 3.875-13.116 6.704-20.285 8.41-2.566.611-4.667 2.447-5.614 4.909l-3.8 9.872h-13.515l-3.802-9.875c-.947-2.461-3.048-4.298-5.613-4.909-7.165-1.705-13.989-4.534-20.281-8.408-2.249-1.384-5.032-1.568-7.441-.499l-9.681 4.299-9.558-9.558 4.298-9.676c1.07-2.412.884-5.196-.5-7.443-3.874-6.291-6.704-13.115-8.41-20.285-.61-2.566-2.446-4.667-4.908-5.614l-9.872-3.8v-13.518zm82.525 57.489c27.974 0 50.732-22.758 50.732-50.731 0-27.974-22.759-50.732-50.732-50.732s-50.731 22.758-50.731 50.732 22.758 50.731 50.731 50.731zm0-85.462c19.151 0 34.732 15.581 34.732 34.732s-15.581 34.731-34.732 34.731-34.731-15.58-34.731-34.731c0-19.152 15.58-34.732 34.731-34.732z"></path>
                    </svg>
                """
            },
            {
                "name": "Profil visiteur",
                "flag": ESysProfileFlag.TRANS_VISITOR.value,
                "description_str": "Profil visiteur",
                "is_default": True,
                "system_reserved_actions": True,
                "profil_system_roles": [
                    {
                        "flag": ESysProfilSuperUserRoleFlag.TRANS_VISITOR_ROLE.value,
                        "is_default": True,
                        "system_reserved_actions": True,
                        "name": "Administrateur (test)",
                        "is_activated": True,
                        "is_hidden": False,
                        "is_locked": False,
                        "is_deleted": False,
                    },
                ],
                "svg_icon": """<svg id="fi_11495468" enable-background="new 0 0 512 512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg"><path d="m503.954 493.069c-3.682-34.414-26.675-62.332-57.555-73.56 11.151-8.923 18.312-22.633 18.312-37.992 0-24.146-17.683-44.23-40.777-48.006v-27.054c0-4.418-3.582-8-8-8h-97.194c-9.083-8.368-19.835-14.909-31.683-19.11 11.953-9.288 19.666-23.786 19.666-40.061 0-3.043-.284-6.019-.801-8.916h187.808c4.418 0 8-3.582 8-8s-3.582-8-8-8h-43.428c.004-26.317.024-44.303.045-62.285.021-17.989.042-35.977.045-62.305h14.425c4.535 0 8.534-2.555 10.438-6.667s1.262-8.815-1.673-12.271l-48.147-56.708c-2.189-2.577-5.384-4.054-8.766-4.053-3.381 0-6.574 1.479-8.761 4.055l-48.145 56.704c-2.936 3.456-3.577 8.158-1.674 12.271 1.902 4.113 5.902 6.668 10.438 6.668h14.425c.003 26.329.024 44.316.045 62.305.021 17.982.042 35.968.045 62.285h-17.917v-90.868c0-4.418-3.582-8-8-8h-51.26c-4.418 0-8 3.582-8 8v87.184c-4.588-6.695-10.737-12.239-17.921-16.102v-33.241c0-4.418-3.582-8-8-8h-51.261c-4.418 0-8 3.582-8 8v51.581c-.29.475-.563.961-.837 1.446h-16.569c-4.418 0-8 3.582-8 8s3.582 8 8 8h10.802c-.516 2.897-.801 5.873-.801 8.916 0 16.275 7.713 30.773 19.667 40.061-11.848 4.202-22.601 10.742-31.684 19.11h-97.321c-4.418 0-8 3.582-8 8v27.076c-23.033 3.828-40.652 23.881-40.652 47.983 0 15.359 7.162 29.069 18.313 37.992-30.88 11.228-53.873 39.146-57.555 73.56-.242 2.257.486 4.51 2.004 6.199 1.518 1.688 3.681 2.652 5.95 2.652h159.88c2.27 0 4.433-.964 5.95-2.653 1.518-1.688 2.246-3.941 2.004-6.199-3.683-34.413-26.676-62.331-57.554-73.559 11.151-8.923 18.313-22.633 18.313-37.993 0-24.102-17.62-44.155-40.652-47.983v-19.076h75.525c-8.282 12.187-13.761 26.504-15.431 42.107-.242 2.257.486 4.51 2.004 6.199 1.518 1.688 3.681 2.652 5.95 2.652h168.023c2.27 0 4.433-.964 5.95-2.652 1.518-1.688 2.246-3.942 2.004-6.199-1.669-15.602-7.148-29.919-15.431-42.106h75.399v19.099c-22.971 3.88-40.526 23.903-40.526 47.961 0 15.359 7.162 29.07 18.313 37.992-30.879 11.228-53.872 39.146-57.554 73.56-.242 2.257.486 4.51 2.004 6.198s3.681 2.653 5.95 2.653h159.879c2.27 0 4.433-.964 5.95-2.652 1.518-1.687 2.246-3.941 2.004-6.198zm-337.528-7.149h-140.973c7.55-32.339 36.426-55.752 70.487-55.752 34.06 0 62.936 23.413 70.486 55.752zm-37.833-104.403c0 18.004-14.647 32.652-32.652 32.652s-32.652-14.647-32.652-32.652 14.647-32.652 32.652-32.652 32.652 14.647 32.652 32.652zm139.054-55.445-11.647 13.151-11.647-13.151 11.469-36.06c.056 0 .112-.004.169-.004h.01.01c.056 0 .111.003.167.004zm131.349-174.006c-.023-19.749-.046-39.497-.046-70.287 0-4.418-3.582-8-8-8h-12.694l38.416-45.245 38.416 45.245h-12.694c-4.418 0-8 3.582-8 8 0 30.79-.022 50.538-.046 70.287-.02 17.988-.042 35.978-.045 62.304h-35.261c-.004-26.326-.025-44.316-.046-62.304zm-49.872-20.565v82.868h-35.26v-82.868zm-85.181 37.841v19.847c-2.589-.409-5.24-.626-7.942-.626-10.054 0-19.426 2.953-27.318 8.019v-27.239h35.26zm-42.666 69.944c0-19.146 15.577-34.723 34.724-34.723s34.723 15.577 34.723 34.723c0 19.143-15.571 34.717-34.712 34.723-.003 0-.007 0-.01 0s-.007 0-.01 0c-19.143-.006-34.715-15.58-34.715-34.723zm17.106 52.767-10.654 33.499c-.854 2.685-.232 5.62 1.635 7.729l14.29 16.135h-62.242c6.489-28.661 28.811-50.76 56.971-57.363zm29.964 57.362 14.29-16.134c1.867-2.109 2.488-5.044 1.635-7.729l-10.654-33.499c28.159 6.603 50.482 28.702 56.972 57.362zm115.061 32.102c0-18.004 14.647-32.652 32.652-32.652 18.004 0 32.651 14.648 32.651 32.652s-14.647 32.652-32.651 32.652c-18.004-.001-32.652-14.648-32.652-32.652zm-37.834 104.403c7.55-32.339 36.426-55.751 70.486-55.751s62.937 23.413 70.486 55.752zm-332.448-357.598 11.187 4.306c1.735 5.947 4.111 11.678 7.097 17.116l-4.869 10.961c-1.343 3.025-.686 6.564 1.654 8.904l17.326 17.326c2.341 2.34 5.878 2.998 8.904 1.655l10.967-4.871c5.438 2.985 11.166 5.359 17.11 7.094l4.308 11.19c1.188 3.088 4.156 5.126 7.466 5.126h24.502c3.31 0 6.277-2.038 7.466-5.126l4.306-11.187c5.947-1.735 11.678-4.11 17.116-7.096l10.962 4.869c3.023 1.343 6.563.686 8.904-1.654l17.326-17.327c2.34-2.34 2.997-5.879 1.654-8.904l-4.87-10.966c2.983-5.437 5.358-11.166 7.093-17.11l11.19-4.307c3.089-1.188 5.127-4.156 5.127-7.466v-24.501c0-3.31-2.038-6.277-5.126-7.466l-11.187-4.306c-1.735-5.948-4.111-11.678-7.097-17.116l4.869-10.962c1.343-3.024.686-6.564-1.655-8.904l-17.326-17.326c-2.339-2.34-5.878-2.999-8.903-1.654l-10.967 4.87c-5.438-2.985-11.166-5.359-17.11-7.094l-4.307-11.19c-1.188-3.088-4.156-5.126-7.466-5.126h-24.502c-3.31 0-6.277 2.038-7.466 5.126l-4.309 11.19c-5.943 1.735-11.672 4.11-17.109 7.094l-10.967-4.87c-3.026-1.345-6.564-.685-8.904 1.654l-17.326 17.326c-2.34 2.34-2.997 5.879-1.654 8.904l4.87 10.965c-2.985 5.438-5.36 11.167-7.095 17.112l-11.189 4.307c-3.088 1.189-5.126 4.156-5.126 7.466v24.502c0 3.31 2.038 6.278 5.126 7.466zm10.874-26.475 9.875-3.801c2.462-.947 4.298-3.048 4.909-5.614 1.704-7.166 4.533-13.989 8.407-20.28 1.384-2.247 1.57-5.031.5-7.442l-4.299-9.68 9.558-9.558 9.681 4.3c2.409 1.07 5.194.884 7.441-.5 6.292-3.874 13.115-6.703 20.28-8.408 2.565-.611 4.666-2.447 5.613-4.909l3.802-9.875h13.517l3.801 9.875c.947 2.462 3.048 4.298 5.613 4.909 7.166 1.705 13.989 4.534 20.281 8.408 2.247 1.384 5.032 1.57 7.441.499l9.681-4.299 9.558 9.558-4.298 9.676c-1.071 2.411-.884 5.196.5 7.442 3.874 6.29 6.703 13.115 8.41 20.285.61 2.566 2.446 4.667 4.908 5.614l9.872 3.8v13.517l-9.875 3.801c-2.462.948-4.299 3.048-4.909 5.614-1.706 7.166-4.534 13.99-8.408 20.281-1.383 2.247-1.569 5.03-.499 7.441l4.299 9.68-9.558 9.559-9.676-4.297c-2.409-1.071-5.194-.885-7.442.499-6.291 3.875-13.116 6.704-20.285 8.41-2.566.611-4.667 2.447-5.614 4.909l-3.8 9.872h-13.515l-3.802-9.875c-.947-2.461-3.048-4.298-5.613-4.909-7.165-1.705-13.989-4.534-20.281-8.408-2.249-1.384-5.032-1.568-7.441-.499l-9.681 4.299-9.558-9.558 4.298-9.676c1.07-2.412.884-5.196-.5-7.443-3.874-6.291-6.704-13.115-8.41-20.285-.61-2.566-2.446-4.667-4.908-5.614l-9.872-3.8v-13.518zm82.525 57.489c27.974 0 50.732-22.758 50.732-50.731 0-27.974-22.759-50.732-50.732-50.732s-50.731 22.758-50.731 50.732 22.758 50.731 50.731 50.731zm0-85.462c19.151 0 34.732 15.581 34.732 34.732s-15.581 34.731-34.732 34.731-34.731-15.58-34.731-34.731c0-19.152 15.58-34.732 34.731-34.732z"></path>
                    </svg>
                """
            },
        ]

        for index, profil in enumerate(profils):
            try:
                svg_icon = profil.get('svg_icon', "")
                profil_roles = profil.get('profil_system_roles', [])

                profil_data = {
                    field_name: field_value
                    for field_name, field_value in profil.items()
                    if field_name not in {'profil_system_roles', 'svg_icon'}
                }
                result = await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.RBAC_PROFILE,
                    filter_data={"flag": profil_data['flag']},
                    update_data=profil_data
                )
                print(f"\n saved profil [index]:{index} {result} \n")
                print(
                    f"\n saved profil > [index]:{index} profil_roles : {len(profil_roles)} \n")
                # save sycamoer icon
                processed_profil_id = result if isinstance(
                    result, str) else result['id']
                print(
                    f"\n saved profil > [index]:{index} processed_profil_id : {processed_profil_id} \n")
                # LOOP TO UPSERT ROLES

                for index, role in enumerate(profil_roles):
                    print(
                        f"\n saved profil roles > [index]:{index} role element : {role} \n")
                    new_role_data = {
                        # "name": f"{role['name']}",
                        # "is_default": role['is_default'],
                        # "system_reserved_actions": role['system_reserved_actions'],
                        **role,
                        "rbac_profile_id": processed_profil_id,
                        # "flag": role['flag'],
                        # "description_str": "Rôle d'un super utilisateur par défaut du profil "+profil_data['name'],
                        # "description_html": "<p>Rôle d'un super utilisateur par défaut du profil "+profil_data['name']+"</p>"
                    }
                    saved_role = await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.RBAC_ROLE,
                        filter_data={
                            "flag": new_role_data['flag'], 'rbac_profile_id': new_role_data['rbac_profile_id']},
                        update_data=new_role_data
                    )
                    saved_role_id = saved_role if isinstance(
                        saved_role, str) else saved_role['id']
                    print(
                        f"\n saved profil >> [index]:{index} saved_role_id : {saved_role_id} | role : {role} \n")
                    # ADD ALL DEFAULT PERMISSIONS
                    await rbac_role_service.create_single_rbac_default_role_permissions(
                        rbac_role_id=saved_role_id,
                        body_profil_id=processed_profil_id
                    )

                # PROFIL ICON
                profil_flag = profil_data.get("flag", "")
                profil_icon_data = {
                    "is_default": False,
                    "flag": EIconFlag.STANDARD_SVG.value,
                    "icon": svg_icon,
                    "name": f"icône du client {profil_flag.lower()}"
                }
                profil_icon_data = {
                    **profil_icon_data,
                    "hard_code_flag": generate_label_to_flag(f"icon_profil_{profil_flag}")
                }
                saved_icon = await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.REF_ICON,
                    filter_data={
                        "hard_code_flag": profil_icon_data['hard_code_flag']
                    },
                    update_data=profil_icon_data
                )
                saved_icon_id = saved_icon if isinstance(
                    saved_icon, str) else saved_icon['id']
                icon_relation = {
                    "targeted_id": processed_profil_id,
                    "ref_icon_id": saved_icon_id,
                    "restricted_api_consumer_list": [
                        EApiConsumerFlag.SENAT_DIGIT_ADMIN_WEB.value,
                    ],
                }
                result_icon_relation = await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_ICON_API_CONSUMER,
                    filter_data={
                        "targeted_id": icon_relation['targeted_id'], 'ref_icon_id': icon_relation['ref_icon_id']},
                    update_data=icon_relation
                )
                processed_icon_relation_id = result_icon_relation if isinstance(
                    result_icon_relation, str) else str(result_icon_relation['id'])
                icon_restricted_platform = icon_relation.get(
                    'restricted_api_consumer_list', [])

                for api_consumer_flag in icon_restricted_platform:
                    api_consumer_info = await generic_service.fetch_one_from_collection(
                        collection_key=CollectionKey.REF_API_CONSUMER,
                        output_data_type=OutputDataType.DEFAULT,
                        query={
                            "filter__flag": api_consumer_flag
                        }
                    )
                    if api_consumer_info:
                        await rbac_role_service.create_restricted_api_consumer(targeted_id=processed_icon_relation_id, ref_api_consumer_id=api_consumer_info['id'])

                # print("upserted result.",result)
            except ValueError as e:
                print(f"Error: {e}")
            except PermissionError as e:
                print(f"Permission Error: {e}")

        # print("Default profiles created or updated.")
        print(f"\n in profil after profil \n")
        # START DEFAULT APPLICATIONS
        res = await create_default_application()

    except ValueError as e:
        print(f"Error >> create profiles: {e}")
    except PermissionError as e:
        print(f"Permission Error: {e}")


async def create_attach_doc_natures(sys_organization_id=None):
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default attach doc nature records if they do not already exist.
    """
    list_of_attachment_doc_natures = [
        {
            "name": "Attestation médicale",
            "description_str": "Document délivré par un professionnel de santé attestant de l'état de santé d'une personne.",
            "flag": "medical_attestation",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Déclaration de créance",
            "description_str": "Document par lequel un créancier déclare une somme due par un débiteur.",
            "flag": "creditor_declaration",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Bordereau de dépôt",
            "description_str": "Document attestant du dépôt d'un dossier ou d'un montant auprès d'une institution.",
            "flag": "deposit_slip",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Bordereau de versement",
            "description_str": "Document justifiant le versement d'une somme d'argent à un bénéficiaire.",
            "flag": "payment_slip",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Décision",
            "description_str": "Document officiel émanant d'une autorité compétente pour acter une résolution ou une mesure.",
            "flag": "decision",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Demande de paiement",
            "description_str": "Document formulant une requête pour le règlement d'une somme due.",
            "flag": "payment_request",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Devis de travaux",
            "description_str": "Document détaillant le coût et les modalités des travaux à réaliser.",
            "flag": "work_quote",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "État de besoins",
            "description_str": "Document listant les besoins spécifiques pour un projet ou une activité.",
            "flag": "needs_statement",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Document",
            "description_str": "Pièce générique justificative ou informative.",
            "flag": "document",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "État de sommes à payer",
            "description_str": "Document récapitulant les montants dus à des créanciers.",
            "flag": "amounts_to_pay_statement",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Extrait bancaire",
            "description_str": "Document émis par une banque détaillant les transactions d'un compte.",
            "flag": "bank_statement",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Facture",
            "description_str": "Document commercial détaillant les biens ou services fournis et leur coût.",
            "flag": "invoice",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Facture proforma",
            "description_str": "Document préliminaire détaillant une offre de biens ou services avant émission de la facture définitive.",
            "flag": "proforma_invoice",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Grille de paie",
            "description_str": "Document détaillant les éléments de rémunération et les déductions pour un employé.",
            "flag": "payroll_grid",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Lettre",
            "description_str": "Document écrit formel ou informel utilisé pour communiquer des informations.",
            "flag": "letter",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Lettre de demande",
            "description_str": "Document écrit formulant une requête spécifique.",
            "flag": "request_letter",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Liste",
            "description_str": "Document énumérant des éléments ou des informations spécifiques.",
            "flag": "list",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Note",
            "description_str": "Document succinct contenant des informations ou des instructions.",
            "flag": "note",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Note explicative",
            "description_str": "Document fournissant des explications détaillées sur un sujet ou une décision.",
            "flag": "explanatory_note",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Note technique",
            "description_str": "Document détaillant les aspects techniques d'un projet ou d'une activité.",
            "flag": "technical_note",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Offre de service",
            "description_str": "Document proposant des services avec leurs conditions et tarifs.",
            "flag": "service_offer",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Ordonnance médicale",
            "description_str": "Document prescrivant des soins ou des médicaments délivré par un médecin.",
            "flag": "medical_prescription",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Ordre de mission",
            "description_str": "Document autorisant et détaillant les modalités d'une mission professionnelle.",
            "flag": "mission_order",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Ordre de paiement",
            "description_str": "Document autorisant le paiement d'une somme à un bénéficiaire.",
            "flag": "payment_order",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Paie",
            "description_str": "Document récapitulatif des salaires et charges sociales pour un employé.",
            "flag": "payroll",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Procès-verbal / Fin de contrat de bail",
            "description_str": "Document actant la fin d'un contrat de bail ou relatant les conclusions d'une réunion.",
            "flag": "contract_termination",
            "sys_organization_id": sys_organization_id,
        },
        {
            "name": "Reçu",
            "description_str": "Document attestant de la réception d'un paiement ou d'un bien.",
            "flag": "receipt",
            "sys_organization_id": sys_organization_id,
        },
    ]
    for data in list_of_attachment_doc_natures:
        try:
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.OPS_EXPENSE_ATTACH_DOC_TYPE,
                filter_data={
                    "flag": data['flag'], "sys_organization_id": sys_organization_id},
                update_data=data
            )
            DebugService.app_debug_print("\n\nupserted result.", result, True)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}", True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}", True)


async def create_default_notification_channels():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default notification channels if they do not already exist.
    """
    notification_channels = [
        {
            "name": "Email",
            "description_str": "Canal de notification par email.",
            "flag": ENotificationChannelFlag.EMAIL.value,
        },
        {
            "name": "SMS",
            "description_str": "Canal de notification par SMS.",
            "flag": ENotificationChannelFlag.SMS.value,
        },
        {
            "name": "Push notification",
            "description_str": "Canal de notification par push notification.",
            "flag": ENotificationChannelFlag.PUSH.value,
        }
    ]
    for data in notification_channels:
        try:
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_NOTIFICATION_CHANNEL,
                filter_data={"flag": data['flag']},
                update_data=data
            )
            DebugService.app_debug_print("\n\nupserted result.", result, True)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}", True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}", True)


async def create_default_notification_tunnels():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default notification tunnels if they do not already exist.
    """
    notification_tunnels = [
        {
            "name": "Inscription de compte utilisateur",
            "description_str": "Tunnel de notification pour l'inscription d'un compte utilisateur.",
            "flag": ENotificationTunnelFlag.USER_ACCOUNT_REGISTRATION.value,
        },
        {
            "name": "Réinitialisation du mot de passe",
            "description_str": "Tunnel de notification pour la réinitialisation du mot de passe du compte utilisateur.",
            "flag": ENotificationTunnelFlag.USER_ACCOUNT_PASSWORD_RESET.value,
        },
        {
            "name": "Echec d'une opération de paiement",
            "description_str": "Tunnel de notification pour l'échec d'une opération de paiement.",
            "flag": ENotificationTunnelFlag.PAYMENT_OPERATION_FAILED.value,
        },
        {
            "name": "Succès d'une opération de paiement",
            "description_str": "Tunnel de notification pour le succès d'une opération de paiement.",
            "flag": ENotificationTunnelFlag.PAYMENT_OPERATION_SUCCEEDED.value,
        },
        {
            "name": "Paiement en attente",
            "description_str": "Tunnel de notification pour un paiement en attente.",
            "flag": ENotificationTunnelFlag.PAYMENT_OPERATION_PENDING.value,
        },
        {
            "name": "Paiement approuvé",
            "description_str": "Tunnel de notification pour un paiement approuvé.",
            "flag": ENotificationTunnelFlag.PAYMENT_OPERATION_APPROVED.value,
        },
        {
            "name": "Inscription de compte entreprise",
            "description_str": "Tunnel de notification pour l'inscription d'un compte entreprise.",
            "flag": ENotificationTunnelFlag.BUSINESS_ACCOUNT_REGISTRATION.value,
        },
        {
            "name": "Requête de retrait de fonds",
            "description_str": "Tunnel de notification pour une requête de retrait de fonds.",
            "flag": ENotificationTunnelFlag.WALLET_WITHDRAWAL_REQUESTED.value,
        },
        {
            "name": "Retrait de fonds approuvé",
            "description_str": "Tunnel de notification pour un retrait de fonds approuvé.",
            "flag": ENotificationTunnelFlag.WALLET_WITHDRAWAL_APPROVED.value,
        },
        {
            "name": "Retrait de fonds rejeté",
            "description_str": "Tunnel de notification pour un retrait de fonds rejeté.",
            "flag": ENotificationTunnelFlag.WALLET_WITHDRAWAL_REJECTED.value,
        },
        {
            "name": "Rechargement de portefeuille réussi",
            "description_str": "Tunnel de notification pour un rechargement de portefeuille réussi.",
            "flag": ENotificationTunnelFlag.WALLET_RELOAD_SUCCEEDED.value,
        }
    ]
    for data in notification_tunnels:
        try:
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_NOTIFICATION_TUNNEL,
                filter_data={"flag": data['flag']},
                update_data=data
            )
            DebugService.app_debug_print("\n\nupserted result.", result, True)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}", True)
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}", True)


async def create_auth_question_response_category():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default API consumers if they do not already exist.
    """
    # Make sure to `await` find_one()
    auth_response_categories = [
        {
            "name": "Informations personnelles stables",
            "flag": "info_personnelles_stables",
            "children": [
                {"name": "Quel est votre mois de naissance ?",
                    "flag": "mois_naissance"},
                {"name": "Quel est votre lieu de naissance ?",
                    "flag": "lieu_naissance"},
                {"name": "Quel est le nom de votre meilleur ami d'enfance ?",
                    "flag": "ami_enfance"},
                {"name": "Quel est votre surnom d'enfance ?",
                    "flag": "surnom_enfance"},
                {"name": "Quel est le prénom de votre frère ou sœur aîné(e) ?", "flag": "prenom_aine"},
                {"name": "Quel est votre deuxième prénom ?",
                    "flag": "deuxieme_prenom"},
                {"name": "Quel est le nom de votre premier animal de compagnie ?",
                    "flag": "premier_animal"},
                {"name": "Quel est votre plat préféré ?", "flag": "plat_prefere"},
                {"name": "Quel est le nom de votre enseignant préféré à l'école ?",
                    "flag": "enseignant_prefere"},
                {"name": "Quel est le nom de l'hôpital où vous êtes né ?",
                    "flag": "hopital_naissance"},
            ]
        },
        {
            "name": "Expériences personnelles uniques",
            "flag": "experiences_personnelles",
            "children": [
                {"name": "Quel est le nom de votre premier employeur ?",
                    "flag": "premier_employeur"},
                {"name": "Quel est le pays que vous avez visité en premier ?",
                    "flag": "premier_voyage"},
                {"name": "Quel était votre métier rêvé durant l'enfance ?",
                    "flag": "metier_reve"},
                {"name": "Quel sport avez-vous pratiqué le plus longtemps ?",
                    "flag": "sport_pratique"},
                {"name": "Quel est le nom d'un premier collègue de travail dont vous vous souvenez ?",
                    "flag": "premier_collegue"},
                {"name": "Quel est le modèle de votre première voiture ?",
                    "flag": "premiere_voiture"},
                {"name": "Quel est le premier film que vous avez vu au cinéma ?",
                    "flag": "premier_film"},
                {"name": "Quel est le nom de votre professeur préféré du secondaire ?",
                    "flag": "prof_prefere"},
                {"name": "Dans quelle ville avez-vous vécu après avoir quitté la maison familiale ?",
                    "flag": "premiere_ville"},
                {"name": "Quel était votre jeu préféré durant l'enfance ?",
                    "flag": "jeu_prefere"},
            ]
        },
        {
            "name": "Préférences personnelles",
            "flag": "preferences_personnelles",
            "children": [
                {"name": "Quel est votre fruit préféré ?", "flag": "fruit_prefere"},
                {"name": "Quel est votre pays préféré ?", "flag": "pays_prefere"},
                {"name": "Quelle est votre couleur préférée ?",
                    "flag": "couleur_preferee"},
                {"name": "Quel est votre chanteur ou groupe préféré ?",
                    "flag": "musicien_prefere"},
                {"name": "Quel est votre film préféré ?", "flag": "film_prefere"},
                {"name": "Quel autre plat préférez-vous ?", "flag": "plat_prefere_2"},
                {"name": "Quel est votre sport préféré ?", "flag": "sport_prefere"},
                {"name": "Quelle est votre saison préférée ?",
                    "flag": "saison_preferee"},
                {"name": "Quel est votre hobby préféré ?", "flag": "hobby_prefere"},
                {"name": "Quel est votre type de musique préféré ?",
                    "flag": "musique_preferee"},
            ]
        }
    ]

    for index, info in enumerate(auth_response_categories):
        try:
            result = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_AUTH_QUESTION_CATEGORY, filter_data={"flag": info['flag']}, update_data=info)
            print(f"upserted result : {result}. index : {index}")
            result_category_id = result if isinstance(
                result, str) else str(result['id'])
            children = info.get('children', [])
            for child in children:
                child['ref_auth_question_category_id'] = result_category_id
                await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.REF_AUTH_QUESTION, filter_data={"flag": child['flag'], "ref_auth_question_category_id": child['ref_auth_question_category_id']}, update_data=child)

        except ValueError as e:
            print(f"Error ADDING AUTH QUESTION CATEGORY 1: {e}")
        except PermissionError as e:
            print(f"Error ADDING AUTH QUESTION CATEGORY 2 : {e}")


# Arborescence des TYPES d'entités (REF_NAMED_ENTITY)
NEW_NAMED_ENTITIES = [
    {
        "name": "continent",
        "named_entity_flag": "continent",
        "unique_flag": "named-continent",
        "children": [
            {
                "name": "pays",
                "named_entity_flag": "country",
                "unique_flag": "named-country",
                "children": [
                    {
                        "name": "province",
                        "named_entity_flag": "province",
                        "unique_flag": "named-province",
                        "children": [
                            {
                                "name": "ville",
                                "named_entity_flag": "town",
                                "unique_flag": "named-town",
                                "children": [
                                    {
                                        "name": "territoire",
                                        "named_entity_flag": "territory",
                                        "unique_flag": "named-territory",
                                        "children": [
                                            {
                                                "name": "secteur",
                                                "named_entity_flag": "sector",
                                                "unique_flag": "named-sector",
                                                "children": [
                                                    {
                                                        "name": "village",
                                                        "named_entity_flag": "village",
                                                        "unique_flag": "named-village",
                                                        "children": [],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                    {
                                        "name": "commune",
                                        "named_entity_flag": "township",
                                        "unique_flag": "named-township",
                                        "children": [
                                            {
                                                "name": "quartier",
                                                "named_entity_flag": "quarter",
                                                "unique_flag": "named-quarter",
                                                "children": [
                                                    {
                                                        "name": "avenue",
                                                        "named_entity_flag": "avenue",
                                                        "unique_flag": "named-avenue",
                                                        "children": [],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
]

DRC_LOCATION_TREE = [
    {
        "name": "afrique",
        "named_entity_flag": "continent",
        "unique_flag": "afrique-continent",
        "children": [
            {
                "name": "république démocratique du congo",
                "named_entity_flag": "country",
                "country_flag": "🇨🇩",
                "unique_flag": "rdc-country",
                "children": [
                    {
                        "name": "Kinshasa",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kinshasa",
                        "children": [
                            {
                                "name": "Kinshasa",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-town-kinshasa",
                                "children": [
                                    {
                                        "name": "gombe",
                                        "named_entity_flag": "township",
                                        "unique_flag": "rdc-township-gombe",
                                        "children": [
                                            {
                                                "name": "gare centrale",
                                                "named_entity_flag": "quarter",
                                                "unique_flag": "rdc-quarter-gare-centrale",
                                                "children": [],
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "name": "Kongo-Central",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kongo-central",
                        "children": [
                            {
                                "name": "Matadi",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-matadi",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Kwango",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kwango",
                        "children": [
                            {
                                "name": "Kenge",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kenge",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Kwilu",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kwilu",
                        "children": [
                            {
                                "name": "Bandundu",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-bandundu",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Mai-Ndombe",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-mai-ndombe",
                        "children": [
                            {
                                "name": "Inongo",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-inongo",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Kasaï",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kasai",
                        "children": [
                            {
                                "name": "Tshikapa",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-tshikapa",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Kasaï-Central",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kasai-central",
                        "children": [
                            {
                                "name": "Kananga",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kananga",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Kasaï-Oriental",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-kasai-oriental",
                        "children": [
                            {
                                "name": "Mbuji-Mayi",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-mbuji-mayi",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Lomami",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-lomami",
                        "children": [
                            {
                                "name": "Kabinda",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kabinda",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Sankuru",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-sankuru",
                        "children": [
                            {
                                "name": "Lusambo",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-lusambo",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Maniema",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-maniema",
                        "children": [
                            {
                                "name": "Kindu",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kindu",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Sud-Kivu",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-sud-kivu",
                        "children": [
                            {
                                "name": "Bukavu",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-bukavu",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Nord-Kivu",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-nord-kivu",
                        "children": [
                            {
                                "name": "Goma",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-goma",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Ituri",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-ituri",
                        "children": [
                            {
                                "name": "Bunia",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-bunia",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Haut-Uélé",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-haut-uele",
                        "children": [
                            {
                                "name": "Isiro",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-isiro",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Tshopo",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-tshopo",
                        "children": [
                            {
                                "name": "Kisangani",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kisangani",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Bas-Uélé",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-bas-uele",
                        "children": [
                            {
                                "name": "Buta",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-buta",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Nord-Ubangi",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-nord-ubangi",
                        "children": [
                            {
                                "name": "Gbadolite",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-gbadolite",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Mongala",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-mongala",
                        "children": [
                            {
                                "name": "Lisala",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-lisala",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Sud-Ubangi",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-sud-ubangi",
                        "children": [
                            {
                                "name": "Gemena",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-gemena",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Équateur",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-equateur",
                        "children": [
                            {
                                "name": "Mbandaka",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-mbandaka",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Tshuapa",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-tshuapa",
                        "children": [
                            {
                                "name": "Boende",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-boende",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Haut-Lomami",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-haut-lomami",
                        "children": [
                            {
                                "name": "Kamina",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kamina",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Lualaba",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-lualaba",
                        "children": [
                            {
                                "name": "Kolwezi",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kolwezi",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Haut-Katanga",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-haut-katanga",
                        "children": [
                            {
                                "name": "Lubumbashi",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-lubumbashi",
                                "children": [],
                            }
                        ],
                    },
                    {
                        "name": "Tanganyika",
                        "named_entity_flag": "province",
                        "unique_flag": "rdc-province-tanganyika",
                        "children": [
                            {
                                "name": "Kalemie",
                                "named_entity_flag": "town",
                                "unique_flag": "rdc-ville-kalemie",
                                "children": [],
                            }
                        ],
                    }
                ],
            },
        ]
    },
   
]


# DRC_LOCATION_TREE = [
#     {
#         "name": "afrique",
#         "named_entity_flag": "continent",
#         "unique_flag": "afrique-continent",
#         "children": [
#             {
#                 "name": "république démocratique du congo",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇨🇩",
#                 "unique_flag": "rdc-country",
#                 "children": [
#                     {
#                         "name": "Kinshasa",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kinshasa",
#                         "children": [
#                             {
#                                 "name": "Kinshasa",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-town-kinshasa",
#                                 "children": [
#                                     {
#                                         "name": "gombe",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "rdc-township-gombe",
#                                         "children": [
#                                             {
#                                                 "name": "gare centrale",
#                                                 "named_entity_flag": "quarter",
#                                                 "unique_flag": "rdc-quarter-gare-centrale",
#                                                 "children": [],
#                                             }
#                                         ],
#                                     }
#                                 ],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Kongo-Central",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kongo-central",
#                         "children": [
#                             {
#                                 "name": "Matadi",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-matadi",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Kwango",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kwango",
#                         "children": [
#                             {
#                                 "name": "Kenge",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kenge",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Kwilu",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kwilu",
#                         "children": [
#                             {
#                                 "name": "Bandundu",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-bandundu",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Mai-Ndombe",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-mai-ndombe",
#                         "children": [
#                             {
#                                 "name": "Inongo",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-inongo",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Kasaï",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kasai",
#                         "children": [
#                             {
#                                 "name": "Tshikapa",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-tshikapa",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Kasaï-Central",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kasai-central",
#                         "children": [
#                             {
#                                 "name": "Kananga",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kananga",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Kasaï-Oriental",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-kasai-oriental",
#                         "children": [
#                             {
#                                 "name": "Mbuji-Mayi",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-mbuji-mayi",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Lomami",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-lomami",
#                         "children": [
#                             {
#                                 "name": "Kabinda",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kabinda",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Sankuru",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-sankuru",
#                         "children": [
#                             {
#                                 "name": "Lusambo",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-lusambo",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Maniema",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-maniema",
#                         "children": [
#                             {
#                                 "name": "Kindu",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kindu",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Sud-Kivu",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-sud-kivu",
#                         "children": [
#                             {
#                                 "name": "Bukavu",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-bukavu",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Nord-Kivu",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-nord-kivu",
#                         "children": [
#                             {
#                                 "name": "Goma",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-goma",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Ituri",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-ituri",
#                         "children": [
#                             {
#                                 "name": "Bunia",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-bunia",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Haut-Uélé",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-haut-uele",
#                         "children": [
#                             {
#                                 "name": "Isiro",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-isiro",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Tshopo",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-tshopo",
#                         "children": [
#                             {
#                                 "name": "Kisangani",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kisangani",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Bas-Uélé",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-bas-uele",
#                         "children": [
#                             {
#                                 "name": "Buta",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-buta",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Nord-Ubangi",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-nord-ubangi",
#                         "children": [
#                             {
#                                 "name": "Gbadolite",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-gbadolite",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Mongala",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-mongala",
#                         "children": [
#                             {
#                                 "name": "Lisala",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-lisala",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Sud-Ubangi",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-sud-ubangi",
#                         "children": [
#                             {
#                                 "name": "Gemena",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-gemena",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Équateur",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-equateur",
#                         "children": [
#                             {
#                                 "name": "Mbandaka",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-mbandaka",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Tshuapa",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-tshuapa",
#                         "children": [
#                             {
#                                 "name": "Boende",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-boende",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Haut-Lomami",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-haut-lomami",
#                         "children": [
#                             {
#                                 "name": "Kamina",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kamina",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Lualaba",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-lualaba",
#                         "children": [
#                             {
#                                 "name": "Kolwezi",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kolwezi",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Haut-Katanga",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-haut-katanga",
#                         "children": [
#                             {
#                                 "name": "Lubumbashi",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-lubumbashi",
#                                 "children": [],
#                             }
#                         ],
#                     },
#                     {
#                         "name": "Tanganyika",
#                         "named_entity_flag": "province",
#                         "unique_flag": "rdc-province-tanganyika",
#                         "children": [
#                             {
#                                 "name": "Kalemie",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "rdc-ville-kalemie",
#                                 "children": [],
#                             }
#                         ],
#                     }
#                 ],
#             },
#             {
#                 "name": "République du Congo",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇨🇬",
#                 "unique_flag": "congo-brazza-country",
#                 "children": [
#                     {
#                         "name": "Brazzaville",
#                         "named_entity_flag": "province",  # department
#                         "unique_flag": "congo-brazza-department-brazzaville",
#                         "children": [
#                             {
#                                 "name": "Brazzaville",
#                                 "named_entity_flag": "town",  # city
#                                 "unique_flag": "congo-brazza-city-brazzaville",
#                                 "children": [
#                                     {
#                                         "name": "Poto-Poto",
#                                         "named_entity_flag": "township",  # arrondissement
#                                         "unique_flag": "congo-brazza-arrondissement-poto-poto",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "République du Cameroun",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇨🇲",
#                 "unique_flag": "cameroon-country",
#                 "children": [
#                     {
#                         "name": "Centre",
#                         "named_entity_flag": "province",  # region
#                         "unique_flag": "cameroon-region-centre",
#                         "children": [
#                             {
#                                 "name": "Yaoundé",
#                                 "named_entity_flag": "town",  # city
#                                 "unique_flag": "cameroon-city-yaounde",
#                                 "children": [
#                                     {
#                                         "name": "Yaoundé I",
#                                         "named_entity_flag": "township",  # arrondissement
#                                         "unique_flag": "cameroon-arrondissement-yaounde-1",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Littoral",
#                         "named_entity_flag": "province",  # region
#                         "unique_flag": "cameroon-region-littoral",
#                         "children": [
#                             {
#                                 "name": "Douala",
#                                 "named_entity_flag": "town",  # city
#                                 "unique_flag": "cameroon-city-douala",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Nigeria",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇳🇬",
#                 "unique_flag": "nigeria-country",
#                 "children": [
#                     {
#                         "name": "Lagos",
#                         "named_entity_flag": "province",
#                         "unique_flag": "nigeria-state-lagos",
#                         "children": [
#                             {
#                                 "name": "Lagos City",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "nigeria-city-lagos",
#                                 "children": [
#                                     {
#                                         "name": "Lagos Island",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "nigeria-lga-lagos-island",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Federal Capital Territory",
#                         "named_entity_flag": "province",
#                         "unique_flag": "nigeria-fct-abuja",
#                         "children": [
#                             {
#                                 "name": "Abuja",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "nigeria-city-abuja",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Afrique du Sud",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇿🇦",
#                 "unique_flag": "south-africa-country",
#                 "children": [
#                     {
#                         "name": "Gauteng",
#                         "named_entity_flag": "province",
#                         "unique_flag": "south-africa-province-gauteng",
#                         "children": [
#                             {
#                                 "name": "Johannesburg",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "south-africa-city-johannesburg",
#                                 "children": [
#                                     {
#                                         "name": "Sandton",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "south-africa-suburb-sandton",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Égypte",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇪🇬",
#                 "unique_flag": "egypt-country",
#                 "children": [
#                     {
#                         "name": "Le Caire",
#                         "named_entity_flag": "province",
#                         "unique_flag": "egypt-governorate-cairo",
#                         "children": [
#                             {
#                                 "name": "Le Caire",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "egypt-city-cairo",
#                                 "children": [
#                                     {
#                                         "name": "Gizeh",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "egypt-district-giza",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             # West African CFA (XOF) countries
#             {
#                 "name": "Bénin",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇧🇯",
#                 "unique_flag": "benin-country",
#                 "children": [
#                     {
#                         "name": "Littoral",
#                         "named_entity_flag": "province",
#                         "unique_flag": "benin-department-littoral",
#                         "children": [
#                             {
#                                 "name": "Cotonou",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "benin-city-cotonou",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Burkina Faso",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇧🇫",
#                 "unique_flag": "burkina-faso-country",
#                 "children": [
#                     {
#                         "name": "Centre",
#                         "named_entity_flag": "province",
#                         "unique_flag": "burkina-region-centre",
#                         "children": [
#                             {
#                                 "name": "Ouagadougou",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "burkina-city-ouagadougou",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Côte d'Ivoire",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇨🇮",
#                 "unique_flag": "ivory-coast-country",
#                 "children": [
#                     {
#                         "name": "Abidjan",
#                         "named_entity_flag": "province",
#                         "unique_flag": "ivory-coast-district-abidjan",
#                         "children": [
#                             {
#                                 "name": "Abidjan",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "ivory-coast-city-abidjan",
#                                 "children": [
#                                     {
#                                         "name": "Plateau",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "ivory-coast-commune-plateau",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Guinée-Bissau",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇬🇼",
#                 "unique_flag": "guinea-bissau-country",
#                 "children": [
#                     {
#                         "name": "Bissau",
#                         "named_entity_flag": "province",
#                         "unique_flag": "guinea-bissau-sector-bissau",
#                         "children": [
#                             {
#                                 "name": "Bissau",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "guinea-bissau-city-bissau",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Mali",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇲🇱",
#                 "unique_flag": "mali-country",
#                 "children": [
#                     {
#                         "name": "Bamako",
#                         "named_entity_flag": "province",
#                         "unique_flag": "mali-district-bamako",
#                         "children": [
#                             {
#                                 "name": "Bamako",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "mali-city-bamako",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Niger",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇳🇪",
#                 "unique_flag": "niger-country",
#                 "children": [
#                     {
#                         "name": "Niamey",
#                         "named_entity_flag": "province",
#                         "unique_flag": "niger-region-niamey",
#                         "children": [
#                             {
#                                 "name": "Niamey",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "niger-city-niamey",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Sénégal",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇸🇳",
#                 "unique_flag": "senegal-country",
#                 "children": [
#                     {
#                         "name": "Dakar",
#                         "named_entity_flag": "province",
#                         "unique_flag": "senegal-region-dakar",
#                         "children": [
#                             {
#                                 "name": "Dakar",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "senegal-city-dakar",
#                                 "children": [
#                                     {
#                                         "name": "Plateau",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "senegal-commune-plateau",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Togo",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇹🇬",
#                 "unique_flag": "togo-country",
#                 "children": [
#                     {
#                         "name": "Maritime",
#                         "named_entity_flag": "province",
#                         "unique_flag": "togo-region-maritime",
#                         "children": [
#                             {
#                                 "name": "Lomé",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "togo-city-lome",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             # Central African CFA (XAF) countries
#             {
#                 "name": "République Centrafricaine",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇨🇫",
#                 "unique_flag": "central-african-republic-country",
#                 "children": [
#                     {
#                         "name": "Bangui",
#                         "named_entity_flag": "province",
#                         "unique_flag": "car-prefecture-bangui",
#                         "children": [
#                             {
#                                 "name": "Bangui",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "car-city-bangui",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Tchad",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇹🇩",
#                 "unique_flag": "chad-country",
#                 "children": [
#                     {
#                         "name": "N'Djamena",
#                         "named_entity_flag": "province",
#                         "unique_flag": "chad-region-ndjamena",
#                         "children": [
#                             {
#                                 "name": "N'Djamena",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "chad-city-ndjamena",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Guinée Équatoriale",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇬🇶",
#                 "unique_flag": "equatorial-guinea-country",
#                 "children": [
#                     {
#                         "name": "Litoral",
#                         "named_entity_flag": "province",
#                         "unique_flag": "eq-guinea-province-litoral",
#                         "children": [
#                             {
#                                 "name": "Malabo",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "eq-guinea-city-malabo",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Gabon",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇬🇦",
#                 "unique_flag": "gabon-country",
#                 "children": [
#                     {
#                         "name": "Estuaire",
#                         "named_entity_flag": "province",
#                         "unique_flag": "gabon-province-estuaire",
#                         "children": [
#                             {
#                                 "name": "Libreville",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "gabon-city-libreville",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             }
#         ]
#     },
#     {
#         "name": "europe",
#         "named_entity_flag": "continent",
#         "unique_flag": "europe-continent",
#         "children": [
#             {
#                 "name": "France",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇫🇷",
#                 "unique_flag": "france-country",
#                 "children": [
#                     {
#                         "name": "Île-de-France",
#                         "named_entity_flag": "province",
#                         "unique_flag": "france-region-ile-de-france",
#                         "children": [
#                             {
#                                 "name": "Paris",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "france-city-paris",
#                                 "children": [
#                                     {
#                                         "name": "1er arrondissement",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "france-arrondissement-paris-1",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Provence-Alpes-Côte d'Azur",
#                         "named_entity_flag": "province",
#                         "unique_flag": "france-region-paca",
#                         "children": [
#                             {
#                                 "name": "Marseille",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "france-city-marseille",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Belgique",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇧🇪",
#                 "unique_flag": "belgium-country",
#                 "children": [
#                     {
#                         "name": "Bruxelles-Capitale",
#                         "named_entity_flag": "province",
#                         "unique_flag": "belgium-region-bruxelles",
#                         "children": [
#                             {
#                                 "name": "Bruxelles",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "belgium-city-bruxelles",
#                                 "children": [
#                                     {
#                                         "name": "Ixelles",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "belgium-commune-ixelles",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Allemagne",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇩🇪",
#                 "unique_flag": "germany-country",
#                 "children": [
#                     {
#                         "name": "Berlin",
#                         "named_entity_flag": "province",
#                         "unique_flag": "germany-state-berlin",
#                         "children": [
#                             {
#                                 "name": "Berlin",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "germany-city-berlin",
#                                 "children": [
#                                     {
#                                         "name": "Mitte",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "germany-bezirk-mitte",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Bayern",
#                         "named_entity_flag": "province",
#                         "unique_flag": "germany-state-bayern",
#                         "children": [
#                             {
#                                 "name": "Munich",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "germany-city-munich",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Royaume-Uni",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇬🇧",
#                 "unique_flag": "uk-country",
#                 "children": [
#                     {
#                         "name": "Angleterre",
#                         "named_entity_flag": "province",
#                         "unique_flag": "uk-country-england",
#                         "children": [
#                             {
#                                 "name": "Londres",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "uk-city-london",
#                                 "children": [
#                                     {
#                                         "name": "Westminster",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "uk-borough-westminster",
#                                         "children": []
#                                     }
#                                 ]
#                             },
#                             {
#                                 "name": "Manchester",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "uk-city-manchester",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Italie",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇮🇹",
#                 "unique_flag": "italy-country",
#                 "children": [
#                     {
#                         "name": "Latium",
#                         "named_entity_flag": "province",
#                         "unique_flag": "italy-region-lazio",
#                         "children": [
#                             {
#                                 "name": "Rome",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "italy-city-rome",
#                                 "children": [
#                                     {
#                                         "name": "Rome Centre",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "italy-municipio-rome-centre",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Espagne",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇪🇸",
#                 "unique_flag": "spain-country",
#                 "children": [
#                     {
#                         "name": "Communauté de Madrid",
#                         "named_entity_flag": "province",
#                         "unique_flag": "spain-community-madrid",
#                         "children": [
#                             {
#                                 "name": "Madrid",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "spain-city-madrid",
#                                 "children": [
#                                     {
#                                         "name": "Centre",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "spain-district-centro",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             }
#         ]
#     },
#     {
#         "name": "amérique",
#         "named_entity_flag": "continent",
#         "unique_flag": "amerique-continent",
#         "children": [
#             {
#                 "name": "États-Unis",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇺🇸",
#                 "unique_flag": "usa-country",
#                 "children": [
#                     {
#                         "name": "New York",
#                         "named_entity_flag": "province",
#                         "unique_flag": "usa-state-new-york",
#                         "children": [
#                             {
#                                 "name": "New York City",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "usa-city-new-york",
#                                 "children": [
#                                     {
#                                         "name": "Manhattan",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "usa-borough-manhattan",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Canada",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇨🇦",
#                 "unique_flag": "canada-country",
#                 "children": [
#                     {
#                         "name": "Ontario",
#                         "named_entity_flag": "province",
#                         "unique_flag": "canada-province-ontario",
#                         "children": [
#                             {
#                                 "name": "Toronto",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "canada-city-toronto",
#                                 "children": [
#                                     {
#                                         "name": "Downtown Toronto",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "canada-district-downtown-toronto",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Québec",
#                         "named_entity_flag": "province",
#                         "unique_flag": "canada-province-quebec",
#                         "children": [
#                             {
#                                 "name": "Montreal",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "canada-city-montreal",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Brésil",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇧🇷",
#                 "unique_flag": "brazil-country",
#                 "children": [
#                     {
#                         "name": "São Paulo",
#                         "named_entity_flag": "province",
#                         "unique_flag": "brazil-state-sao-paulo",
#                         "children": [
#                             {
#                                 "name": "São Paulo",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "brazil-city-sao-paulo",
#                                 "children": [
#                                     {
#                                         "name": "Centre",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "brazil-district-centro",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Rio de Janeiro",
#                         "named_entity_flag": "province",
#                         "unique_flag": "brazil-state-rio-de-janeiro",
#                         "children": [
#                             {
#                                 "name": "Rio de Janeiro",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "brazil-city-rio-de-janeiro",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Mexique",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇲🇽",
#                 "unique_flag": "mexico-country",
#                 "children": [
#                     {
#                         "name": "Mexico",
#                         "named_entity_flag": "province",
#                         "unique_flag": "mexico-state-mexico",
#                         "children": [
#                             {
#                                 "name": "Mexico City",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "mexico-city-mexico-city",
#                                 "children": [
#                                     {
#                                         "name": "Cuauhtémoc",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "mexico-borough-cuauhtemoc",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Jalisco",
#                         "named_entity_flag": "province",
#                         "unique_flag": "mexico-state-jalisco",
#                         "children": [
#                             {
#                                 "name": "Guadalajara",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "mexico-city-guadalajara",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             },
#             {
#                 "name": "Argentine",
#                 "named_entity_flag": "country",
#                 "country_flag": "🇦🇷",
#                 "unique_flag": "argentina-country",
#                 "children": [
#                     {
#                         "name": "Buenos Aires",
#                         "named_entity_flag": "province",
#                         "unique_flag": "argentina-province-buenos-aires",
#                         "children": [
#                             {
#                                 "name": "Buenos Aires",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "argentina-city-buenos-aires",
#                                 "children": [
#                                     {
#                                         "name": "Palermo",
#                                         "named_entity_flag": "township",
#                                         "unique_flag": "argentina-barrio-palermo",
#                                         "children": []
#                                     }
#                                 ]
#                             }
#                         ]
#                     },
#                     {
#                         "name": "Córdoba",
#                         "named_entity_flag": "province",
#                         "unique_flag": "argentina-province-cordoba",
#                         "children": [
#                             {
#                                 "name": "Córdoba",
#                                 "named_entity_flag": "town",
#                                 "unique_flag": "argentina-city-cordoba",
#                                 "children": []
#                             }
#                         ]
#                     }
#                 ]
#             }



#         ]
#     },
# ]


def normalize_unique_flag(flag: str) -> str:
    return (
        flag.strip()
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
    )


async def seed_named_entities():
    """
    Alimente REF_NAMED_ENTITY à partir de NEW_NAMED_ENTITIES
    en respectant l'arborescence (pays > province > ville > ...)
    et en utilisant unique_flag pour les upserts.
    """
    generic_service = GenericService(DEFAULT_LANGUAGE)

    async def process_named_entities(entities, parent_entity=None):
        for entity in entities:
            unique_flag = normalize_unique_flag(entity["unique_flag"])

            named_entity_data = {
                "name": entity["name"],
                "named_entity_flag": entity["named_entity_flag"],
                "unique_flag": unique_flag,
            }

            if parent_entity:
                named_entity_data["ref_named_entity_id"] = parent_entity["id"]

            saved_named_entity = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_NAMED_ENTITY,
                filter_data={"unique_flag": unique_flag},
                update_data=named_entity_data,
            )

            print(
                f"[NAMED_ENTITY] {unique_flag} → {saved_named_entity['name']}")

            if entity.get("children"):
                await process_named_entities(entity["children"], saved_named_entity)

    await process_named_entities(NEW_NAMED_ENTITIES)


# IANA time zone per RDC unique_flag.
# Western provinces use Africa/Kinshasa (WAT, UTC+1);
# eastern provinces use Africa/Lubumbashi (CAT, UTC+2).
# Unlisted descendants inherit their parent's zone at seed time.
DRC_TIMEZONE_BY_UNIQUE_FLAG = {
    "rdc-country": "Africa/Kinshasa",
    # WAT — Africa/Kinshasa
    "rdc-province-kinshasa": "Africa/Kinshasa",
    "rdc-province-kongo-central": "Africa/Kinshasa",
    "rdc-province-kwango": "Africa/Kinshasa",
    "rdc-province-kwilu": "Africa/Kinshasa",
    "rdc-province-mai-ndombe": "Africa/Kinshasa",
    "rdc-province-kasai": "Africa/Kinshasa",
    "rdc-province-kasai-central": "Africa/Kinshasa",
    "rdc-province-equateur": "Africa/Kinshasa",
    "rdc-province-tshuapa": "Africa/Kinshasa",
    "rdc-province-mongala": "Africa/Kinshasa",
    "rdc-province-nord-ubangi": "Africa/Kinshasa",
    "rdc-province-sud-ubangi": "Africa/Kinshasa",
    # CAT — Africa/Lubumbashi
    "rdc-province-kasai-oriental": "Africa/Lubumbashi",
    "rdc-province-lomami": "Africa/Lubumbashi",
    "rdc-province-sankuru": "Africa/Lubumbashi",
    "rdc-province-maniema": "Africa/Lubumbashi",
    "rdc-province-sud-kivu": "Africa/Lubumbashi",
    "rdc-province-nord-kivu": "Africa/Lubumbashi",
    "rdc-province-ituri": "Africa/Lubumbashi",
    "rdc-province-haut-uele": "Africa/Lubumbashi",
    "rdc-province-bas-uele": "Africa/Lubumbashi",
    "rdc-province-tshopo": "Africa/Lubumbashi",
    "rdc-province-haut-lomami": "Africa/Lubumbashi",
    "rdc-province-lualaba": "Africa/Lubumbashi",
    "rdc-province-haut-katanga": "Africa/Lubumbashi",
    "rdc-province-tanganyika": "Africa/Lubumbashi",
}


async def seed_drc_geo_hierarchy():
    """
    Alimente REF_ENTITY pour la RDC (pays > provinces > villes > ...),
    en lien avec REF_NAMED_ENTITY via named_entity_flag,
    et en utilisant unique_flag (lowercase) pour l'upsert.
    """
    generic_service = GenericService(DEFAULT_LANGUAGE)

    async def get_named_entity_by_flag(flag: str):
        # On part du principe que seed_named_entities() a déjà tourné.
        # On cherche l'entité nommée existante, et si elle n'existe pas, on lève une erreur.
        existing = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_NAMED_ENTITY,
            query={"filter__named_entity_flag": flag},
        )
        if not existing:
            return None
            # raise ValueError(f"Named entity with flag '{flag}' not found. Run seed_named_entities() first.")
        return existing

    async def process_nodes(nodes, parent_ref_entity=None, parent_time_zone=None):
        for node in nodes:
            flag = node["named_entity_flag"]
            unique_flag = normalize_unique_flag(node["unique_flag"])
            name = node["name"]

            # Récupérer le type d'entité nommée (pays, province, ville, ...)
            named_entity = await get_named_entity_by_flag(flag)

            time_zone = DRC_TIMEZONE_BY_UNIQUE_FLAG.get(unique_flag, parent_time_zone)

            ref_entity_data = {
                "name": name,
                "unique_flag": unique_flag,
                "country_flag": node.get("country_flag"),
                "time_zone": time_zone,
                "ref_named_entity_id": named_entity["id"] if named_entity else None,
            }

            if parent_ref_entity:
                ref_entity_data["ref_entity_id"] = parent_ref_entity["id"]

            ref_entity = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_ENTITY,
                filter_data={"unique_flag": unique_flag},
                update_data=ref_entity_data,
            )

            print(f"[REF_ENTITY] {unique_flag} → {ref_entity['name']} (tz={time_zone})")

            # Hook métier pour créer une organisation au niveau province
            if node["unique_flag"] == "rdc-town-kinshasa":
                try:
                    await create_organization(ref_entity["id"])
                except Exception:
                    # tu peux logger si besoin
                    pass

            if node.get("children"):
                await process_nodes(node["children"], ref_entity, time_zone)

    await process_nodes(DRC_LOCATION_TREE)


async def initialize_geo_reference_data():
    # 1. Création / mise à jour de la hiérarchie des entités nommées
    await seed_named_entities()

    # 2. Création / mise à jour de l'arborescence concrète RDC
    await seed_drc_geo_hierarchy()

 

async def create_currencies():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    """
    Create default currencies records if they do not already exist.
    """
    currencies = [
        {
            "name": "franc congolais",
            "code": "cdf",
            "symbol": "FC",
            "number": 976,
        },
        {
            "name": "dollar américain",
            "code": "usd",
            "symbol": "$",
            "number": 840
        }, 
    ]
    for currency in currencies:
        try:
            result = await generic_service.upsert_data_to_collection(collection_key=CollectionKey.REF_CURRENCY, filter_data={"code": currency['code']}, update_data=currency)
            # DebugService.app_debug_print("upserted result.",result)
        except ValueError as e:
            DebugService.app_debug_print(f"Error: {e}")
        except PermissionError as e:
            DebugService.app_debug_print(f"Permission Error: {e}")

    # DebugService.app_debug_print("Default langs created or updated.")


# Extend the CITIES_DEFAULT_CURRENCIES list with towns from DRC_LOCATION_TREE
CITIES_DEFAULT_CURRENCIES = [
    {
        "country_unique_flag": "rdc-country",
        "currency": "cdf",
        "towns": [
            {
                "unique_flag": "rdc-town-kinshasa",
            },
            {
                "unique_flag": "rdc-ville-matadi",
            },
            {
                "unique_flag": "rdc-ville-kenge",
            },
            {
                "unique_flag": "rdc-ville-bandundu",
            },
            {
                "unique_flag": "rdc-ville-inongo",
            },
            {
                "unique_flag": "rdc-ville-tshikapa",
            },
            {
                "unique_flag": "rdc-ville-kananga",
            },
            {
                "unique_flag": "rdc-ville-mbuji-mayi",
            },
            {
                "unique_flag": "rdc-ville-kabinda",
            },
            {
                "unique_flag": "rdc-ville-lusambo",
            },
            {
                "unique_flag": "rdc-ville-kindu",
            },
            {
                "unique_flag": "rdc-ville-bukavu",
            },
            {
                "unique_flag": "rdc-ville-goma",
            },
            {
                "unique_flag": "rdc-ville-bunia",
            },
            {
                "unique_flag": "rdc-ville-isiro",
            },
            {
                "unique_flag": "rdc-ville-kisangani",
            },
            {
                "unique_flag": "rdc-ville-buta",
            },
            {
                "unique_flag": "rdc-ville-gbadolite",
            },
            {
                "unique_flag": "rdc-ville-lisala",
            },
            {
                "unique_flag": "rdc-ville-gemena",
            },
            {
                "unique_flag": "rdc-ville-mbandaka",
            },
            {
                "unique_flag": "rdc-ville-boende",
            },
            {
                "unique_flag": "rdc-ville-kamina",
            },
            {
                "unique_flag": "rdc-ville-kolwezi",
            },
            {
                "unique_flag": "rdc-ville-lubumbashi",
            },
            {
                "unique_flag": "rdc-ville-kalemie",
            },
        ]
    },
    # Congo-Brazzaville
    # {
    #     "country_unique_flag": "congo-brazza-country",
    #     "currency": "xaf",
    #     "towns": [
    #         {"unique_flag": "congo-brazza-city-brazzaville"},
    #     ]
    # },
    # # Cameroon
    # {
    #     "country_unique_flag": "cameroon-country",
    #     "currency": "xaf",
    #     "towns": [
    #         {"unique_flag": "cameroon-city-yaounde"},
    #         {"unique_flag": "cameroon-city-douala"},
    #     ]
    # },
    # # Brazil
    # {
    #     "country_unique_flag": "brazil-country",
    #     "currency": "brl",
    #     "towns": [
    #         {"unique_flag": "brazil-city-sao-paulo"},
    #         {"unique_flag": "brazil-city-rio-de-janeiro"},
    #     ]
    # },
    # # Mexico
    # {
    #     "country_unique_flag": "mexico-country",
    #     "currency": "mxn",
    #     "towns": [
    #         {"unique_flag": "mexico-city-mexico-city"},
    #         {"unique_flag": "mexico-city-guadalajara"},
    #     ]
    # },
    # # Argentina
    # {
    #     "country_unique_flag": "argentina-country",
    #     "currency": "ars",
    #     "towns": [
    #         {"unique_flag": "argentina-city-buenos-aires"},
    #         {"unique_flag": "argentina-city-cordoba"},
    #     ]
    # },
    # # France
    # {
    #     "country_unique_flag": "france-country",
    #     "currency": "eur",
    #     "towns": [
    #         {"unique_flag": "france-city-paris"},
    #         {"unique_flag": "france-city-marseille"},
    #     ]
    # },
    # # Canada
    # {
    #     "country_unique_flag": "canada-country",
    #     "currency": "cad",
    #     "towns": [
    #         {"unique_flag": "canada-city-toronto"},
    #         {"unique_flag": "canada-city-montreal"},
    #     ]
    # },
    # # UK
    # {
    #     "country_unique_flag": "uk-country",
    #     "currency": "gbp",
    #     "towns": [
    #         {"unique_flag": "uk-city-london"},
    #         {"unique_flag": "uk-city-manchester"},
    #     ]
    # },
    # # Germany
    # {
    #     "country_unique_flag": "germany-country",
    #     "currency": "eur",
    #     "towns": [
    #         {"unique_flag": "germany-city-berlin"},
    #         {"unique_flag": "germany-city-munich"},
    #     ]
    # },
    # # Nigeria
    # {
    #     "country_unique_flag": "nigeria-country",
    #     "currency": "ngn",
    #     "towns": [
    #         {"unique_flag": "nigeria-city-lagos"},
    #         {"unique_flag": "nigeria-city-abuja"},
    #     ]
    # },
    # # Belgium
    # {
    #     "country_unique_flag": "belgium-country",
    #     "currency": "eur",
    #     "towns": [
    #         {"unique_flag": "belgium-city-bruxelles"},
    #     ]
    # },
    # # South Africa
    # {
    #     "country_unique_flag": "south-africa-country",
    #     "currency": "zar",
    #     "towns": [
    #         {"unique_flag": "south-africa-city-johannesburg"},
    #     ]
    # },
    # # Egypt
    # {
    #     "country_unique_flag": "egypt-country",
    #     "currency": "egp",
    #     "towns": [
    #         {"unique_flag": "egypt-city-cairo"},
    #     ]
    # },
    # # Benin (XOF - West African CFA)
    # {
    #     "country_unique_flag": "benin-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "benin-city-cotonou"},
    #     ]
    # },
    # # Burkina Faso (XOF)
    # {
    #     "country_unique_flag": "burkina-faso-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "burkina-city-ouagadougou"},
    #     ]
    # },
    # # Côte d'Ivoire (XOF)
    # {
    #     "country_unique_flag": "ivory-coast-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "ivory-coast-city-abidjan"},
    #     ]
    # },
    # # Guinea-Bissau (XOF)
    # {
    #     "country_unique_flag": "guinea-bissau-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "guinea-bissau-city-bissau"},
    #     ]
    # },
    # # Mali (XOF)
    # {
    #     "country_unique_flag": "mali-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "mali-city-bamako"},
    #     ]
    # },
    # # Niger (XOF)
    # {
    #     "country_unique_flag": "niger-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "niger-city-niamey"},
    #     ]
    # },
    # # Senegal (XOF)
    # {
    #     "country_unique_flag": "senegal-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "senegal-city-dakar"},
    #     ]
    # },
    # # Togo (XOF)
    # {
    #     "country_unique_flag": "togo-country",
    #     "currency": "xof",
    #     "towns": [
    #         {"unique_flag": "togo-city-lome"},
    #     ]
    # },
    # # Central African Republic (XAF)
    # {
    #     "country_unique_flag": "central-african-republic-country",
    #     "currency": "xaf",
    #     "towns": [
    #         {"unique_flag": "car-city-bangui"},
    #     ]
    # },
    # # Chad (XAF)
    # {
    #     "country_unique_flag": "chad-country",
    #     "currency": "xaf",
    #     "towns": [
    #         {"unique_flag": "chad-city-ndjamena"},
    #     ]
    # },
    # # Equatorial Guinea (XAF)
    # {
    #     "country_unique_flag": "equatorial-guinea-country",
    #     "currency": "xaf",
    #     "towns": [
    #         {"unique_flag": "eq-guinea-city-malabo"},
    #     ]
    # },
    # # Gabon (XAF)
    # {
    #     "country_unique_flag": "gabon-country",
    #     "currency": "xaf",
    #     "towns": [
    #         {"unique_flag": "gabon-city-libreville"},
    #     ]
    # },
    # # Italy
    # {
    #     "country_unique_flag": "italy-country",
    #     "currency": "eur",
    #     "towns": [
    #         {"unique_flag": "italy-city-rome"},
    #     ]
    # },
    # # Spain
    # {
    #     "country_unique_flag": "spain-country",
    #     "currency": "eur",
    #     "towns": [
    #         {"unique_flag": "spain-city-madrid"},
    #     ]
    # },
    # # USA
    # {
    #     "country_unique_flag": "usa-country",
    #     "currency": "usd",
    #     "towns": [
    #         {"unique_flag": "usa-city-new-york"},
    #     ]
    # },
]

# if __name__ == "__main__":
#     asyncio.run(init_data())
# Function to upsert cities into the database


async def upsert_cities():
    """
    Upserts cities into the database.

    Args:
        cities (list): List of city dictionaries with unique_flag and currency.
    """
    try:
        generic_service = GenericService(DEFAULT_LANGUAGE)
        countries = CITIES_DEFAULT_CURRENCIES
        for country in countries:
            currency_code = country['currency']
            cities = country['towns']
            ref_currency = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_CURRENCY,
                    query={"filter__code": str(currency_code).lower()},
                )
            if not ref_currency:
                continue
            for city in cities:
                # Replace this with actual database upsert logic
                print(
                    f"Upserting city: {city['unique_flag']} with currency: {currency_code}")
                ref_entity = await generic_service.fetch_one_from_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    query={"filter__unique_flag": city["unique_flag"]},
                )
                
                if ref_entity:
                    await generic_service.upsert_data_to_collection(
                        collection_key=CollectionKey.CFG_DEFAULT_RELATED_CURRENCY,
                        filter_data={
                            "targeted_id": ref_entity['id'],
                            "ref_currency_id": ref_currency['id']
                        },
                        update_data={
                            "targeted_id": ref_entity['id'],
                            "ref_currency_id": ref_currency['id']
                        }
                    )
    except Exception as e:
        print(f"Error upserting cities > : {e} ")



TELEPHONE_NETWORKS = [
    {
        "country_unique_flag": "rdc-country",
        "networks": [
            {
                "name": "Orange",
                "short_name": "drc_orange",
                "prefixes": ["84", "85", "89"],
            },
            {
                "name": "Vodacom",
                "short_name": "drc_vodacom",
                "prefixes": ["80", "81", "82", "83"],
            },
            {
                "name": "Airtel",
                "short_name": "drc_airtel",
                "prefixes": ["97", "98", "99"],
            },
            {
                "name": "Africell",
                "short_name": "drc_africell",
                "prefixes": ["90"],
            }
        ],
        "available_currency_codes": ["cdf", "usd"],
        "country_codes": ["243"],
        "max_phone_number_chars": 9,
        "min_phone_number_chars": 9,
        "city_default_currency_code": "usd",
        "ewallet_prefixes": [
            {
                "currency_code": "cdf",
                "prefixes": ["5000", "5100", "5200", "5300", "5400",],
                "wallet_type": EWalletType.CUSTOMER.value,
            },
            {
                "currency_code": "usd",
                "prefixes": ["6000", "6100", "6200", "6300", "6400"],
                "wallet_type": EWalletType.CUSTOMER.value,
            }, 
            {
                "currency_code": "usd",
                "prefixes": ["6600", "6700", "6800", "6900"],
                "wallet_type": EWalletType.AGENT.value,
            }, 
            {
                "currency_code": "usd",
                "prefixes": ["7500", "7600", "7700", "7800", "7900"],
                "wallet_type": EWalletType.AGENT.value,
            }, 
        ]
    }
]

async def seed_telephone_networks():
    """
    Populate telephone networks, phone prefixes, country codes, currencies,
    and ewallet prefixes from TELEPHONE_NETWORKS configuration.
    """
    generic_service = GenericService(DEFAULT_LANGUAGE)

    for country_config in TELEPHONE_NETWORKS:
        country_unique_flag = normalize_unique_flag(
            country_config["country_unique_flag"])

        # 1. Find the country by unique_flag in REF_ENTITY
        country_entity = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.REF_ENTITY,
            query={"filter__unique_flag": country_unique_flag},
        )

        if not country_entity:
            print(
                f"[TELEPHONE_NETWORKS] Country not found: {country_unique_flag}, skipping...")
            continue

        cfg_system_country_id = country_entity["id"]
        print(
            f"[TELEPHONE_NETWORKS] Processing country: {country_entity['name']} ({country_unique_flag})")
        
        if 'max_phone_number_chars' in country_config and 'min_phone_number_chars' in country_config:
            if not country_entity.get("min_phone_number_chars") or not country_entity.get("max_phone_number_chars") or country_entity.get("min_phone_number_chars") ==0 or country_entity.get("max_phone_number_chars") ==0:
                await generic_service.update_data_in_collection(
                    collection_key=CollectionKey.REF_ENTITY,
                    item_id=cfg_system_country_id,
                    data={
                        "min_phone_number_chars": country_config['min_phone_number_chars'],
                        "max_phone_number_chars": country_config['max_phone_number_chars'],
                    },
                )

        # 3. Create telephone networks and their prefixes
        for network in country_config.get("networks", []):
            # Create/update telephone network
            telephone_network = await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.REF_TELEPHONE_NETWORK,
                filter_data={"short_name": network["short_name"]},
                update_data={
                    "name": network["name"],
                    "short_name": network["short_name"],
                    "cfg_system_country_id": cfg_system_country_id,
                    "is_available": True,
                },
            )
            print(
                f"  [REF_TELEPHONE_NETWORK] {network['name']} ({network['short_name']})")

            # Create phone prefixes for this network
            for prefix in network.get("prefixes", []):
                await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_PHONE_PREFIX,
                    filter_data={
                        "prefix": prefix,
                        "ref_telephone_network_id": telephone_network["id"],
                        "cfg_system_country_id": cfg_system_country_id,
                    },
                    update_data={
                        "prefix": prefix,
                        "ref_telephone_network_id": telephone_network["id"],
                        "cfg_system_country_id": cfg_system_country_id,
                    },
                )
                print(f"    [CFG_COUNTRY_RELATED_PHONE_PREFIX] +{prefix}")

        # 4. Create country codes
        for country_code in country_config.get("country_codes", []):
            await generic_service.upsert_data_to_collection(
                collection_key=CollectionKey.CFG_COUNTRY_RELATED_COUNTRY_CODE,
                filter_data={
                    "country_code": country_code,
                    "cfg_system_country_id": cfg_system_country_id,
                },
                update_data={
                    "country_code": country_code,
                    "cfg_system_country_id": cfg_system_country_id,
                },
            )
            print(f"  [CFG_COUNTRY_RELATED_COUNTRY_CODE] +{country_code}")

        # 5. Create available currencies for this country
        for currency_code in country_config.get("available_currency_codes", []):
            # Find the currency by code
            currency = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY,
                query={"filter__code": currency_code.lower()},
            )

            if currency:
                is_default = currency_code == country_config.get(
                    "city_default_currency_code", "")
                await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_CURRENCY,
                    filter_data={
                        "ref_currency_id": currency["id"],
                        "cfg_system_country_id": cfg_system_country_id,
                    },
                    update_data={
                        "ref_currency_id": currency["id"],
                        "cfg_system_country_id": cfg_system_country_id,
                        "is_default": is_default,
                    },
                )
                print(
                    f"  [CFG_COUNTRY_RELATED_CURRENCY] {currency_code.upper()} (default: {is_default})")
            else:
                print(
                    f"  [CFG_COUNTRY_RELATED_CURRENCY] Currency not found: {currency_code}")

        # 6. Create ewallet prefixes if present
        for ewallet_config in country_config.get("ewallet_prefixes", []):
            currency_code = ewallet_config.get("currency_code", "").lower()
            wallet_type = ewallet_config.get(
                "wallet_type", EWalletType.CUSTOMER.value)

            # Find the currency
            currency = await generic_service.fetch_one_from_collection(
                collection_key=CollectionKey.REF_CURRENCY,
                query={"filter__code": currency_code},
            )

            if not currency:
                print(
                    f"  [CFG_COUNTRY_RELATED_EWALLET_PREFIX] Currency not found: {currency_code}, skipping...")
                continue

            for prefix in ewallet_config.get("prefixes", []):
                await generic_service.upsert_data_to_collection(
                    collection_key=CollectionKey.CFG_COUNTRY_RELATED_EWALLET_PREFIX,
                    filter_data={
                        "prefix": prefix,
                        "cfg_system_country_id": cfg_system_country_id,
                        "ref_currency_id": currency["id"],
                    },
                    update_data={
                        "prefix": prefix,
                        "cfg_system_country_id": cfg_system_country_id,
                        "ref_currency_id": currency["id"],
                        "lokotro_wallet_type": wallet_type,
                    },
                )
                print(
                    f"    [CFG_COUNTRY_RELATED_EWALLET_PREFIX] {prefix} ({currency_code} - {wallet_type})")

    print("[TELEPHONE_NETWORKS] Seeding completed!")


from typing import Any, Optional


def _extract_id_from_result(result: Any) -> Optional[Any]:
    """
    Try to extract id/_id from different possible return formats.
    """
    if result is None:
        return None

    if isinstance(result, str):
        return result
    
    if isinstance(result, dict):
        return result.get("id") or result.get("_id")

    if hasattr(result, "id"):
        value = getattr(result, "id")
        if value is not None:
            return value

    if hasattr(result, "_id"):
        value = getattr(result, "_id")
        if value is not None:
            return value

    if hasattr(result, "model_dump"):
        data = result.model_dump()
        return data.get("id") or data.get("_id")

    return None


async def _resolve_created_node_id(generic_service, created_result: Any, payload: dict) -> Optional[Any]:
    """
    Resolve inserted node id either from insert result or by refetching.
    """
    created_id = _extract_id_from_result(created_result)
    if created_id is not None:
        return created_id

    records = await generic_service.fetch_data_from_collection(
        collection_key=CollectionKey.CFG_ORGANISM_CHART,
        query={
            "name": payload["name"],
            "cfg_organism_chart_id": payload["cfg_organism_chart_id"],
        }
    )

    if records:
        return _extract_id_from_result(records[0])

    return None


async def _create_org_chart_node(generic_service, node: dict, parent_id: Optional[Any] = None,org_id: Optional[Any] = None):
    payload = {
        "name": node["name"],
        "description_str": node.get("description_str", ""),
        "cfg_organism_chart_id": parent_id,
        "sys_organization_id": org_id,
    }

    DebugService.app_debug_print(f"[_create_org_chart_node] org chart node payload : {payload} ",True)

    created_result = await generic_service.add_data_to_collection(
        collection_key=CollectionKey.CFG_ORGANISM_CHART,
        data=payload
    )

    DebugService.app_debug_print(f"[_create_org_chart_node] org chart node created result : {created_result} ",True)


    created_id = await _resolve_created_node_id(
        generic_service=generic_service,
        created_result=created_result,
        payload=payload,
    )

    DebugService.app_debug_print(f"[_create_org_chart_node] org chart node created id : {created_id} ",True)

    if created_id is None:
        raise ValueError(f"Unable to resolve created node id for '{node['name']}'")


    for child in node.get("children", []):
        await _create_org_chart_node(
            generic_service=generic_service,
            node=child,
            parent_id=created_id,
            org_id=org_id
        )


async def create_org_charts():
    try:
        generic_service = GenericService(DEFAULT_LANGUAGE)

        org_charts = [
            {
                "name": "CONSEIL D'ADMINISTRATION",
                "description_str": "Organe de gouvernance et d'orientation stratégique.",
                "cfg_organism_chart_id": None,
                "children": [
                    {
                        "name": "DIRECTION GENERALE",
                        "description_str": "Organe de direction et de coordination générale des activités.",
                        "cfg_organism_chart_id": None,
                        "children": [
                            {
                                "name": "POOL DES ASSISTANTS",
                                "description_str": "Structure d'appui à la Direction Générale.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "SECRETARIAT",
                                "description_str": "Assure le secrétariat administratif de la Direction Générale.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "COMMUNICATION & PRESSE",
                                "description_str": "Gère la communication institutionnelle et les relations presse.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "AUDIT",
                                "description_str": "Assure l'audit interne et le contrôle des processus.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "CELLULE JURIDIQUE",
                                "description_str": "Prend en charge les questions juridiques et réglementaires.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "SECURITE & GARDIENNAGE",
                                "description_str": "Assure la sécurité des sites, des biens et des personnes.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "COORDINATION DES AGENCES PROVINCIALES",
                                "description_str": "Coordonne les activités des agences provinciales.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "Service Inspection réseaux",
                                "description_str": "Assure l'inspection et le suivi opérationnel des réseaux.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "CGPMP",
                                "description_str": "Cellule/structure de gestion de la passation des marchés publics.",
                                "cfg_organism_chart_id": None,
                                "children": []
                            },
                            {
                                "name": "DRH",
                                "description_str": "Direction des Ressources Humaines.",
                                "cfg_organism_chart_id": None,
                                "children": [
                                    {
                                        "name": "Chef du Personnel",
                                        "description_str": "Supervise l'administration du personnel.",
                                        "cfg_organism_chart_id": None,
                                        "children": [
                                            {
                                                "name": "Service Suivi Carrière",
                                                "description_str": "Assure le suivi de carrière du personnel.",
                                                "cfg_organism_chart_id": None,
                                                "children": []
                                            },
                                            {
                                                "name": "Service Paie",
                                                "description_str": "Gère la paie et les éléments de rémunération.",
                                                "cfg_organism_chart_id": None,
                                                "children": []
                                            },
                                            {
                                                "name": "Service Formation",
                                                "description_str": "Prend en charge la formation et le développement des compétences.",
                                                "cfg_organism_chart_id": None,
                                                "children": []
                                            },
                                            {
                                                "name": "Service Social",
                                                "description_str": "Assure le suivi des questions sociales du personnel.",
                                                "cfg_organism_chart_id": None,
                                                "children": []
                                            },
                                            {
                                                "name": "Service contentieux administratifs",
                                                "description_str": "Gère les contentieux administratifs liés au personnel.",
                                                "cfg_organism_chart_id": None,
                                                "children": []
                                            },
                                        ]
                                    }
                                ]
                            },
                            {
                                "name": "DA",
                                "description_str": "Direction Administrative.",
                                "cfg_organism_chart_id": None,
                                "children": [
                                    {
                                        "name": "Services Généraux",
                                        "description_str": "Gère les services généraux et moyens administratifs.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Informatique",
                                        "description_str": "Assure la gestion des systèmes informatiques.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Relations Publiques",
                                        "description_str": "Assure les relations publiques et protocolaires.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Supervision Dépôt II",
                                        "description_str": "Supervise les activités du Dépôt II.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Suivi Billetterie",
                                        "description_str": "Assure le suivi administratif de la billetterie.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                ]
                            },
                            {
                                "name": "DF",
                                "description_str": "Direction Financière.",
                                "cfg_organism_chart_id": None,
                                "children": [
                                    {
                                        "name": "Service Comptabilité",
                                        "description_str": "Assure la comptabilité générale et analytique.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Budget & Fiscalité",
                                        "description_str": "Gère le budget et les obligations fiscales.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Trésorerie",
                                        "description_str": "Assure la gestion de la trésorerie.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                ]
                            },
                            {
                                "name": "DEX",
                                "description_str": "Direction de l'Exploitation.",
                                "cfg_organism_chart_id": None,
                                "children": [
                                    {
                                        "name": "Service Mouvement",
                                        "description_str": "Organise les mouvements et l'exploitation des véhicules.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Méthodes & Organisation",
                                        "description_str": "Définit les méthodes et l'organisation de l'exploitation.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Billetterie",
                                        "description_str": "Gère la billetterie d'exploitation.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Contrôle",
                                        "description_str": "Assure le contrôle de l'exploitation.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                ]
                            },
                            {
                                "name": "DC",
                                "description_str": "Direction Commerciale.",
                                "cfg_organism_chart_id": None,
                                "children": [
                                    {
                                        "name": "Service Interurbain",
                                        "description_str": "Gère les activités de transport interurbain.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Location",
                                        "description_str": "Gère les activités de location.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Transport Scolaire",
                                        "description_str": "Prend en charge les services de transport scolaire.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Marketing et Publicité",
                                        "description_str": "Assure le marketing et la publicité.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                ]
                            },
                            {
                                "name": "DT",
                                "description_str": "Direction Technique.",
                                "cfg_organism_chart_id": None,
                                "children": [
                                    {
                                        "name": "Service Atelier",
                                        "description_str": "Assure les activités d'atelier.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Maintenance des Equipements Industriels",
                                        "description_str": "Gère la maintenance des équipements industriels.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Dépannage",
                                        "description_str": "Assure les interventions de dépannage.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Ordonnancement & Hydrocarbures",
                                        "description_str": "Gère l'ordonnancement technique et les hydrocarbures.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Service Logistique",
                                        "description_str": "Assure la logistique technique et opérationnelle.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                    {
                                        "name": "Serv. Contrôle Technique & Analyse des Pannes",
                                        "description_str": "Assure le contrôle technique et l'analyse des pannes.",
                                        "cfg_organism_chart_id": None,
                                        "children": []
                                    },
                                ]
                            },
                        ]
                    },
                    {
                        "name": "COLLEGE DES COMMISSAIRES AUX COMPTES",
                        "description_str": "Organe de contrôle et de commissariat aux comptes.",
                        "cfg_organism_chart_id": None,
                        "children": []
                    }
                ]
            }
        ]

        check = await generic_service.fetch_data_from_collection(
            collection_key=CollectionKey.CFG_ORGANISM_CHART,
            all_data=True,
            query={}
        )

        DebugService.app_debug_print(f"[create_org_charts] charts found: {len(check)}",True)


        if len(check) > 0:
            return
        
        main_profil = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.RBAC_PROFILE,
            query={"flag":ESysProfileFlag.MAIN_PROFILE.value}
        )
        DebugService.app_debug_print(f"[create_org_charts] main profil found : {main_profil}",True)
        if not main_profil:
            DebugService.app_debug_print("[create_org_charts] No main profil found",True)
            return
        
        organization = await generic_service.fetch_one_from_collection(
            collection_key=CollectionKey.SYS_ORGANIZATION,
            query={"rbac_profile_id": main_profil['id']}
        )

        DebugService.app_debug_print(f"[create_org_charts] organization found for main profil : {organization}",True)
        if not organization:
            DebugService.app_debug_print("[create_org_charts] No organization found for main profil",True)
            return

        for org_chart in org_charts:
            try:
                await _create_org_chart_node(
                    generic_service=generic_service,
                    node=org_chart,
                    parent_id=None,
                    org_id=organization['id']
                )
            except ValueError as e:
                DebugService.app_debug_print(f"Error in create_org_charts: {e}",True)
            except PermissionError as e:
                DebugService.app_debug_print(f"Permission Error in create_org_charts: {e}",True)

    except ValueError as e:
            DebugService.app_debug_print(f"Error in create_org_charts > 1 : {e}",True)
    except PermissionError as e:
        DebugService.app_debug_print(f"Permission Error in create_org_charts > 2: {e}",True)


# Example usage
if __name__ == "__main__":

    loop = asyncio.get_event_loop()  # Get the current event loop
    loop.run_until_complete(init_data())  # Run without creating a nested loop

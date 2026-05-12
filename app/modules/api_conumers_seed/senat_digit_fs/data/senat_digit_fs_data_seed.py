"""Entry-point for the Senat-Digit FS (S2S) consumer seed.

Mirrors the structure used in trans_agent_flutter_app: this seed creates
application records (bottom-nav apps + sub_menus). It runs after the
top-level seed.py (RBAC titles, permissions, endpoints) and before
seed_core.py (which wires `core_seeds` restrictions to apps/menus).

At clone-and-rename time the apps list is empty; populate it during
the Senat-Digit feature module work (§3.5 of COWORK_PROMPT.md).
"""

from app.db.session import init_db
from app.modules.core.services.generic.generic_services import GenericService
from app.modules.core.models.field_translation_keys import DEFAULT_LANGUAGE
from app.modules.api_conumers_seed.senat_digit_fs.apps.senat_digit_fs_app import (
    get_senat_digit_fs_seed_app,
)
from app.modules.api_conumers_seed.senat_digit_fs.rbac.senat_digit_fs_rbac import (
    CORE_SENAT_DIGIT_FS_APP_RBAC_TITLE_DB,
)


async def init_senat_digit_fs_modules_data():
    """Seed Senat-Digit FS (S2S) application records + RBAC titles."""
    await init_db()
    await create_senat_digit_fs_apps()
    await create_senat_digit_fs_rbac()


async def create_senat_digit_fs_rbac():
    try:
        from app.modules.core.services.rbac_role.rbac_role_service import RbacRoleService
        rbac_role_service = RbacRoleService(DEFAULT_LANGUAGE)
        await rbac_role_service.seed_rbac_from_module(CORE_SENAT_DIGIT_FS_APP_RBAC_TITLE_DB)
    except ValueError as e:
        print(f"Error in create_senat_digit_fs_rbac: {e}")
    except PermissionError as e:
        print(f"Permission Error: {e}")


async def create_senat_digit_fs_apps():
    generic_service = GenericService(DEFAULT_LANGUAGE)
    apps = get_senat_digit_fs_seed_app()
    for index, app in enumerate(apps):
        try:
            saved = await generic_service.on_single_application_save(app)
            print(f"Senat-Digit FS (S2S) app saved: {saved}  index: {index}")
        except ValueError as e:
            print(f"Error saving Senat-Digit FS (S2S) app at index {index}: {e}")
        except PermissionError as e:
            print(f"Permission error saving Senat-Digit FS (S2S) app at index {index}: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_senat_digit_fs_modules_data())

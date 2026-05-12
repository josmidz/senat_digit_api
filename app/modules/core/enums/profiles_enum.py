from enum import Enum

# PROFIL FLAG


class ESysProfileFlag(str, Enum):
    SYSTEM_PROFIL = "system_profil" 
    MAIN_PROFILE = "main_profile"
    TEST_SYS_PROFIL = "test_profil"
    TRANS_VISITOR = "trans_visitor"
    TRANS_CUSTOMER = "trans_customer"


# PROFIL SUPER ROLE FLAG
class ESysProfilSuperUserRoleFlag(str, Enum):
    TEST_PROFIL_SUPER_ADMIN = "test_profil_super_admin"

    # SYSTEM ROLES
    SYSTEM_PROFIL_SUPER_ADMIN = "system_profil_super_admin"

    # MAIN_PROFILE roles — Sénat-Digit chamber roles.
    # `MAIN_PROFILE_SUPER_ADMIN` retains god-mode (every senat-digit
    # feature permission) for ops/break-glass; production accounts use
    # SENATEUR or GREFFIER which split the matrix per parliamentary
    # responsibility:
    #   SENATEUR  — participates: cast vote, request parole, sign
    #               presence, propose amendment, give proxy.
    #   GREFFIER  — orchestrates: open/close session, configure scrutin,
    #               publish agenda/documents, dispatch parole, audit
    #               read access. Cannot vote.
    MAIN_PROFILE_SUPER_ADMIN = "main_profile_super_admin"
    SENATEUR = "senateur"
    GREFFIER = "greffier"
    # REGULATOR_OF_LINE_LAUNCHING_TRANS_ROLE = "regulator_of_line_launching_trans_role"
    # SUPERVISOR_TRANS_ROLE = "supervisor_trans_role"
    DISTRIBUTOR_TRANS_ROLE = "distributor_trans_role"
    CONTROLLER_TRANS_ROLE = "controller_trans_role"
    REGULATOR_OF_LINE_LAUNCHING_TRANS_ROLE = "regulator_of_line_launching_trans_role"
    REGULATOR_OF_LINE_TRANS_ROLE = "regulator_of_line_trans_role"
    DRIVER_TRANS_ROLE = "driver_trans_role"
    PERCEPTOR_TRANS_ROLE = "perceptor_trans_role"
    PARKER_TRANS_ROLE = "parker_trans_role"
    # PLANNER_TRANS_ROLE = "planner_trans_role"


    TRANS_FINANCER_ROLE = "trans_financer_role"
    TRANS_EXPENSE_TYPE_PERSON_ROLE = "trans_expense_type_person_role"
    TRANS_ACCOUTANT_ROLE = "trans_accoutant_role"
    TRANS_RH_ROLE = "trans_rh_role"

    OPERATION_STAFF_TRANS_ROLE = "operation_staff_trans_role"

    TRANS_CUSTOMER_ROLE = "trans_customer_role"
    TRANS_VISITOR_ROLE = "trans_visitor_role"
 


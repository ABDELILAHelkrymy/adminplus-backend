import uuid
from django.core.management.base import BaseCommand
from users.models import Permission, Role, SystemRole


class Command(BaseCommand):
    help = "Populate the database with predefined permissions and roles"

    def handle(self, *args, **kwargs):
        # Define permissions
        permissions_data = [
            # General Permissions
            {"name": "view_user", "resource": "user", "action": "view"},
            {"name": "manage_user", "resource": "user", "action": "manage"},
            {"name": "view_roles", "resource": "role", "action": "view"},
            {"name": "manage_roles", "resource": "role", "action": "manage"},

            # Business Account Permissions
            {"name": "view_business_account", "resource": "business_account", "action": "view"},
            {"name": "manage_business_account", "resource": "business_account", "action": "manage"},
            {"name": "invite_accountant", "resource": "business_account", "action": "invite"},
            {"name": "manage_internal_users", "resource": "business_account", "action": "manage_users"},

            # Invoice Permissions
            {"name": "view_invoices", "resource": "invoice", "action": "view"},
            {"name": "create_invoices", "resource": "invoice", "action": "create"},
            {"name": "edit_invoices", "resource": "invoice", "action": "edit"},
            {"name": "delete_invoices", "resource": "invoice", "action": "delete"},
            {"name": "send_invoices", "resource": "invoice", "action": "send"},
            {"name": "mark_invoices_paid", "resource": "invoice", "action": "mark_paid"},

            # Expense Permissions
            {"name": "view_expenses", "resource": "expense", "action": "view"},
            {"name": "create_expenses", "resource": "expense", "action": "create"},
            {"name": "edit_expenses", "resource": "expense", "action": "edit"},
            {"name": "delete_expenses", "resource": "expense", "action": "delete"},

            # Reports Permissions
            {"name": "view_reports", "resource": "report", "action": "view"},
            {"name": "generate_reports", "resource": "report", "action": "generate"},
            {"name": "export_reports", "resource": "report", "action": "export"},

            # Integration Permissions
            {"name": "view_integrations", "resource": "integration", "action": "view"},
            {"name": "manage_integrations", "resource": "integration", "action": "manage"},
            {"name": "sync_integrations", "resource": "integration", "action": "sync"},

            # Accountant Connection Permissions
            {"name": "view_connections", "resource": "connection", "action": "view"},
            {"name": "manage_connections", "resource": "connection", "action": "manage"},
            {"name": "update_access_level", "resource": "connection", "action": "update_access"},

            # Data Sharing Permissions
            {"name": "view_data_sharing_preferences", "resource": "data_sharing", "action": "view"},
            {"name": "update_data_sharing_preferences", "resource": "data_sharing", "action": "update"},
        ]

        # Create permissions
        self.stdout.write("Creating permissions...")
        for perm_data in permissions_data:
            permission, created = Permission.objects.get_or_create(
                name=perm_data["name"],
                defaults={
                    "resource": perm_data["resource"],
                    "action": perm_data["action"],
                },
            )
            if created:
                self.stdout.write(f"  Created permission: {permission.name}")
            else:
                self.stdout.write(f"  Permission already exists: {permission.name}")

        # Define roles and their associated permissions
        roles_data = {
            SystemRole.ADMIN: [
                "view_user", "manage_user", "view_roles", "manage_roles",
                "view_business_account", "manage_business_account", "invite_accountant", "manage_internal_users",
                "view_invoices", "create_invoices", "edit_invoices", "delete_invoices", "send_invoices", "mark_invoices_paid",
                "view_expenses", "create_expenses", "edit_expenses", "delete_expenses",
                "view_reports", "generate_reports", "export_reports",
                "view_integrations", "manage_integrations", "sync_integrations",
                "view_connections", "manage_connections", "update_access_level",
                "view_data_sharing_preferences", "update_data_sharing_preferences",
            ],
            SystemRole.INTERNAL_ACCOUNTANT: [
                "view_invoices", "create_invoices", "edit_invoices", "mark_invoices_paid",
                "view_expenses", "create_expenses", "edit_expenses",
                "view_reports", "generate_reports",
                "view_business_account",
            ],
            SystemRole.EMPLOYEE: [
                "view_invoices", "create_invoices",
                "view_expenses", "create_expenses",
            ],
            SystemRole.VIEWER: [
                "view_user", "view_business_account", "view_invoices", "view_expenses", "view_reports",
            ],
        }

        # Create roles and assign permissions
        self.stdout.write("Creating roles and assigning permissions...")
        for role_name, permission_names in roles_data.items():
            role, created = Role.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(f"  Created role: {role.name}")
            else:
                self.stdout.write(f"  Role already exists: {role.name}")

            # Assign permissions to the role
            for perm_name in permission_names:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(f"  Permission not found: {perm_name}")

        self.stdout.write("Roles and permissions setup completed successfully!")
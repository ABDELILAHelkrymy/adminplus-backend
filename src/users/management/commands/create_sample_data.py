from django.core.management.base import BaseCommand
from users.models import User, Role, SystemRole, UserRole, BusinessAccount, ExternalAccountantAccount


class Command(BaseCommand):
    help = "Create a BusinessAccount with associated users and an External Accountant"

    def handle(self, *args, **kwargs):
        # Ensure roles exist
        self.stdout.write("Ensuring roles exist...")
        roles = {}
        for system_role in SystemRole.choices:
            role_name = system_role[0]
            role, created = Role.objects.get_or_create(name=role_name)
            roles[role_name] = role
            if created:
                self.stdout.write(f"  Created role: {role.name}")
            else:
                self.stdout.write(f"  Role already exists: {role.name}")

        # Create Admin User
        self.stdout.write("Creating Admin user...")
        admin_user, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={
                "first_name": "Admin",
                "last_name": "User",
                "is_active": True,
            },
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()
            UserRole.objects.create(user=admin_user, role=roles[SystemRole.ADMIN], system_role=SystemRole.ADMIN)
            self.stdout.write(f"  Created Admin user: {admin_user.email}")
        else:
            self.stdout.write(f"  Admin user already exists: {admin_user.email}")

        # Create BusinessAccount
        self.stdout.write("Creating BusinessAccount...")
        business_account, created = BusinessAccount.objects.get_or_create(
            business_name="Sample Business",
            defaults={
                "tax_number": "123456789",
                "business_address": "123 Business St, City, Country",
                "phone_number": "+1234567890",
                "website": "https://example.com",
                "primary_user": admin_user,
            },
        )
        if created:
            self.stdout.write(f"  Created BusinessAccount: {business_account.business_name}")
        else:
            self.stdout.write(f"  BusinessAccount already exists: {business_account.business_name}")

        # Create Internal Accountant
        self.stdout.write("Creating Internal Accountant...")
        accountant_user, created = User.objects.get_or_create(
            email="accountant@example.com",
            defaults={
                "first_name": "Internal",
                "last_name": "Accountant",
                "is_active": True,
            },
        )
        if created:
            accountant_user.set_password("accountant123")
            accountant_user.save()
            UserRole.objects.create(
                user=accountant_user, role=roles[SystemRole.INTERNAL_ACCOUNTANT], system_role=SystemRole.INTERNAL_ACCOUNTANT
            )
            self.stdout.write(f"  Created Internal Accountant: {accountant_user.email}")
        else:
            self.stdout.write(f"  Internal Accountant already exists: {accountant_user.email}")
        business_account.internal_users.add(accountant_user)

        # Create Employee
        self.stdout.write("Creating Employee...")
        employee_user, created = User.objects.get_or_create(
            email="employee@example.com",
            defaults={
                "first_name": "Employee",
                "last_name": "User",
                "is_active": True,
            },
        )
        if created:
            employee_user.set_password("employee123")
            employee_user.save()
            UserRole.objects.create(user=employee_user, role=roles[SystemRole.EMPLOYEE], system_role=SystemRole.EMPLOYEE)
            self.stdout.write(f"  Created Employee: {employee_user.email}")
        else:
            self.stdout.write(f"  Employee already exists: {employee_user.email}")
        business_account.internal_users.add(employee_user)

        # Create Viewer
        self.stdout.write("Creating Viewer...")
        viewer_user, created = User.objects.get_or_create(
            email="viewer@example.com",
            defaults={
                "first_name": "Viewer",
                "last_name": "User",
                "is_active": True,
            },
        )
        if created:
            viewer_user.set_password("viewer123")
            viewer_user.save()
            UserRole.objects.create(user=viewer_user, role=roles[SystemRole.VIEWER], system_role=SystemRole.VIEWER)
            self.stdout.write(f"  Created Viewer: {viewer_user.email}")
        else:
            self.stdout.write(f"  Viewer already exists: {viewer_user.email}")
        business_account.internal_users.add(viewer_user)

        # Create External Accountant
        self.stdout.write("Creating External Accountant...")
        external_user, created = User.objects.get_or_create(
            email="external@example.com",
            defaults={
                "first_name": "External",
                "last_name": "Accountant",
                "is_active": True,
            },
        )
        if created:
            external_user.set_password("external123")
            external_user.save()
            UserRole.objects.create(user=external_user, role=roles[SystemRole.VIEWER], system_role=SystemRole.VIEWER)
            self.stdout.write(f"  Created External Accountant User: {external_user.email}")
        else:
            self.stdout.write(f"  External Accountant User already exists: {external_user.email}")

        external_accountant, created = ExternalAccountantAccount.objects.get_or_create(
            user=external_user,  # Associate the external accountant with the user
            defaults={
                "accountant_name": "External Accountant",
                "company_name": "External Accounting Firm",
                "tax_number": "987654321",
                "contact_phone": "+9876543210",
            },
        )
        if created:
            self.stdout.write(f"  Created External Accountant: {external_accountant.accountant_name}")
        else:
            self.stdout.write(f"  External Accountant already exists: {external_accountant.accountant_name}")

        self.stdout.write("Sample data creation completed successfully!")
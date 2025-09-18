from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import Role, Permission, SystemRole


class Command(BaseCommand):
    help = 'Creates comprehensive permissions, roles, and role-permission links for the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing permissions and roles before creating new ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting permissions and roles...'))
            with transaction.atomic():
                Permission.objects.all().delete()
                Role.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Reset complete'))

        with transaction.atomic():
            # Create all permissions first
            self.create_all_permissions()
            
            # Create all roles
            roles = self.create_all_roles()
            
            # Assign permissions to roles
            self.assign_permissions_to_roles(roles)
        
        self.stdout.write(self.style.SUCCESS('Successfully created all permissions, roles, and role-permission links'))

    def create_all_permissions(self):
        """Create all system permissions"""
        self.stdout.write('Creating permissions...')
        
        # Define all resources and their actions
        resources_and_actions = {
            # User Management
            'user': ['view', 'manage', 'invite'],
            'role': ['view', 'manage'],
            'permission': ['view', 'manage'],
            
            # Business Account Management
            'business_account': ['view', 'manage', 'invite', 'manage_users', 'manage_settings'],
            
            # Invoice Management
            'invoice': ['view', 'create', 'update', 'delete', 'export', 'import', 'approve', 'process_payment'],
            'invoice_attachment': ['view', 'manage'],
            'invoice_line_item': ['view', 'manage'],
            
            # Customer & Supplier Management
            'customer': ['view', 'manage'],
            'supplier': ['view', 'manage'],
            
            # Project & Time Management
            'project': ['view', 'manage', 'manage_budget'],
            'time_entry': ['view', 'manage'],
            
            # Financial Management
            'financial_account': ['view', 'manage'],
            'transaction': ['view', 'manage', 'reconcile'],
            'transaction_category': ['view', 'manage'],
            'category': ['view', 'manage'],
            
            # Connection Management (Accountant-Client)
            'connection': ['view', 'manage', 'approve', 'reject', 'manage_access'],
            
            # Integration Management
            'integration': ['view', 'manage', 'sync', 'configure'],
            
            # Articles & Payment Methods
            'article': ['view', 'manage'],
            'payment_method': ['view', 'manage'],
            
            # Reports & Analytics
            'report': ['view', 'create', 'export'],
            'analytics': ['view'],
            'dashboard': ['view'],
            
            # System Administration
            'system': ['view_logs', 'manage_settings', 'backup', 'restore', 'view_audit'],
            
            # Notifications
            'notification': ['view', 'manage', 'send'],
        }
        
        for resource, actions in resources_and_actions.items():
            self.create_resource_permissions(resource, actions)

    def create_resource_permissions(self, resource, actions):
        """Create permissions for a resource with given actions"""
        for action in actions:
            name = f"{action}_{resource}"
            permission, created = Permission.objects.get_or_create(
                name=name,
                defaults={
                    'resource': resource,
                    'action': action
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created permission: {name}')
            else:
                self.stdout.write(f'  - Permission exists: {name}')

    def create_all_roles(self):
        """Create all system roles"""
        self.stdout.write('Creating roles...')
        
        roles = {}
        
        # Create each system role
        for system_role in SystemRole.choices:
            role_key = system_role[0]
            role_name = system_role[1]
            
            role, created = Role.objects.get_or_create(name=role_key)
            roles[role_key] = role
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created role: {role_name} ({role_key})'))
            else:
                self.stdout.write(f'  - Role exists: {role_name} ({role_key})')
        
        return roles

    def assign_permissions_to_roles(self, roles):
        """Assign appropriate permissions to each role"""
        self.stdout.write('Assigning permissions to roles...')
        
        # Define role-based permissions
        role_permissions = {
            SystemRole.ADMIN: self.get_admin_permissions(),
            SystemRole.INTERNAL_ACCOUNTANT: self.get_internal_accountant_permissions(),
            SystemRole.EXTERNAL_ACCOUNTANT: self.get_external_accountant_permissions(),
            SystemRole.EMPLOYEE: self.get_employee_permissions(),
            SystemRole.VIEWER: self.get_viewer_permissions(),
        }
        
        for role_key, permission_names in role_permissions.items():
            if role_key in roles:
                role = roles[role_key]
                # Clear existing permissions first
                role.permissions.clear()
                
                assigned_count = 0
                for perm_name in permission_names:
                    try:
                        permission = Permission.objects.get(name=perm_name)
                        role.permissions.add(permission)
                        assigned_count += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'    Warning: Permission "{perm_name}" not found')
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Assigned {assigned_count} permissions to {role_key}')
                )

    def get_admin_permissions(self):
        """Get all permissions for admin role"""
        # Admin gets all permissions
        return list(Permission.objects.values_list('name', flat=True))

    def get_internal_accountant_permissions(self):
        """Get permissions for internal accountant role"""
        return [
            # User management (limited)
            'view_user',
            
            # Business account (limited)
            'view_business_account',
            'manage_business_account',
            
            # Full invoice management
            'view_invoice', 'create_invoice', 'update_invoice', 'delete_invoice',
            'export_invoice', 'approve_invoice', 'process_payment',
            'view_invoice_attachment', 'manage_invoice_attachment',
            'view_invoice_line_item', 'manage_invoice_line_item',
            
            # Customer & supplier management
            'view_customer', 'manage_customer',
            'view_supplier', 'manage_supplier',
            
            # Project management
            'view_project', 'manage_project', 'manage_project_budget',
            'view_time_entry', 'manage_time_entry',
            
            # Full financial management
            'view_financial_account', 'manage_financial_account',
            'view_transaction', 'manage_transaction', 'reconcile_transaction',
            'view_transaction_category', 'manage_transaction_category',
            'view_category', 'manage_category',
            
            # Articles & payment methods
            'view_article', 'manage_article',
            'view_payment_method', 'manage_payment_method',
            
            # Reports & analytics
            'view_report', 'create_report', 'export_report',
            'view_analytics', 'view_dashboard',
            
            # Integrations
            'view_integration', 'manage_integration', 'sync_integration',
            
            # Notifications
            'view_notification', 'manage_notification',
        ]

    def get_external_accountant_permissions(self):
        """Get permissions for external accountant role"""
        return [
            # Limited user viewing
            'view_user',
            
            # Business account (read-only mostly)
            'view_business_account',
            
            # Invoice management (based on connection access)
            'view_invoice', 'create_invoice', 'update_invoice',
            'export_invoice', 'approve_invoice',
            'view_invoice_attachment', 'manage_invoice_attachment',
            'view_invoice_line_item', 'manage_invoice_line_item',
            
            # Customer & supplier (limited)
            'view_customer', 'manage_customer',
            'view_supplier', 'manage_supplier',
            
            # Project viewing
            'view_project', 'view_time_entry',
            
            # Financial viewing and limited management
            'view_financial_account',
            'view_transaction', 'manage_transaction', 'reconcile_transaction',
            'view_transaction_category', 'manage_transaction_category',
            'view_category', 'manage_category',
            
            # Articles & payment methods
            'view_article', 'manage_article',
            'view_payment_method', 'manage_payment_method',
            
            # Connection management
            'view_connection', 'manage_connection',
            
            # Reports
            'view_report', 'create_report', 'export_report',
            'view_analytics', 'view_dashboard',
            
            # Notifications
            'view_notification',
        ]

    def get_employee_permissions(self):
        """Get permissions for employee role"""
        return [
            # Basic user viewing
            'view_user',
            
            # Business account (read-only)
            'view_business_account',
            
            # Limited invoice management
            'view_invoice', 'create_invoice', 'update_invoice',
            'view_invoice_attachment', 'manage_invoice_attachment',
            'view_invoice_line_item', 'manage_invoice_line_item',
            
            # Customer & supplier viewing
            'view_customer',
            'view_supplier',
            
            # Project and time management
            'view_project',
            'view_time_entry', 'manage_time_entry',
            
            # Basic financial viewing
            'view_financial_account',
            'view_transaction',
            'view_transaction_category',
            'view_category',
            
            # Articles viewing
            'view_article',
            'view_payment_method',
            
            # Basic reports
            'view_report', 'view_dashboard',
            
            # Notifications
            'view_notification',
        ]

    def get_viewer_permissions(self):
        """Get permissions for viewer role"""
        return [
            # Basic viewing only
            'view_user',
            'view_business_account',
            
            # Invoice viewing
            'view_invoice',
            'view_invoice_attachment',
            'view_invoice_line_item',
            
            # Customer & supplier viewing
            'view_customer',
            'view_supplier',
            
            # Project viewing
            'view_project',
            'view_time_entry',
            
            # Financial viewing
            'view_financial_account',
            'view_transaction',
            'view_transaction_category',
            'view_category',
            
            # Articles viewing
            'view_article',
            'view_payment_method',
            
            # Basic reports and dashboard
            'view_report',
            'view_dashboard',
            
            # Notifications
            'view_notification',
        ]


from django.core.management.base import BaseCommand
from apps.users.models import Role, Permission, SystemRole


class Command(BaseCommand):
    help = 'Creates default roles and permissions for the application'

    def handle(self, *args, **options):
        # Create system roles
        admin_role, created = Role.objects.get_or_create(name=SystemRole.ADMIN)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created {SystemRole.ADMIN} role'))
        else:
            self.stdout.write(f'{SystemRole.ADMIN} role already exists')
            
        internal_accountant_role, created = Role.objects.get_or_create(name=SystemRole.INTERNAL_ACCOUNTANT)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created {SystemRole.INTERNAL_ACCOUNTANT} role'))
        else:
            self.stdout.write(f'{SystemRole.INTERNAL_ACCOUNTANT} role already exists')
            
        external_accountant_role, created = Role.objects.get_or_create(name=SystemRole.EXTERNAL_ACCOUNTANT)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created {SystemRole.EXTERNAL_ACCOUNTANT} role'))
        else:
            self.stdout.write(f'{SystemRole.EXTERNAL_ACCOUNTANT} role already exists')
            
        employee_role, created = Role.objects.get_or_create(name=SystemRole.EMPLOYEE)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created {SystemRole.EMPLOYEE} role'))
        else:
            self.stdout.write(f'{SystemRole.EMPLOYEE} role already exists')
            
        viewer_role, created = Role.objects.get_or_create(name=SystemRole.VIEWER)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created {SystemRole.VIEWER} role'))
        else:
            self.stdout.write(f'{SystemRole.VIEWER} role already exists')
            
        # Create basic permissions
        self.create_permissions()
        
        # Assign permissions to roles
        self.assign_permissions_to_admin(admin_role)
        
        self.stdout.write(self.style.SUCCESS('Successfully created default roles and permissions'))
    
    def create_permissions(self):
        """Create basic permissions"""
        # User management permissions
        self.create_resource_permissions('user', ['view', 'create', 'update', 'delete'])
        
        # Business account permissions
        self.create_resource_permissions('business', ['view', 'create', 'update', 'delete'])
        
        # Financial permissions
        self.create_resource_permissions('transaction', ['view', 'create', 'update', 'delete'])
        self.create_resource_permissions('account', ['view', 'create', 'update', 'delete'])
        
        # Accountant permissions
        self.create_resource_permissions('invitation', ['view', 'create', 'update', 'delete'])
        self.create_resource_permissions('connection', ['view', 'create', 'update', 'delete'])
        
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
                self.stdout.write(f'Created permission: {name}')
    
    def assign_permissions_to_admin(self, admin_role):
        """Assign all permissions to admin role"""
        permissions = Permission.objects.all()
        for permission in permissions:
            admin_role.permissions.add(permission)
        
        self.stdout.write(f'Assigned all permissions to {SystemRole.ADMIN} role') 
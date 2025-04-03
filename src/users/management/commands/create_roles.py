# Create a file at src/users/management/commands/create_roles.py
from django.core.management.base import BaseCommand
from users.models import Role, SystemRole

class Command(BaseCommand):
    help = 'Create default system roles'

    def handle(self, *args, **kwargs):
        # Create all roles defined in SystemRole
        roles_created = 0
        for role_name, _ in SystemRole.choices:
            role, created = Role.objects.get_or_create(name=role_name)
            if created:
                roles_created += 1
                self.stdout.write(self.style.SUCCESS(f'Created role: {role_name}'))
        
        if roles_created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created {roles_created} roles'))
        else:
            self.stdout.write(self.style.SUCCESS('All roles already exist'))
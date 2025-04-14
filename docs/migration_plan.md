# Migration Plan

This document outlines the steps to migrate from the current single-app structure to the new modular multi-app structure.

## Steps

1. **Backup the Database and Code**

   - Create a database backup
   - Ensure you have a full repository backup

2. **Copy Users App Data**

   - Copy models, views, and serializers from the existing `users` app to the new `apps/users` directory
   - Update import statements to reflect the new directory structure

3. **Distribute Models**

   - Move business account models from `users/models.py` to `apps/accounts/models.py`
   - Move accountant models from `users/models.py` to `apps/accountants/models.py`
   - Move connection models from `users/models.py` to `apps/connections/models.py`
   - Move integration models from `users/models.py` to `apps/integrations/models.py`

4. **Create New Migrations**

   - After models have been moved, create initial migrations for each app:

   ```bash
   python src/manage.py makemigrations apps.users apps.accounts apps.accountants apps.connections apps.integrations apps.financials apps.notifications apps.common
   ```

5. **Update Settings**

   - Update the `INSTALLED_APPS` setting to include all the new apps
   - Update the `AUTH_USER_MODEL` setting to point to `apps.users.User`

6. **URL Configuration**

   - Update URL patterns to point to the new app views
   - Ensure the API routing structure is correctly set up

7. **Run Migrations**

   - Apply the new migrations:

   ```bash
   python src/manage.py migrate
   ```

8. **Testing**
   - Test all functionality
   - Verify database integrity
   - Ensure all API endpoints still work

## Considerations

- This migration may require manual database operations due to the movement of models between apps
- You might need to configure custom SQL migrations to handle model moves without data loss
- Consider implementing the migration in stages to minimize downtime
- Test thoroughly in a staging environment before applying to production

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0023_customuser_assigned_branch_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='courierprofile',
            name='vehicle_number',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]

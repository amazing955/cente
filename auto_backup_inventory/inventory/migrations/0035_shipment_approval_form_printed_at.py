from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0034_role_features_tape_extra_userroleassignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='shipment',
            name='approval_form_printed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

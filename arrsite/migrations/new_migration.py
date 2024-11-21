from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('arrsite', '0005_notification_reply_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='is_company_reply',
            field=models.BooleanField(default=False),
        ),
    ]
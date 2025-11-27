from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0002_alter_order_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='meat_topping',
            field=models.CharField(blank=True, help_text='Selected meat topping if applicable.', max_length=50),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='extra_toppings',
            field=models.TextField(blank=True, help_text='Comma-separated list of extra toppings.'),
        ),
    ]

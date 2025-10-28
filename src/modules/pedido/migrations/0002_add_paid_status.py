# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pendente'),
                    ('CONFIRMED', 'Confirmado'),
                    ('PAID', 'Pago'),
                    ('PREPARING', 'Em preparação'),
                    ('CANCELLED', 'Cancelado'),
                ],
                default='PENDING',
                help_text='Status do pedido',
                max_length=50
            ),
            preserve_default=False,
        ),
    ]


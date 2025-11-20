# Generated migration for adding installment tracking fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagamento', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='installment_id',
            field=models.CharField(blank=True, help_text='ID da parcela no Asaas', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='installment_number',
            field=models.IntegerField(blank=True, help_text='Número da parcela (1, 2, 3...)', null=True),
        ),
    ]


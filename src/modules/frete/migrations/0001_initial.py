# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MelhorEnvioToken',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('access_token', models.TextField(unique=True)),
                ('refresh_token', models.TextField(unique=True)),
                ('expires_in', models.IntegerField(default=2592000)),
                ('token_type', models.CharField(default='Bearer', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Token Melhor Envio',
                'verbose_name_plural': 'Tokens Melhor Envio',
                'db_table': 'melhor_envio_token',
            },
        ),
    ]


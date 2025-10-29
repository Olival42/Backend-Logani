"""
Configuração do Celery para tarefas assíncronas
"""

import os
from celery import Celery

# Define o módulo de settings padrão para o celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_pagamento_frete.settings')

app = Celery('api_pagamento_frete')

# Usa Django settings para configuração do Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre automaticamente tasks de todos os apps Django
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


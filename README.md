# API de Pagamento e Frete - Asaas

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3+-green.svg)](https://celeryproject.org/)

## Descrição

API RESTful completa para gerenciamento de pedidos, pagamentos e frete, integrada com o gateway **Asaas**. Sistema robusto para e-commerce com processamento de pagamentos via PIX e cartão de crédito (parcelado ou à vista).

Construído com Python e Django seguindo princípios de **Clean Architecture** e **Domain-Driven Design (DDD)**, com processamento assíncrono de tarefas usando **Celery** e total containerização com **Docker**.

## ✨ Funcionalidades

- 🔐 **Autenticação JWT:** Sistema seguro de autenticação com tokens temporários
- 👥 **Gestão de Clientes:** CRUD completo + sincronização automática com Asaas
- 📦 **Gestão de Pedidos:** Criação, consulta, cancelamento e rastreamento de status
- 💳 **Checkout Completo:** Geração de links de pagamento PIX e Cartão de Crédito
- 💰 **Pagamentos Parcelados:** Suporte a até 12 parcelas com gestão automática
- 🔔 **Webhooks Inteligentes:** Processamento automático de notificações de pagamento
- ↩️ **Estorno Automático:** Cancelamento de pedidos com estorno automático
- 📧 **Emails Assíncronos:** Notificações por email (Celery) - performance otimizada
- 🏗️ **Arquitetura Limpa:** Clean Architecture + DDD + Repository Pattern

## 🛠️ Tecnologias

| Categoria | Tecnologia |
|-----------|-----------|
| **Backend** | Python 3.11+, Django 5.0, Django REST Framework |
| **Banco de Dados** | PostgreSQL 17 |
| **Cache/Messaging** | Redis 7 |
| **Processamento Assíncrono** | Celery 5.3 |
| **Gateway de Pagamento** | [Asaas API](https://docs.asaas.com/) |
| **Autenticação** | JWT (PyJWT) |
| **Containerização** | Docker, Docker Compose |
| **Arquitetura** | Clean Architecture + DDD |

## 🚀 Início Rápido

### Pré-requisitos

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Conta no [Asaas](https://www.asaas.com) (sandbox para testes)

### Instalação

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/Olival42/api_pagamento_frete.git
    cd api-pagamento-frete
    ```

2.  **Configure as variáveis de ambiente:**

    Crie uma cópia do arquivo de exemplo `.env.example` e renomeie para `.env`. Em seguida, ajuste as variáveis conforme necessário para o seu ambiente.

    ```bash
    cp .env.example .env
    ```

3.  **Construa e execute os containers:**

    Para ambiente de **desenvolvimento** (com hot-reload):

    ```bash
    docker-compose up --build
    ```

    Para ambiente de **produção**:

    Primeiro, certifique-se de que a variável `ENV` no seu arquivo `.env` está configurada para `prod` e `DEBUG` para `False`. Em seguida, execute:

    ```bash
    docker-compose up --build -d
    ```

4.  **Execute as migrações do banco de dados:**

    ```bash
    docker-compose exec web python manage.py migrate
    ```

    A aplicação estará disponível em `http://localhost:8000` (ou na porta que você configurou em `.env`).

## 📚 Documentação

- **[Documentação Técnica - Fluxo da API](./DOCUMENTACAO_TECNICA_FLUXO_API.md)** - Arquitetura, fluxos e integração completa

## 🏗️ Arquitetura

### Módulos

```
src/modules/
├── usuario/       # Autenticação e usuários
├── cliente/       # Perfil de clientes + Asaas
├── pedido/       # Gestão de pedidos
├── checkout/      # Links de pagamento (Asaas)
├── pagamento/     # Gestão de pagamentos
├── webhook/       # Processamento de notificações
└── email/         # Envio de emails automáticos
```

### Fluxo de Dados

```
Frontend → API → PostgreSQL
              ↓
            Asaas ← Webhook → Celery (Emails Assíncronos)
              ↓
         Redis Cache/MQ
```

### Comandos Docker

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Ver logs do Celery
docker-compose logs -f celery

# Reiniciar um serviço
docker-compose restart celery

# Parar tudo
docker-compose down
```

## ⚙️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` baseado em `.env.example`:

```bash
# Aplicação
ENV=dev
DEBUG=True
SECRET_KEY=sua-chave-secreta
PORT=8000

# PostgreSQL
POSTGRES_DB=api_pagamento
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Asaas (obrigatório)
ASAAS_API_KEY=sua-api-key-asaas
ASAAS_BASE_URL=https://sandbox.asaas.com/api/v3

# Email (obrigatório para notificações de pedidos)
OWNER_EMAIL=seu-email@exemplo.com
DEFAULT_FROM_EMAIL=noreply@api-pagamento.com
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=


# Ngrok (para desenvolvimento - webhook de notificações)
NGROK_AUTHTOKEN=seu-token-ngrok

# Configurações
DAYS_TO_CANCEL=2  # Prazo em dias para cancelar pedidos confirmados
```

**Importante:** 
- Obtenha sua `ASAAS_API_TOKEN` em [https://www.asaas.com](https://www.asaas.com)
- Configure o `OWNER_EMAIL` para receber notificações automáticas
- Emails são processados de forma assíncrona via Celery (melhor performance)
- O sistema inclui 3 serviços no Docker: `web`, `celery` (emails) e `celery-beat` (agendamento)

## 📦 Endpoints da API

### Autenticação
- `POST /users/register/` - Registrar usuário
- `POST /users/login/` - Login
- `POST /users/refresh-token/` - Renovar token
- `POST /users/logout/` - Logout

### Cliente
- `POST /clients/create/` - Criar perfil
- `GET /clients/detail/{id}/` - Ver perfil
- `PUT /clients/update/{id}/` - Atualizar perfil
- `POST /clientes/sync-asaas/`    # Sincronizar com Asaas

```

### Pedidos
```
POST /pedidos/create/         # Criar pedido
GET  /pedidos/detail/{id}/    # Detalhes do pedido
POST /pedidos/cancel/{id}/    # Cancelar pedido
GET  /pedidos/my-orders/      # Listar pedidos do cliente
```

### Checkout
```
POST /checkout/create/        # Criar checkout de pagamento
GET  /checkout/{id}/          # Detalhes do checkout
```

### Webhook
- `POST /webhooks/receive/` - Recebe notificações do Asaas (automático)

**📖 Consulte a [Documentação Técnica](./DOCUMENTACAO_TECNICA_FLUXO_API.md) para detalhes completos de cada endpoint.**

## 🔐 Autenticação

Todas as requisições (exceto login/registro) requerem header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Importante:**
- Token expira após uso
- Faça logout para invalidar token

## 📊 Status dos Pedidos

| Status | Descrição |
|--------|-----------|
| `PENDING` | Aguardando pagamento |
| `CONFIRMED` | Confirmado (pagamento confirmado, aguardando liquidação) |
| `PAID` | Pago e recebido (dinheiro na conta bancária) |
| `PREPARING` | Em preparação (marcado manualmente) |
| `CANCELLED` | Cancelado |

**Detalhes:**
- **Pagamento à vista:** `PENDING` → `CONFIRMED` → `PAID`
- **Pagamento parcelado:** `PENDING` → `CONFIRMED` (após 1ª parcela) → `PAID` (após última parcela)

## 📧 Sistema de Emails Assíncronos

O sistema utiliza **Celery** para processamento assíncrono de emails, garantindo **performance máxima** (<1s de resposta) nas APIs.

### Tipos de Emails Enviados

1. **Pedido Confirmado** → Email ao proprietário com detalhes completos
2. **Pedido Cancelado** → Email ao proprietário e ao cliente
3. **Estorno Processado** → Email ao cliente com informações de crédito

### Performance

| Operação | Tempo Síncrono | Tempo Assíncrono |
|----------|---------------|------------------|
| Cancelar Pedido | ~10 segundos | <1 segundo |
| Confirmar Pedido | ~10 segundos | <1 segundo |

### Como Funciona

```
API → Serializa dados → Enfileira no Redis → Retorna resposta
                                           ↓
                                      Celery Worker
                                           ↓
                                      Envia Email
```

### Logs e Monitoramento

```bash
# Ver logs do Celery em tempo real
docker-compose logs -f celery

# Ver status dos workers
docker exec celery-worker celery -A api_pagamento_frete inspect active
```

## 🧪 Testando a API

### 1. Criar Usuário
```bash
curl -X POST http://localhost:8000/api/usuarios/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "email": "joao@example.com",
    "password": "senha123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/usuarios/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "joao@example.com",
    "password": "senha123"
  }'
```

### 3. Criar Cliente
```bash
curl -X POST http://localhost:8000/api/clientes/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "name": "João Silva",
    "cpf": "12345678900",
    "phone": "11987654321",
    "mobile_phone": "11987654321",
    "email": "joao@example.com",
    "address": {
      "address": "Rua Exemplo, 123",
      "number": "123",
      "city": "São Paulo",
      "state": "SP",
      "postal_code": "01234567"
    }
  }'
```

### 4. Criar Pedido
```bash
curl -X POST http://localhost:8000/api/pedidos/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "client_id": "uuid-do-cliente",
    "items": [
      {
        "product_id": "prod_123",
        "product_name": "Produto A",
        "quantity": 2,
        "unit_price": 50.00
      }
    ]
  }'
```

### 5. Criar Checkout PIX
```bash
curl -X POST http://localhost:8000/api/checkout/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "order_id": "uuid-do-pedido",
    "payment_method": "PIX",
    "installments": 1
  }'
```

**📖 Veja mais exemplos na [Documentação Técnica para Frontend](./DOCUMENTACAO_TECNICA_FRONTEND.md)**

## 🐛 Troubleshooting

### Erro: "Token não informado"
- Certifique-se de incluir o header `Authorization: Bearer <token>`
- Faça login novamente para obter um novo token

### Erro: "Celery worker não inicia"
```bash
# Ver logs
docker-compose logs celery

# Verificar se Redis está rodando
docker-compose ps redis

# Reiniciar serviço
docker-compose restart celery
```

### Emails não são enviados
```bash
# Ver logs do Celery
docker-compose logs -f celery | grep email

# Verificar se worker está processando tasks
docker exec celery-worker celery -A api_pagamento_frete inspect registered
```

### Banco de dados não inicia
```bash
docker-compose down -v
docker-compose up -d
```

### Webhook não recebe notificações
- Certifique-se de que o Ngrok está configurado
- Verifique a URL do webhook no painel do Asaas
- Veja logs: `docker-compose logs -f web | grep webhook`

### Performance lenta
- Verifique se o Celery está rodando: `docker-compose ps celery`
- Verifique logs de tempo de resposta
- Considere escalar workers do Celery se necessário

## 🚀 Deploy e Produção

### Checklist de Produção

- [ ] Alterar `ENV=prod` no `.env`
- [ ] Alterar `DEBUG=False` no `.env`
- [ ] Configurar variáveis de ambiente de produção
- [ ] Configurar credenciais SMTP reais
- [ ] Configurar backup do banco de dados
- [ ] Escalar workers do Celery conforme demanda
- [ ] Configurar HTTPS (Nginx/Caddy como proxy reverso)

### Escalando Workers do Celery

Edite `docker-compose.yml` e aumente o número de replicas:

```yaml
celery:
  deploy:
    replicas: 3  # 3 workers processando emails
```

## 📊 Monitoramento

### Celery Flower (Visualização)

```bash
# Adicionar ao docker-compose.yml
celery-flower:
  build: .
  command: celery -A api_pagamento_frete flower
  ports:
    - "5555:5555"
```

Acesse: `http://localhost:5555`

### Logs

```bash
# Todos os serviços
docker-compose logs -f

# Apenas API
docker-compose logs -f web

# Apenas Celery
docker-compose logs -f celery
```

## 📄 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).

---

⭐ **Star este projeto se ele te ajudou!** ⭐
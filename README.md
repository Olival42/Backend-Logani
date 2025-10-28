# API de Gateway de Pagamento

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)

## Descrição

API RESTful para gateway de pagamentos integrado com **Asaas**. Sistema completo para gerenciamento de pedidos, autenticação de usuários e processamento de pagamentos via PIX e cartão de crédito.

Construído com Python e Django seguindo princípios de **Domain-Driven Design (DDD)**, o projeto é totalmente containerizado com Docker.

## Funcionalidades

- 🔐 **Autenticação JWT:** Sistema seguro de autenticação com refresh tokens
- 👥 **Gestão de Clientes:** CRUD completo + integração automática com Asaas
- 📦 **Gestão de Pedidos:** Criação, consulta e cancelamento de pedidos
- 💳 **Checkout Asaas:** Geração automática de links de pagamento
- 🔔 **Webhooks:** Processamento automático de notificações de pagamento
- 📊 **Status Tracking:** Acompanhamento de status de pedidos em tempo real
- 📧 **Notificações por Email:** Emails automáticos para pedidos confirmados
- 🏗️ **Arquitetura DDD:** Separação clara de responsabilidades por módulos

## Tecnologias Utilizadas

- **Backend:** Python 3.11+, Django 5.0, Django REST Framework
- **Banco de Dados:** PostgreSQL 17
- **Cache:** Redis 7
- **Gateway de Pagamento:** [Asaas](https://www.asaas.com)
- **Autenticação:** JWT (Simple JWT)
- **Containerização:** Docker, Docker Compose
- **Arquitetura:** Domain-Driven Design (DDD)

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

- **[Documentação para Frontend](./DOCUMENTACAO_API_FRONTEND.md)** - Guia completo para integração
- **[Fluxo Completo da API](./FLUXO_API_COMPLETO.md)** - Documentação técnica detalhada

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
            Asaas ← Webhook
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

# Ngrok (para desenvolvimento)
NGROK_AUTHTOKEN=seu-token-ngrok
```

**Importante:** 
- Obtenha sua `ASAAS_API_KEY` em [https://www.asaas.com](https://www.asaas.com)
- O sistema envia emails automáticos para `OWNER_EMAIL` quando pedidos são confirmados
- Configure suas credenciais de email para receber notificações em produção

## 📦 Endpoints Principais

### Autenticação
- `POST /users/register/` - Registrar usuário
- `POST /users/login/` - Login
- `POST /users/refresh-token/` - Renovar token
- `POST /users/logout/` - Logout

### Cliente
- `POST /clients/create/` - Criar perfil
- `GET /clients/detail/{id}/` - Ver perfil
- `PUT /clients/update/{id}/` - Atualizar perfil

### Pedido
- `POST /orders/create/` - Criar pedido
- `GET /orders/detail/{id}/` - Ver pedido
- `GET /orders/my-orders/` - Listar meus pedidos
- `POST /orders/cancel/{id}/` - Cancelar pedido

### Checkout
- `POST /checkouts/create/` - Criar link de pagamento
- `GET /checkouts/detail/{id}/` - Ver checkout

### Webhook
- `POST /webhooks/receive/` - Recebe notificações do Asaas (automático)

## 🔐 Autenticação

Todas as requisições (exceto login/registro) requerem header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

Token expira em **1 hora**. Use `/users/refresh-token/` para renovar.

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

## 📧 Notificações por Email

O sistema envia emails automáticos quando pedidos são confirmados.

### Como Funciona

1. **Quando um pedido é confirmado** (via webhook), o sistema envia email **IMEDIATAMENTE**
2. **Email é enviado** automaticamente para o proprietário do e-commerce
3. **Email inclui:** 
   - Dados do pedido (referência, total, itens)
   - Informações do cliente (nome, CPF, contatos)
   - Endereço completo para entrega
   - Lista de produtos para embalagem/frete

### Configuração

Configure as variáveis no `.env`:
```bash
OWNER_EMAIL=seu-email@exemplo.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=senha-de-app
```

**Nota:** Para desenvolvimento, use: `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`

## 🧪 Testando

### 1. Criar usuário
```bash
curl -X POST http://localhost:8000/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "email": "joao@test.com",
    "password": "MinhaSenh@123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "joao@test.com",
    "password": "MinhaSenh@123"
  }'
```

### 3. Criar pedido (requer token)
```bash
curl -X POST http://localhost:8000/orders/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{
    "items": [
      {
        "product_id": "PROD001",
        "product_name": "Produto A",
        "quantity": 2,
        "unit_price": 100.00
      }
    ]
  }'
```

## 🐛 Troubleshooting

### Erro: "Token não informado"
- Certifique-se de incluir o header `Authorization: Bearer <token>`

### Erro: "Cliente não encontrado"
- Execute `POST /clients/create/` para criar perfil

### Banco não inicia
```bash
docker-compose down
docker-compose up -d
```

## 📄 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).

⭐ **Star este projeto se ele te ajudou!** ⭐
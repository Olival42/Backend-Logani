# 📚 Documentação da API - Para Frontend

## 🎯 Visão Geral

Esta documentação explica como integrar o frontend com a API de Pagamento e Frete. O fluxo é simples e direto.

**URL Base:** `http://localhost:8000/api`

---

## 🔐 1. Autenticação

### Registro de Usuário

**Endpoint:** `POST /users/register/`

**Headers:** Não requer autenticação

**Request Body:**
```json
{
  "name": "João Silva",
  "email": "joao@example.com",
  "password": "MinhaSenh@123"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": "uuid-do-usuario",
    "name": "João Silva",
    "email": "joao@example.com"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_at": 1733059200
}
```

**Observações:**
- Senha deve ter: 8+ caracteres, 1 maiúscula, 1 número, 1 caractere especial
- Email deve ser válido e único

---

### Login

**Endpoint:** `POST /users/login/`

**Headers:** Não requer autenticação

**Request Body:**
```json
{
  "email": "joao@example.com",
  "password": "MinhaSenh@123"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid-do-usuario",
    "name": "João Silva",
    "email": "joao@example.com"
  },
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_at": 1733059200
}
```

**⚠️ Importante:**
- Salve o `access` token para usar nas requisições autenticadas
- Salve o `refresh` token para renovar o access token quando expirar
- Token expira em 1 hora (3600 segundos)

---

### Usar o Token (Todas as requisições protegidas)

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Exemplo em JavaScript:**
```javascript
fetch('http://localhost:8000/api/orders/my-orders/', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
})
```

---

### Refresh Token

**Endpoint:** `POST /users/refresh-token/`

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "access": "novo-access-token"
}
```

**Quando usar:**
- Quando o access token expirar (401 Unauthorized)
- Chamar este endpoint para obter novo access token
- Não precisa fazer login novamente

---

### Logout

**Endpoint:** `POST /users/logout/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "detail": "Logout realizado com sucesso"
}
```

**O que acontece:**
- Tokens são adicionados à blacklist
- Não podem mais ser usados para autenticação

---

## 👤 2. Cliente (Perfil do Usuário)

### Criar Cliente (Após registro)

**Endpoint:** `POST /clients/create/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "name": "João Silva",
  "cpf": "123.456.789-00",
  "phone": "11987654321",
  "mobile_phone": "11912345678",
  "address": {
    "address": "Rua das Flores",
    "number": "123",
    "complement": "Apto 45",
    "postal_code": "01234-567",
    "province": "Centro",
    "city": "São Paulo",
    "state": "SP"
  }
}
```

**Response (201 Created):**
```json
{
  "message": "Cliente criado com sucesso",
  "data": {
    "local_id": "uuid-do-cliente",
    "asaas_id": "cus_xxxxxxxxxxxxx",
    "name": "João Silva",
    "cpf": "123.456.789-00"
  }
}
```

**Observações:**
- CPF deve ser válido e único
- CPF será salvo no formato: `123.456.789-00`
- API cria cliente também no Asaas
- `asaas_id` é importante para pagamentos

---

## 📦 3. Pedido (Order)

### Criar Pedido

**Endpoint:** `POST /orders/create/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
   "items": [
     {
       "product_id": "PROD001",
       "product_name": "Produto A",
       "quantity": 2,
       "unit_price": 150.00
     },
     {
       "product_id": "PROD002",
       "product_name": "Produto B",
       "quantity": 1,
       "unit_price": 89.90
     }
   ],
   "notes": "Pedido especial"
}
```

**Response (201 Created):**
```json
{
  "message": "Pedido criado com sucesso",
  "data": {
    "order_id": "uuid-do-pedido",
    "external_reference": "ORD_20241201120000_ABC12345",
    "client": {
      "id": "uuid-cliente",
      "name": "João Silva"
    },
    "subtotal": 389.90,
    "total": 389.90,
    "total_items": 3,
    "status": "PENDING",
    "notes": "Pedido especial",
    "created_at": "2024-12-01T12:00:00Z",
    "updated_at": null,
    "confirmed_at": null
  }
}
```

**O que acontece:**
1. Sistema cria o pedido com status `PENDING`
2. Gera referência externa única: `ORD_20241201120000_ABC12345`
3. Calcula automaticamente: subtotal, total
4. Aguarda pagamento

---

### Consultar Pedido

**Endpoint:** `GET /orders/detail/{order_id}/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Pedido encontrado",
  "data": {
    "order_id": "uuid-do-pedido",
    "external_reference": "ORD_20241201120000_ABC12345",
    "client": {
      "id": "uuid-cliente",
      "name": "João Silva",
      "cpf": "123.456.789-00",
      "address": {...}
    },
    "items": [
      {
        "product_id": "PROD001",
        "product_name": "Produto A",
        "quantity": 2,
        "unit_price": 150.00,
        "total_price": 300.00
       }
     ],
     "subtotal": 389.90,
     "total": 389.90,
     "status": "CONFIRMED",
     "notes": "Pedido especial",
     "created_at": "2024-12-01T12:00:00Z",
     "confirmed_at": "2024-12-01T12:05:00Z"
  }
}
```

 **Status possíveis do pedido:**
 - `PENDING` - Aguardando pagamento
 - `CONFIRMED` - Confirmado (pagamento confirmado, aguardando recebimento na conta)
 - `PAID` - Pago e recebido (dinheiro na conta, última parcela no caso de parcelamento)
 - `PREPARING` - Em preparação (proprietário marcou manualmente)
 - `CANCELLED` - Cancelado

---

### Listar Pedidos do Cliente

**Endpoint:** `GET /orders/my-orders/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Encontrados 3 pedidos",
  "data": [
    {
      "order_id": "uuid-1",
      "external_reference": "ORD_20241201120000_ABC12345",
      "total": 404.90,
      "status": "CONFIRMED",
      "total_items": 3,
      "created_at": "2024-12-01T12:00:00Z"
    },
    {
      "order_id": "uuid-2",
      "external_reference": "ORD_20241201115000_DEF67890",
      "total": 250.00,
      "status": "DELIVERED",
      "total_items": 2,
      "created_at": "2024-12-01T11:50:00Z"
    }
  ],
  "count": 2
}
```

---

## 💳 4. Pagamento (Payment)

### ⚠️ ATENÇÃO: Ainda em Desenvolvimento

O módulo de PAGAMENTO está implementado mas **não tem views/endpoints públicos ainda**. 

**Para criar pagamentos, você pode usar temporariamente o CHECKOUT:**

---

## 🛒 5. Checkout (Link de Pagamento)

### Criar Checkout (Para Pedido)

**Endpoint:** `POST /checkouts/create/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "value": 404.90,
  "customer": "cus_xxxxxxxxxxxxx",
  "chargeTypes": ["DETACHED"],
  "minutesToExpire": 1440,
  "description": "Pedido ORD_20241201120000_ABC12345",
  "externalReference": "ORD_20241201120000_ABC12345",
  "paymentMethods": ["PIX", "CREDIT_CARD"],
  "successUrl": "https://seusite.com/success",
  "failureUrl": "https://seusite.com/failure",
  "items": [
    {
      "name": "Produto A",
      "value": 150.00,
      "quantity": 2
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "message": "Checkout criado com sucesso",
  "data": {
    "local_id": "uuid-do-checkout",
    "asaas_id": "cko_xxxxxxxxxxxxx",
    "checkout_url": "https://sandbox.asaas.com/checkout/cko_xxxxx",
    "name": "Checkout DETACHED - João Silva",
    "value": 404.90,
    "status": "PENDING",
    "expires_at": "2024-12-02T12:00:00Z"
  }
}
```

**Como usar:**
1. Crie o pedido primeiro
2. Use o `externalReference` do pedido
3. Use o `customer` (asaas_id do cliente)
4. Redirecione o usuário para `checkout_url`

---

### Consultar Checkout

**Endpoint:** `GET /checkouts/detail/{checkout_id}/`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Checkout encontrado",
  "data": {
    "id": "uuid-do-checkout",
    "asaas_id": "cko_xxxxxxxxxxxxx",
    "name": "Checkout DETACHED - João Silva",
    "value": 404.90,
    "status": "PAID",
    "checkout_url": "https://sandbox.asaas.com/checkout/cko_xxxxx",
    "client_name": "João Silva",
    "client_cpf": "123.456.789-00",
    "created_at": "2024-12-01T12:00:00Z",
    "expires_at": "2024-12-02T12:00:00Z"
  }
}
```

---

## 🔔 6. Webhooks (Callbacks Automáticos)

### ⚠️ IMPORTANTE: Endpoint de Webhook

**Endpoint:** `POST /webhooks/receive/`

**Headers:** Sem autenticação (público)

**Descrição:** Este endpoint é chamado AUTOMATICAMENTE pelo Asaas quando ocorre um evento de pagamento. Você NÃO precisa chamá-lo manualmente.

**Payload que o Asaas envia (exemplo):**
```json
{
  "event": "PAYMENT_CONFIRMED",
  "payment": {
    "id": "pay_xxxxxxxxxxxxx",
    "customer": "cus_xxxxxxxxxxxxx",
    "value": 404.90,
    "status": "CONFIRMED",
    "billingType": "PIX",
    "externalReference": "ORD_20241201120000_ABC12345",
    "paymentDate": "2024-12-01T12:05:00Z"
  }
}
```

**O que acontece automaticamente:**
1. Sistema recebe o webhook
2. Atualiza o Payment com o status correto
3. Para pagamentos à vista (PIX): 
   - `PAYMENT_CONFIRMED` → Order vai para `CONFIRMED`
   - `PAYMENT_RECEIVED` → Order vai para `PAID`
4. Para pagamentos parcelados: 
   - Primeira parcela confirmada (`PAYMENT_CONFIRMED`) → Order vai para `CONFIRMED`
   - Última parcela recebida (`PAYMENT_RECEIVED`) → Order vai para `PAID`
5. Tudo automático! 🎉

---

## 🔄 7. Fluxo Completo de Compra

### Passo a Passo Completo

```javascript
// PASSO 1: Login
const loginResponse = await fetch('http://localhost:8000/api/users/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'joao@example.com',
    password: 'MinhaSenh@123'
  })
});

const { access, refresh } = await loginResponse.json();
const accessToken = access;

// PASSO 2: Criar Pedido
const orderResponse = await fetch('http://localhost:8000/api/orders/create/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  },
  body: JSON.stringify({
    items: [
      {
        product_id: 'PROD001',
        product_name: 'Produto A',
        quantity: 2,
        unit_price: 150.00
      }
    ]
  })
});

const { data: order } = await orderResponse.json();
// order.order_id
// order.external_reference
// order.total

// PASSO 3: Criar Checkout (Link de Pagamento)
const checkoutResponse = await fetch('http://localhost:8000/api/checkouts/create/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  },
  body: JSON.stringify({
    value: order.total,
    customer: 'cus_xxxxxxxxxxxxx',  // asaas_id do cliente
    chargeTypes: ['DETACHED'],
    minutesToExpire: 1440,
    description: `Pedido ${order.external_reference}`,
    externalReference: order.external_reference,
    paymentMethods: ['PIX', 'CREDIT_CARD'],
    successUrl: 'https://seusite.com/success',
    failureUrl: 'https://seusite.com/failure'
  })
});

const { data: checkout } = await checkoutResponse.json();
// checkout.checkout_url <- URL para cliente pagar

// PASSO 4: Redirecionar Cliente para Pagamento
window.location.href = checkout.checkout_url;

// PASSO 5: Cliente paga no Asaas
// (redirecionado para a página do Asaas)

// PASSO 6: Webhook AUTOMÁTICO (você não precisa fazer nada)
// Asaas envia POST para /webhooks/receive/
// Sistema atualiza automaticamente o status do pedido

// PASSO 7: Verificar Status do Pedido
const orderStatus = await fetch(`http://localhost:8000/api/orders/detail/${order.order_id}/`, {
  headers: {
    'Authorization': `Bearer ${accessToken}`
  }
});

const { data: orderData } = await orderStatus.json();
// orderData.status pode ser: CONFIRMED, PAID, etc.
```

---

## 📊 8. Status e Estados

### Status do Pedido (Order)

| Status | Descrição | Quando Acontece |
|--------|-----------|----------------|
| `PENDING` | Aguardando pagamento | Pedido criado, aguardando pagamento |
| `CONFIRMED` | Confirmado | Pagamento confirmado (ainda aguardando liquidação) |
| `PAID` | Pago e recebido | Dinheiro na conta bancária |
| `PREPARING` | Em preparação | Proprietário marcou manualmente |
| `CANCELLED` | Cancelado | Cancelamento manual ou estorno |

**Detalhes:**
- **Pagamento à vista (PIX):** 
  - `PENDING` → `CONFIRMED` (webhook PAYMENT_CONFIRMED) → `PAID` (webhook PAYMENT_RECEIVED)
- **Pagamento parcelado:**
  - `PENDING` → `CONFIRMED` (1ª parcela confirmada) → `PAID` (última parcela recebida)

### Status do Payment (via webhook)

| Status | Descrição | Quando Acontece |
|--------|-----------|----------------|
| `PENDING` | Aguardando pagamento | Checkout criado |
| `PAID` | Pago | Webhook PAYMENT_CONFIRMED |
| `RECEIVED` | Recebido | Webhook PAYMENT_RECEIVED (PIX) |
| `REFUNDED` | Estornado | Webhook PAYMENT_REFUNDED |
| `CANCELLED` | Cancelado | Webhook PAYMENT_CANCELED |
| `FAILED` | Falhou | Webhook PAYMENT_FAILED |

---

## 🔗 9. Lista Completa de Endpoints

### Autenticação
```
POST   /users/register/          # Registro
POST   /users/login/             # Login
POST   /users/logout/            # Logout
POST   /users/refresh-token/     # Renovar token
```

### Cliente
```
POST   /clients/create/          # Criar perfil
GET    /clients/detail/{id}/     # Ver perfil
PUT    /clients/update/{id}/     # Atualizar perfil
```

### Pedido
```
POST   /orders/create/           # Criar pedido
GET    /orders/detail/{id}/       # Ver pedido
GET    /orders/my-orders/        # Listar meus pedidos
POST   /orders/confirm/{id}/     # Confirmar pedido
POST   /orders/cancel/{id}/      # Cancelar pedido
```

### Checkout/Pagamento
```
POST   /checkouts/create/        # Criar link de pagamento
GET    /checkouts/detail/{id}/    # Ver checkout
GET    /checkouts/list/          # Listar checkouts
POST   /checkouts/cancel/{id}/    # Cancelar checkout
```

### Webhooks
```
POST   /webhooks/receive/        # Receber notificações (automático)
POST   /webhooks/create/         # Criar webhook (configuração)
GET    /webhooks/list/           # Listar webhooks
GET    /webhooks/detail/{id}/    # Ver webhook
PUT    /webhooks/update/{id}/    # Atualizar webhook
DELETE /webhooks/delete/{id}/    # Deletar webhook
```

---

## ⚠️ 10. Observações Importantes

### Campos obrigatórios

**Create Order:**
- ✅ `items` (pelo menos 1 item)

**Create Checkout:**
- ✅ `value`
- ✅ `customer` (asaas_id do cliente)
- ✅ `chargeTypes`
- ✅ `minutesToExpire`

### Validações

**Email:**
- Formato válido: `email@dominio.com`
- Único no sistema

**Senha:**
- Mínimo 8 caracteres
- Pelo menos 1 maiúscula
- Pelo menos 1 número
- Pelo menos 1 caractere especial

**CPF:**
- Formato: `123.456.789-00` ou `12345678900`
- Válido segundo algoritmo
- Único no sistema

**Valores:**
- Sempre positivos
- Subtotal = soma dos itens
- Total = subtotal

---

## 🧪 11. Exemplos Práticos

### Exemplo 1: E-commerce Completo

```javascript
// 1. Usuário faz login
const login = await login(email, password);
const token = login.access;

// 2. Usuário adiciona produtos ao carrinho (frontend)
const cart = {
  items: [
    { id: 'PROD001', name: 'Produto A', qty: 2, price: 150.00 },
    { id: 'PROD002', name: 'Produto B', qty: 1, price: 89.90 }
  ]
};

// 3. Criar pedido no backend
const order = await createOrder(token, {
  items: cart.items
});

// 5. Criar checkout (link de pagamento)
const checkout = await createCheckout(token, {
  value: order.total,
  customer: user.asaas_id,
  externalReference: order.external_reference,
  paymentMethods: ['PIX', 'CREDIT_CARD']
});

// 6. Redirecionar para pagamento
window.location.href = checkout.checkout_url;

// 7. Cliente paga no Asaas
// ...

// 8. Sistema recebe webhook automaticamente
// Webhook atualiza: order.status = CONFIRMED

// 9. Frontend verifica status
const updatedOrder = await getOrder(token, order.order_id);
if (updatedOrder.status === 'CONFIRMED') {
  showSuccessMessage();
}
```

---

### Exemplo 2: Verificar Status do Pedido

```javascript
// Polling - verificar status a cada X segundos
const pollOrderStatus = async (orderId, token) => {
  const response = await fetch(`http://localhost:8000/api/orders/detail/${orderId}/`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const { data } = await response.json();
  
  // Atualizar UI baseado no status
   switch(data.status) {
     case 'PENDING':
       showPaymentButton();
       break;
     case 'CONFIRMED':
       showConfirmedMessage();
       break;
     case 'PREPARING':
       showPreparingMessage();
       break;
     case 'CANCELLED':
       showCancelledMessage();
       break;
   }
};

// Verificar a cada 5 segundos
setInterval(() => pollOrderStatus(orderId, token), 5000);
```

---

## 📱 12. Fluxo de Estorno (Opcional)

### Solicitar Estorno (para pedidos pagos)

```javascript
// 1. Cliente solicita estorno
const refundRequest = {
  order_id: 'uuid-do-pedido',
  reason: 'Não recebi o produto'
};

// 2. Backend processa estorno
const refund = await refundPayment(token, {
  external_reference: order.external_reference,
  value: order.total,
  description: refundRequest.reason
});

// 3. Sistema atualiza automaticamente:
// - Payment.status = REFUNDED
// - Order.status = CANCELLED

// 4. Verificar resultado
const updatedOrder = await getOrder(token, order.order_id);
// updatedOrder.status = CANCELLED
```

---

## 🎨 13. Tratamento de Erros

### Erros Comuns

**401 Unauthorized:**
```json
{
  "detail": "Token não informado"
}
```
**Solução:** Adicione o header `Authorization: Bearer <token>`

**400 Bad Request:**
```json
{
  "email": ["Email inválido"],
  "password": ["A senha precisa ter pelo menos 8 caracteres"]
}
```
**Solução:** Corrija os campos mencionados

**404 Not Found:**
```json
{
  "error": "Pedido não encontrado"
}
```
**Solução:** Verifique se o ID está correto

---

## 🚀 14. Quick Start

### Base URL
```
http://localhost:8000/api
```

### Passos Iniciais

1. **Registrar/Login:**
```bash
POST /users/register/
POST /users/login/
```

2. **Criar Perfil:**
```bash
POST /clients/create/
```

3. **Criar Pedido:**
```bash
POST /orders/create/
```

4. **Criar Pagamento:**
```bash
POST /checkouts/create/
```

5. **Redirecionar para pagamento:**
```javascript
window.location.href = checkout.checkout_url;
```

6. **Verificar status:**
```bash
GET /orders/detail/{order_id}/
```

**🎯 Esta documentação foi criada especificamente para facilitar a integração do frontend!**


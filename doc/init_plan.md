# 📋 **ПЛАН РАЗРАБОТКИ SECURE CHAT PROXY**

## 🎯 **ОПИСАНИЕ ПРОЕКТА**

### **Что мы делаем:**
Разрабатываем безопасный прокси-сервер и виджет чата для e-commerce платформ, который позволяет публичным пользователям взаимодействовать с AI-агентом через n8n, сохраняя при этом полную историю диалогов и обеспечивая безопасность архитектуры.

### **Зачем мы это делаем:**
1. **Скрытие инфраструктуры** - защита n8n webhook URL и credentials от публичного доступа
2. **Контроль доступа** - управление тем, какие данные может запрашивать пользователь
3. **Аналитика и история** - сохранение всех взаимодействий для анализа и улучшения
4. **Масштабируемость** - возможность обслуживать множество сайтов через один сервис
5. **Персонализация** - возможность идентификации вернувшихся пользователей

## 🏗️ **АРХИТЕКТУРА СИСТЕМЫ**

```
┌─────────────────────────────────────────────────────────────┐
│                     E-COMMERCE WEBSITES                      │
├─────────────────────────────────────────────────────────────┤
│  Site A    │    Site B    │    Site C    │    Site N...    │
└──────┬──────────────┬──────────────┬──────────────┬────────┘
       │              │              │              │
       └──────────────┴──────┬──────┴──────────────┘
                              │ HTTPS/WSS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CHAT WIDGET (React)                       │
├─────────────────────────────────────────────────────────────┤
│ • Embedded iframe                                            │
│ • Session management via cookies                             │
│ • SSE connection for streaming                               │
│ • Auto-reconnect logic                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ API Calls
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 PROXY SERVER (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│ • Session Management      │ • Rate Limiting                 │
│ • JWT Generation          │ • Request Validation            │
│ • SSE Streaming           │ • Analytics Collection          │
│ • Site Origin Validation  │ • Error Handling               │
└──────────────────────────┬──────────────────────────────────┘
                           │ Internal API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     n8n WORKFLOW                             │
├─────────────────────────────────────────────────────────────┤
│ • Chat Trigger (SSE enabled)                                │
│ • AI Agent Processing                                        │
│ • Tools & Integrations                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL │ Redis Cache │ S3/MinIO Storage │ Vector DB     │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 **КАК ВСЁ РАБОТАЕТ**

### **1. Инициализация сессии:**
- Пользователь заходит на e-commerce сайт
- Загружается chat widget (React приложение в iframe)
- Widget запрашивает новую сессию у proxy server
- Создается уникальный session_id, сохраняется в secure cookie
- Генерируется fingerprint браузера для дополнительной идентификации

### **2. Обработка сообщений:**
- Пользователь отправляет сообщение через widget
- Widget отправляет POST запрос на proxy с session_id
- Proxy валидирует origin сайта и сессию
- Proxy генерирует JWT токен с метаданными
- Proxy отправляет запрос в n8n с JWT и контекстом
- n8n обрабатывает через AI agent и возвращает SSE stream
- Proxy проксирует SSE stream обратно в widget

### **3. Управление контекстом:**
- Proxy загружает историю чата из БД по session_id
- Добавляет контекст сайта (domain, page_url, user_agent)
- Обогащает метаданными (время, геолокация по IP)
- Передает полный контекст в n8n для персонализации

### **4. Безопасность:**
- CORS политики для разрешенных доменов
- Rate limiting по IP и session_id
- Валидация и санитизация входящих данных
- Шифрование sensitive данных в БД
- Автоматическая ротация JWT секретов

## 📁 **СТРУКТУРА МОНОРЕПОЗИТОРИЯ**

```
chat-proxy-system/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                 # CI/CD pipeline
│   │   ├── deploy-staging.yml
│   │   └── deploy-production.yml
│   └── dependabot.yml
│
├── apps/
│   ├── proxy-server/              # FastAPI Backend
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── v1/
│   │   │   │   │   ├── endpoints/
│   │   │   │   │   │   ├── chat.py
│   │   │   │   │   │   ├── session.py
│   │   │   │   │   │   ├── analytics.py
│   │   │   │   │   │   └── health.py
│   │   │   │   │   └── router.py
│   │   │   │   └── deps.py
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   ├── session.py
│   │   │   │   └── exceptions.py
│   │   │   ├── services/
│   │   │   │   ├── n8n_client.py
│   │   │   │   ├── jwt_service.py
│   │   │   │   ├── rate_limiter.py
│   │   │   │   └── analytics.py
│   │   │   ├── models/
│   │   │   │   ├── chat.py
│   │   │   │   ├── session.py
│   │   │   │   └── analytics.py
│   │   │   ├── db/
│   │   │   │   ├── base.py
│   │   │   │   ├── session.py
│   │   │   │   └── migrations/
│   │   │   ├── middleware/
│   │   │   │   ├── cors.py
│   │   │   │   ├── rate_limit.py
│   │   │   │   └── logging.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── alembic/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── pyproject.toml
│   │
│   ├── chat-widget/               # React Frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ChatWindow/
│   │   │   │   ├── MessageList/
│   │   │   │   ├── InputArea/
│   │   │   │   └── ConnectionStatus/
│   │   │   ├── hooks/
│   │   │   │   ├── useSSE.ts
│   │   │   │   ├── useSession.ts
│   │   │   │   └── useChat.ts
│   │   │   ├── services/
│   │   │   │   ├── api.ts
│   │   │   │   ├── sse.ts
│   │   │   │   └── storage.ts
│   │   │   ├── utils/
│   │   │   │   ├── fingerprint.ts
│   │   │   │   └── sanitizer.ts
│   │   │   ├── types/
│   │   │   ├── App.tsx
│   │   │   └── index.tsx
│   │   ├── public/
│   │   │   └── embed.js          # Скрипт для встраивания
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── vite.config.ts
│   │
│   └── admin-dashboard/           # Опциональный админ интерфейс
│       ├── src/
│       └── ...
│
├── packages/                      # Shared packages
│   ├── types/                    # TypeScript типы
│   │   ├── src/
│   │   │   ├── chat.ts
│   │   │   ├── session.ts
│   │   │   └── api.ts
│   │   └── package.json
│   │
│   └── utils/                    # Общие утилиты
│       ├── src/
│       │   ├── validators.ts
│       │   └── constants.ts
│       └── package.json
│
├── infrastructure/               # IaC и конфигурации
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.dev.yml
│   │   └── docker-compose.prod.yml
│   ├── kubernetes/
│   │   ├── base/
│   │   ├── overlays/
│   │   └── kustomization.yaml
│   ├── terraform/
│   │   ├── modules/
│   │   ├── environments/
│   │   └── main.tf
│   └── nginx/
│       └── nginx.conf
│
├── scripts/                      # Утилиты разработки
│   ├── setup.sh
│   ├── migrate.sh
│   ├── generate-embed.js
│   └── test-integration.sh
│
├── docs/                         # Документация
│   ├── architecture/
│   │   ├── README.md
│   │   ├── security.md
│   │   └── diagrams/
│   ├── api/
│   │   └── openapi.yaml
│   ├── deployment/
│   └── integration-guide.md
│
├── .env.example
├── .gitignore
├── turbo.json                    # Turborepo конфигурация
├── package.json                  # Root package.json
├── pnpm-workspace.yaml          # PNPM workspace
└── README.md
```

## 🔧 **КЛЮЧЕВЫЕ КОМПОНЕНТЫ**

### **Proxy Server (FastAPI):**
- **Session Manager** - управление жизненным циклом сессий
- **JWT Service** - генерация и валидация токенов
- **N8N Client** - взаимодействие с n8n через SSE
- **Rate Limiter** - защита от spam и DDoS
- **Analytics Collector** - сбор метрик использования
- **CORS Handler** - управление доступом с разных доменов

### **Chat Widget (React):**
- **SSE Connection Manager** - управление streaming соединением
- **Message Queue** - буферизация сообщений при разрывах
- **Session Storage** - локальное хранение контекста
- **Auto-reconnect** - восстановление соединения
- **Fingerprinting** - идентификация устройства
- **Responsive UI** - адаптивный интерфейс

### **Data Layer:**
- **PostgreSQL** - основное хранилище (сессии, история, аналитика)
- **Redis** - кэш сессий и rate limiting
- **S3/MinIO** - хранение файлов и медиа
- **Vector DB** - опционально для semantic search

## 🚀 **ЭТАПЫ РЕАЛИЗАЦИИ**

### **Phase 1: MVP (2-3 недели)**
- Базовый proxy server с JWT
- Простой chat widget
- Интеграция с n8n
- Сохранение истории в PostgreSQL

### **Phase 2: Security (1-2 недели)**
- Rate limiting
- CORS policies
- Session management
- Input validation

### **Phase 3: Production Ready (2-3 недели)**
- SSE streaming optimization
- Error handling & retry logic
- Monitoring & logging
- Docker & K8s configs

### **Phase 4: Advanced Features (2-4 недели)**
- Analytics dashboard
- Multi-site management
- A/B testing support
- Custom branding options

## 📊 **МЕТРИКИ УСПЕХА**

- **Latency** < 100ms для первого байта
- **Uptime** > 99.9%
- **Concurrent users** > 10,000
- **Message throughput** > 1000 msg/sec
- **Zero security breaches**
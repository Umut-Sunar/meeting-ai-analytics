# Meeting AI Analytics System - Monorepo

Bu proje, AI destekli toplantı analiz sistemi için monorepo yapısını içerir.

## 📁 Proje Yapısı

```
.
├── web/              # Web uygulaması (React + TypeScript + Vite)
├── backend/          # Backend API servisleri 
├── desktop/
│   ├── macos/        # macOS desktop uygulaması
│   └── windows/      # Windows desktop uygulaması
├── infra/            # Infrastructure ve deployment scripts
└── .cursor/          # Cursor IDE konfigürasyonları
```

## 🚀 Çalışma Komutları

### Web Uygulaması
```bash
cd web
npm install
npm run dev
```

### Backend
```bash
cd backend
# Python dependency management ile (uv/poetry)
uv install  # veya poetry install
```

#### Health Check Endpoints
Backend provides health check endpoints for monitoring and k8s/ecs probes:

- **`GET /api/v1/health`** - Simple health check for k8s/ecs probes
  ```json
  {
    "redis": "ok|down",
    "storage": "ok|down|unavailable", 
    "version": "0.1.0"
  }
  ```

- **`GET /api/v1/health/detailed`** - Detailed health check with timestamp
  ```json
  {
    "status": "healthy|unhealthy",
    "timestamp": "2025-08-31T01:00:00.000Z",
    "version": "0.1.0",
    "services": {
      "database": "healthy|unhealthy",
      "redis": "healthy|unhealthy", 
      "storage": "healthy|unhealthy|unavailable"
    }
  }
  ```

- **`GET /api/v1/ping`** - Simple ping endpoint

### Desktop - macOS
```bash
cd desktop/macos
# Xcode projesi açmak için
open *.xcodeproj
```

### Desktop - Windows
```bash
cd desktop/windows
# Visual Studio solution dosyası
```

## 📋 Özellikler

- **Dashboard**: Genel bakış ve ana metrikler
- **Toplantı Analizi**: AI destekli toplantı özetleri ve analitikler
- **Ekip Yönetimi**: Kullanıcı rolleri ve performans takibi
- **Desktop Apps**: Native macOS ve Windows uygulamaları
- **API Backend**: RESTful API servisleri

## 🛠️ Geliştirme

Her modül kendi bağımlılıklarını yönetir. Detaylı kurulum talimatları için ilgili klasörlerdeki README dosyalarını kontrol edin.

# Backend API

Meeting AI Analytics System'in FastAPI backend servisi.

## 🚀 Kurulum ve Çalıştırma

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- MinIO (S3-compatible storage)
- Docker & Docker Compose

### Geliştirme Ortamı

1. **Virtual environment oluştur:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

2. **Bağımlılıkları yükle:**
```bash
pip install -r requirements.txt
pip install passlib[bcrypt]  # Password hashing için
```

3. **Docker servisleri başlat:**
```bash
# Ana dizinden
docker-compose -f docker-compose.dev.yml up -d postgres redis minio
```

4. **Environment dosyası oluştur:**
```bash
cp env.example .env
# .env dosyasını düzenle
```

5. **Database migration:**
```bash
# Yeni migration oluştur (şema değişiklikleri sonrası)
alembic revision --autogenerate -m "Add comprehensive schema with tenant isolation"

# Migration'ları uygula
alembic upgrade head
```

6. **Seed data oluştur:**
```bash
python seeds/initial_data.py
```

7. **Backend'i başlat:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Health Check
- `GET /api/v1/health` - Sistem sağlık kontrolü
- `GET /api/v1/ping` - Basit ping testi

### Meetings
- `GET /api/v1/meetings` - Toplantı listesi (filtreleme ve sayfalama)
- `GET /api/v1/meetings/{id}` - Tek toplantı detayı
- `POST /api/v1/meetings` - Yeni toplantı oluştur
- `PUT /api/v1/meetings/{id}` - Toplantı güncelle
- `DELETE /api/v1/meetings/{id}` - Toplantı sil

## 📚 API Dokümantasyonu

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🗄️ Database

### Multi-Tenant Şema
Tüm tablolar `tenant_id` (UUID) içerir ve Row Level Security (RLS) hazırlığı yapılmıştır.

#### Core Tables
- **users** - Kullanıcılar (tenant_id ile izole)
- **teams** - Takımlar ve üyelikler
- **meetings** - Toplantılar ve metadata
- **subscriptions** - Abonelik yönetimi
- **quotas** - Kullanım kotaları

#### Audio & Transcript Tables
- **meeting_streams** - Audio stream metadata
- **audio_blobs** - S3'teki audio parçaları
- **transcripts** - Konuşma transkriptleri
- **ai_messages** - AI sohbet geçmişi

#### Skills & Analytics
- **skills** - Yetenek tanımları
- **skill_assessments** - Performans değerlendirmeleri
- **analytics_daily** - Günlük analitik özetler
- **audit_logs** - Sistem işlem kayıtları

#### Device & Integration
- **devices** - Masaüstü istemci kayıtları
- **api_keys** - API erişim anahtarları
- **webhooks** - Webhook entegrasyonları
- **documents** - Kullanıcı dosyaları

### Migration
```bash
# Yeni migration oluştur
alembic revision --autogenerate -m "Description"

# Migration'ları uygula
alembic upgrade head

# Migration geçmişi
alembic history

# Belirli bir revision'a dön
alembic downgrade <revision>
```

### Seed Data
```bash
# Initial test data oluştur
python seeds/initial_data.py

# Oluşturulan veriler:
# - 1 tenant
# - 2 user (admin@meetingai.dev / member@meetingai.dev)
# - 1 team
# - 1 meeting
# - 2 skill + assessments
# - 1 device registration
# - 1 subscription + quota
```

## 🔧 Geliştirme

### Proje Yapısı
```
backend/
├── app/
│   ├── database/        # Database bağlantı ve konfigürasyon
│   ├── models/          # SQLAlchemy modelleri
│   │   ├── enums.py     # Tüm enum tanımları
│   │   ├── users.py     # User modeli
│   │   ├── teams.py     # Team ve TeamMember
│   │   ├── meetings.py  # Meeting, Stream, Audio, Transcript
│   │   ├── subscriptions.py # Plan, Subscription, Quota
│   │   ├── skills.py    # Skill ve SkillAssessment
│   │   ├── devices.py   # Device kayıtları
│   │   ├── documents.py # Document yönetimi
│   │   └── audit.py     # Audit, Analytics, API keys
│   ├── routers/         # FastAPI route'ları
│   ├── schemas/         # Pydantic şemaları
│   └── main.py          # Ana uygulama
├── alembic/             # Database migration'ları
├── seeds/               # Test verileri
│   └── initial_data.py  # Seed data scripti
├── tests/               # Test dosyaları
├── requirements.txt     # Python bağımlılıkları
└── Sprint-3-Commands.md # Sprint-3 komutları
```

### Enum Kullanımı
```python
from app.models.enums import UserRole, MeetingStatus, SkillCategory

# Model tanımında
role = Column(Enum(UserRole), default=UserRole.USER)
status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
```

### Tenant Isolation
```python
# Her model tenant_id ile
class User(Base):
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
        Index('ix_users_tenant_id', 'tenant_id'),
    )
```

### Code Style
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/

# Type check
mypy app/
```

## 🐳 Docker Servisleri

Docker Compose ile şu servisler çalıştırılır:

- **PostgreSQL**: Ana veritabanı (port 5432)
- **Redis**: Cache ve session store (port 6379)
- **MinIO**: Object storage (port 9000, console 9001)
- **pgAdmin**: PostgreSQL web arayüzü (port 5050)

### Erişim Bilgileri
- **PostgreSQL**: `meeting_ai` / `dev_password_123` / `meeting_ai_db`
- **Redis**: password: `dev_redis_password`
- **MinIO**: `minioadmin` / `dev_minio_password_123`
- **pgAdmin**: `admin@meeting-ai.dev` / `admin_password_123`

## 🧪 Test

```bash
# Tüm testleri çalıştır
pytest

# Coverage ile
pytest --cov=app

# Belirli test
pytest tests/test_meetings.py
```

## 📊 API Kullanım Örnekleri

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Toplantı Listesi
```bash
curl "http://localhost:8000/api/v1/meetings?page=1&per_page=10"
```

### Toplantı Oluştur
```bash
curl -X POST http://localhost:8000/api/v1/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sprint Planning",
    "date": "2024-08-26T10:00:00Z",
    "duration": 60,
    "participant_ids": ["user1", "user2"]
  }'
```

## 🔐 Multi-Tenant Security

### Row Level Security (RLS) Hazırlığı
Tüm tablolar `tenant_id` ile hazırlanmıştır. Gelecek sprintlerde RLS politikaları eklenecek:

```sql
-- Örnek RLS policy (gelecekte uygulanacak)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_tenant_policy ON users 
    FOR ALL TO authenticated_user 
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### Index Stratejisi
- Tüm tenant_id kolonları indexli
- Composite indexler: (tenant_id, frequently_queried_column)
- Foreign key indexleri mevcut
- Performance için compound indexler

## 📈 Sonraki Adımlar

1. **RLS Politikalarını Aktif Et**
2. **API Endpoint'lerini Database'e Bağla**
3. **Tenant Context Middleware**
4. **JWT Authentication**
5. **Real-time WebSocket Support**
6. **File Upload/Storage Integration**
7. **AI Integration (Speech-to-Text, Summarization)**
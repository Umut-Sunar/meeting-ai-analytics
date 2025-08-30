# 🚀 Analytics System Başlatma Yönergeleri

Bu dosya, Cursor açtığınızda analytics system'i JWT token ile tamamen çalışır halde başlatmak için gereken tüm terminal komutlarını içerir.

## 📋 Hızlı Başlatma Sırası

### 1. Proje Dizinine Git
```bash
cd /Users/doganumutsunar/analytics-system
```
**Açıklama**: Ana proje dizinine geçer

### 2. Redis Çakışmalarını Temizle
```bash
make redis-cleanup
```
**Açıklama**: Varsa tüm Redis instance'larını durdurur (Docker + host)

### 3. Redis Şifresini Ayarla
```bash
export REDIS_PASSWORD=dev_redis_password
```
**Açıklama**: Redis şifresi environment variable'ını ayarlar

### 4. Docker Servislerini Başlat
```bash
docker compose -f docker-compose.dev.yml up -d
```
**Açıklama**: Redis, PostgreSQL, MinIO ve PgAdmin'i Docker'da başlatır

### 5. Servislerin Hazır Olmasını Bekle
```bash
sleep 5
```
**Açıklama**: Docker container'ların tamamen başlaması için bekler

### 6. Redis Bağlantısını Test Et
```bash
redis-cli -a $REDIS_PASSWORD ping
```
**Açıklama**: Redis'in şifreyle erişilebilir olduğunu doğrular (PONG dönmeli)

### 7. Backend Dizinine Git ve Virtual Environment Aktif Et
```bash
cd backend && source venv/bin/activate
```
**Açıklama**: Backend dizinine geçer ve Python sanal ortamını aktif eder

### 8. Backend Sunucusunu Başlat
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
**Açıklama**: FastAPI backend sunucusunu başlatır (auto-reload ile)

---

## 🎯 Tek Komutla Başlatma (Alternatif)

Eğer tek komutla başlatmak isterseniz:

```bash
cd /Users/doganumutsunar/analytics-system && export USE_DOCKER_REDIS=1 && export REDIS_PASSWORD=dev_redis_password && ./start_system.sh
```

---

## ✅ Başarı Kontrolleri

### Redis Durumu Kontrolü
```bash
make redis-conflict-check
```
**Beklenen Çıktı**: Sadece Docker Redis çalışıyor olmalı
```
🔍 Checking for Redis conflicts...
Port 6379 usage:
COMMAND    PID           USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
com.docke 1996 doganumutsunar  162u  IPv6 0x3033e6bdfd85ca98      0t0  TCP *:6379 (LISTEN)

Redis processes:
No host Redis processes found

Docker Redis status:
NAMES              STATUS
meeting-ai-redis   Up 8 seconds (healthy)
```

### Backend Health Kontrolü
```bash
curl http://localhost:8000/api/v1/health
```
**Beklenen Çıktı**: 
```json
{"status":"healthy","timestamp":"2025-08-31T01:54:50.071548","version":"0.1.0","services":{"database":"healthy","redis":"healthy","storage":"healthy"}}
```

### JWT Token Test (Yeni Terminal Açın)
```bash
cd /Users/doganumutsunar/analytics-system
JWT_TOKEN=$(cat CURRENT_JWT_TOKEN.txt)
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/v1/meetings
```
**Beklenen Çıktı**: Meeting listesi JSON formatında
```json
{"meetings":[{"title":"Q3 Product Strategy Sync","date":"2024-07-22T10:00:00Z","duration":45,"id":"m1",...}],"total":2,"page":1,"per_page":10,"has_next":false,"has_prev":false}
```

---

## 🔑 JWT Token Üretme

### Yeni JWT Token Oluştur
```bash
cd backend && source venv/bin/activate
python create_correct_jwt.py
```
**Açıklama**: 
- Backend'in kendi güvenlik fonksiyonlarını kullanarak RS256 algoritması ile JWT token üretir
- Token otomatik olarak `CURRENT_JWT_TOKEN.txt` dosyasına kaydedilir
- Token 24 saat geçerlidir
- Test kullanıcısı: `test-user-001`, email: `test@example.com`

### Token Bilgilerini Kontrol Et
```bash
# Token'ı görüntüle
cat CURRENT_JWT_TOKEN.txt

# Token'ın geçerlilik süresini ve kullanıcı bilgilerini kontrol et
cd backend && python -c "
from app.core.security import decode_jwt_token
from datetime import datetime
token = open('../CURRENT_JWT_TOKEN.txt').read().strip()
claims = decode_jwt_token(token)
print('JWT Token Claims:')
print(f'  User ID: {claims.user_id}')
print(f'  Tenant ID: {claims.tenant_id}')
print(f'  Email: {claims.email}')
print(f'  Role: {claims.role}')
print(f'  Expires: {datetime.fromtimestamp(claims.exp).strftime(\"%Y-%m-%d %H:%M:%S\")}')
print(f'  Audience: {claims.aud}')
print(f'  Issuer: {claims.iss}')
"
```

### Erişilebilir Meeting ID'leri
```bash
# Mevcut JWT token ile erişilebilir meeting'leri listele
JWT_TOKEN=$(cat CURRENT_JWT_TOKEN.txt)
curl -s -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/v1/meetings | python -c "
import sys, json
data = json.load(sys.stdin)
print('Available Meeting IDs:')
for meeting in data['meetings']:
    print(f'  ID: {meeting[\"id\"]} - {meeting[\"title\"]}')
    print(f'      Date: {meeting[\"date\"]}')
    print(f'      Duration: {meeting[\"duration\"]} minutes')
    print()
"
```

**🔑 Önemli**: 
- JWT token **tüm meeting'lere erişim** sağlar (development modunda)
- Production'da tenant_id ve user_id bazlı filtreleme yapılacak
- Şu anda erişilebilir meeting ID'leri: **m1**, **m2**

### WebSocket Endpoint'leri
JWT token ile kullanabileceğiniz WebSocket endpoint'leri:

```bash
# Transcript alma (frontend için)
ws://localhost:8000/ws/transcript/m1
# Authorization: Bearer <JWT_TOKEN> header ile

# Audio ingest (MacClient için)
ws://localhost:8000/ws/ingest/meetings/m1?source=mic
ws://localhost:8000/ws/ingest/meetings/m1?source=sys
# Authorization: Bearer <JWT_TOKEN> header ile

# Meeting subscriber (genel dinleme)
ws://localhost:8000/ws/meetings/m1?token=<JWT_TOKEN>
```

**Örnek Frontend Kullanımı:**
```javascript
const token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."; // JWT token
const ws = new WebSocket("ws://localhost:8000/ws/transcript/m1", [], {
  headers: {
    "Authorization": `Bearer ${token}`
  }
});
```

### Özel JWT Token Oluştur
```bash
cd backend && python -c "
from app.core.security import create_dev_jwt_token
token = create_dev_jwt_token(
    user_id='custom-user-123',
    tenant_id='custom-tenant-456', 
    email='custom@example.com',
    role='admin'
)
print('Custom Token:', token)
with open('../CURRENT_JWT_TOKEN.txt', 'w') as f:
    f.write(token)
print('Token saved to CURRENT_JWT_TOKEN.txt')
"
```

---

## 🔧 Sorun Giderme Komutları

### Port 8000 Meşgulse (Address already in use)
```bash
# Önce uvicorn process'lerini durdur
pkill -f "uvicorn app.main:app"

# Port 8000'i kullanan process'i kontrol et
lsof -i :8000

# Eğer başka bir process varsa, PID ile durdur
# kill -9 <PID>
```
**Açıklama**: Port 8000'de çalışan tüm process'leri durdurur

### Redis Çakışması Varsa
```bash
make redis-cleanup
export REDIS_PASSWORD=dev_redis_password
docker compose -f docker-compose.dev.yml up -d redis
```
**Açıklama**: Tüm Redis instance'larını temizler ve sadece Docker Redis'i başlatır

### Tüm Servisleri Durdur
```bash
docker compose -f docker-compose.dev.yml down
pkill -f uvicorn
```
**Açıklama**: Tüm Docker servislerini ve backend sunucusunu durdurur

### Redis Şifre Problemi
```bash
# Redis container'ına bağlan ve şifreyi kontrol et
docker exec -it meeting-ai-redis redis-cli -a dev_redis_password CONFIG GET requirepass
```
**Beklenen Çıktı**: `1) "requirepass" 2) "dev_redis_password"`

---

## 🛠️ Makefile Komutları

Projenizde kullanabileceğiniz hazır komutlar:

```bash
make help                    # Tüm komutları göster
make redis-start            # Docker Redis başlat
make redis-stop             # Docker Redis durdur
make redis-host-start       # Host Redis başlat
make redis-conflict-check   # Redis çakışmalarını kontrol et
make redis-cleanup          # Tüm Redis instance'larını temizle
make backend-start          # Backend sunucusunu başlat
make audit                  # Repository audit çalıştır
make status                 # Docker container durumları
```

---

## 📊 Sistem Durumu Özeti

Başarılı başlatma sonrası şu servisler çalışıyor olmalı:

- ✅ **Redis**: `localhost:6379` (şifreli)
- ✅ **PostgreSQL**: `localhost:5432`
- ✅ **MinIO**: `localhost:9000`
- ✅ **PgAdmin**: `localhost:5050`
- ✅ **Backend API**: `localhost:8000`
- ✅ **JWT Token**: Geçerli ve test edilmiş

---

## 🎯 Hızlı Başlatma Özeti

**Kopyala-yapıştır için tek blok:**

```bash
cd /Users/doganumutsunar/analytics-system
make redis-cleanup
export REDIS_PASSWORD=dev_redis_password
docker compose -f docker-compose.dev.yml up -d
sleep 5
redis-cli -a $REDIS_PASSWORD ping
cd backend && source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**JWT Token üretme (gerekirse):**
```bash
cd backend && source venv/bin/activate && python create_correct_jwt.py
```

**🎉 Bu komutlarla sistem JWT token ile tamamen hazır olacak!**

---

## 📝 Notlar

- Backend sunucusu `--reload` ile başlatılır, kod değişikliklerinde otomatik yeniden başlar
- JWT token `CURRENT_JWT_TOKEN.txt` dosyasında saklanır
- Redis şifresi `dev_redis_password` olarak ayarlanmıştır
- Tüm Docker servisleri `docker-compose.dev.yml` ile yönetilir
- Sorun yaşarsanız `make redis-conflict-check` ile durumu kontrol edin

**Son Güncelleme**: 31 Ağustos 2025

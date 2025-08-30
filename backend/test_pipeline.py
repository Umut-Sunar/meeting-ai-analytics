#!/usr/bin/env python3
"""
🧪 ANALYTICS SYSTEM TEST PIPELINE
==================================

Otomatik JWT token üretimi ve kapsamlı sistem testleri.
Tek komutla tüm sistemi test eder ve hazır token döner.

Usage:
    python test_pipeline.py [--verbose] [--skip-deepgram]
"""

import asyncio
import json
import uuid
import sys
import argparse
import traceback
from datetime import datetime, timedelta
from pathlib import Path

# Backend imports
from app.core.security import create_dev_jwt_token, decode_jwt_token
from app.core.config import get_settings
from app.services.asr.deepgram_live import DeepgramLiveClient

class Colors:
    """Terminal renkleri"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class TestPipeline:
    def __init__(self, verbose=False, skip_deepgram=False):
        self.verbose = verbose
        self.skip_deepgram = skip_deepgram
        self.settings = get_settings()
        self.test_results = {}
        self.jwt_token = None
        self.test_params = {}
        
    def log(self, message, level="INFO"):
        """Renkli log mesajları"""
        colors = {
            "INFO": Colors.CYAN,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "HEADER": Colors.HEADER
        }
        
        color = colors.get(level, Colors.ENDC)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "HEADER":
            print(f"\n{color}{Colors.BOLD}{message}{Colors.ENDC}")
            print(f"{color}{'=' * len(message)}{Colors.ENDC}")
        else:
            prefix = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "WARNING": "⚠️",
                "ERROR": "❌"
            }.get(level, "📝")
            
            print(f"{color}[{timestamp}] {prefix} {message}{Colors.ENDC}")
            
        if self.verbose and level == "ERROR":
            print(f"{Colors.RED}{traceback.format_exc()}{Colors.ENDC}")

    def generate_test_params(self):
        """Test parametrelerini üret"""
        self.log("Test parametreleri oluşturuluyor...", "INFO")
        
        self.test_params = {
            'test_meeting_id': f'test-meeting-{uuid.uuid4().hex[:8]}',
            'test_user_id': 'test-user-001',
            'test_tenant_id': 'test-tenant-001',
            'test_email': 'test@example.com',
            'backend_url': 'http://localhost:8000',
            'websocket_url': 'ws://localhost:8000',
            'deepgram_test_params': {
                'language': self.settings.DEEPGRAM_LANGUAGE,
                'model': self.settings.DEEPGRAM_MODEL,
                'sample_rate': self.settings.INGEST_SAMPLE_RATE,
                'channels': self.settings.INGEST_CHANNELS
            },
            'test_sources': ['mic', 'sys'],
            'generated_at': datetime.now().isoformat()
        }
        
        self.log(f"Meeting ID: {self.test_params['test_meeting_id']}", "SUCCESS")
        return True

    def generate_jwt_token(self):
        """JWT token üret"""
        self.log("JWT token oluşturuluyor...", "INFO")
        
        try:
            # Backend'in kendi fonksiyonunu kullan
            self.jwt_token = create_dev_jwt_token(
                user_id=self.test_params['test_user_id'],
                tenant_id=self.test_params['test_tenant_id'],
                email=self.test_params['test_email'],
                role="user"
            )
            
            # Token'ı doğrula
            claims = decode_jwt_token(self.jwt_token)
            
            # CURRENT_JWT_TOKEN.txt'ye kaydet
            token_file = Path("../CURRENT_JWT_TOKEN.txt")
            with open(token_file, 'w') as f:
                f.write(self.jwt_token)
            
            self.test_params['jwt_token'] = self.jwt_token
            
            self.log(f"JWT token oluşturuldu: {self.jwt_token[:50]}...", "SUCCESS")
            self.log(f"User: {claims.email}, Role: {claims.role}", "SUCCESS")
            self.log(f"Expires: {datetime.fromtimestamp(claims.exp)}", "SUCCESS")
            
            self.test_results['jwt_generation'] = {
                'status': 'success',
                'token_length': len(self.jwt_token),
                'expires_at': claims.exp,
                'user_id': claims.user_id,
                'email': claims.email
            }
            
            return True
            
        except Exception as e:
            self.log(f"JWT token oluşturma hatası: {e}", "ERROR")
            self.test_results['jwt_generation'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False

    def test_backend_api(self):
        """Backend API testleri"""
        self.log("Backend API testleri başlıyor...", "INFO")
        
        try:
            import requests
            
            # Health check
            response = requests.get(f"{self.test_params['backend_url']}/api/v1/health", timeout=5)
            health_data = response.json()
            
            if response.status_code == 200 and health_data.get('status') == 'healthy':
                self.log("Backend health check: OK", "SUCCESS")
                
                # JWT ile authenticated health check
                headers = {'Authorization': f'Bearer {self.jwt_token}'}
                auth_response = requests.get(f"{self.test_params['backend_url']}/api/v1/health", 
                                           headers=headers, timeout=5)
                
                if auth_response.status_code == 200:
                    self.log("JWT authentication: OK", "SUCCESS")
                    
                    self.test_results['backend_api'] = {
                        'status': 'success',
                        'health_check': health_data,
                        'jwt_auth': 'valid'
                    }
                    return True
                else:
                    self.log(f"JWT authentication failed: {auth_response.status_code}", "ERROR")
                    
            else:
                self.log(f"Backend health check failed: {response.status_code}", "ERROR")
                
        except Exception as e:
            self.log(f"Backend API test hatası: {e}", "ERROR")
            
        self.test_results['backend_api'] = {
            'status': 'failed',
            'error': 'Backend API tests failed'
        }
        return False

    async def test_deepgram_connection(self):
        """Deepgram bağlantı testi"""
        if self.skip_deepgram:
            self.log("Deepgram testleri atlanıyor...", "WARNING")
            self.test_results['deepgram'] = {'status': 'skipped'}
            return True
            
        self.log("Deepgram bağlantı testi başlıyor...", "INFO")
        
        if not self.settings.DEEPGRAM_API_KEY:
            self.log("DEEPGRAM_API_KEY bulunamadı", "ERROR")
            self.test_results['deepgram'] = {
                'status': 'failed',
                'error': 'No API key'
            }
            return False
        
        try:
            # Callback'ler
            transcripts_received = []
            errors_received = []
            
            async def on_transcript(result):
                transcripts_received.append(result)
                if self.verbose:
                    self.log(f"Transcript: {result.get('text', '')}", "INFO")
            
            async def on_error(error):
                errors_received.append(error)
                self.log(f"Deepgram error: {error}", "WARNING")
            
            # Deepgram client
            client = DeepgramLiveClient(
                meeting_id=self.test_params['test_meeting_id'],
                language=self.settings.DEEPGRAM_LANGUAGE,
                sample_rate=self.settings.INGEST_SAMPLE_RATE,
                channels=self.settings.INGEST_CHANNELS,
                model=self.settings.DEEPGRAM_MODEL,
                on_transcript=on_transcript,
                on_error=on_error
            )
            
            # Bağlan
            await client.connect()
            self.log("Deepgram bağlantısı kuruldu", "SUCCESS")
            
            # Test ses verisi gönder
            test_frames = 3
            for i in range(test_frames):
                # Sessizlik verisi
                test_audio = b'\x00' * 1920  # 48kHz, 1ch, 20ms
                await client.send_pcm(test_audio)
                await asyncio.sleep(0.1)
            
            # Sonuçları bekle
            await asyncio.sleep(2)
            
            # Finalize
            await client.finalize()
            
            self.log(f"Deepgram test tamamlandı", "SUCCESS")
            self.log(f"Gönderilen bytes: {client.bytes_sent}", "INFO")
            self.log(f"Gönderilen frame'ler: {client.frames_sent}", "INFO")
            
            self.test_results['deepgram'] = {
                'status': 'success',
                'bytes_sent': client.bytes_sent,
                'frames_sent': client.frames_sent,
                'transcripts_received': len(transcripts_received),
                'errors_received': len(errors_received),
                'connection_time': str(client.connected_at)
            }
            
            return True
            
        except Exception as e:
            self.log(f"Deepgram test hatası: {e}", "ERROR")
            self.test_results['deepgram'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False

    def generate_output(self):
        """Final çıktı üret"""
        self.log("Test sonuçları hazırlanıyor...", "HEADER")
        
        # Özet istatistikler
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r.get('status') == 'success')
        failed_tests = sum(1 for r in self.test_results.values() if r.get('status') == 'failed')
        skipped_tests = sum(1 for r in self.test_results.values() if r.get('status') == 'skipped')
        
        print(f"\n{Colors.BOLD}{Colors.HEADER}🎯 TEST PIPELINE SONUÇLARI{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 50}{Colors.ENDC}")
        
        print(f"\n📊 {Colors.BOLD}İSTATİSTİKLER:{Colors.ENDC}")
        print(f"   Toplam Test: {total_tests}")
        print(f"   {Colors.GREEN}✅ Başarılı: {passed_tests}{Colors.ENDC}")
        print(f"   {Colors.RED}❌ Başarısız: {failed_tests}{Colors.ENDC}")
        print(f"   {Colors.YELLOW}⏭️ Atlanan: {skipped_tests}{Colors.ENDC}")
        
        # JWT Token bilgileri
        if self.jwt_token:
            print(f"\n🔑 {Colors.BOLD}JWT TOKEN (HAZIR):{Colors.ENDC}")
            print(f"{Colors.GREEN}{self.jwt_token}{Colors.ENDC}")
            
            print(f"\n📋 {Colors.BOLD}MACCLIENT İÇİN PARAMETRELER:{Colors.ENDC}")
            print(f"   Meeting ID: {Colors.CYAN}{self.test_params['test_meeting_id']}{Colors.ENDC}")
            print(f"   Backend URL: {Colors.CYAN}{self.test_params['backend_url']}{Colors.ENDC}")
            print(f"   WebSocket URL: {Colors.CYAN}{self.test_params['websocket_url']}{Colors.ENDC}")
            
            # WebSocket endpoint'leri
            print(f"\n🔌 {Colors.BOLD}WEBSOCKET ENDPOINT'LERİ:{Colors.ENDC}")
            meeting_id = self.test_params['test_meeting_id']
            print(f"   Mic: {Colors.CYAN}ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}?source=mic{Colors.ENDC}")
            print(f"   System: {Colors.CYAN}ws://localhost:8000/api/v1/ws/ingest/meetings/{meeting_id}?source=sys{Colors.ENDC}")
            print(f"   Transcript: {Colors.CYAN}ws://localhost:8000/api/v1/transcript/{meeting_id}{Colors.ENDC}")
        
        # Test detayları
        if self.verbose:
            print(f"\n🔍 {Colors.BOLD}DETAYLI TEST SONUÇLARI:{Colors.ENDC}")
            for test_name, result in self.test_results.items():
                status_color = Colors.GREEN if result['status'] == 'success' else Colors.RED
                print(f"   {test_name}: {status_color}{result['status']}{Colors.ENDC}")
                if 'error' in result:
                    print(f"     Error: {Colors.RED}{result['error']}{Colors.ENDC}")
        
        # JSON çıktı dosyası
        output_data = {
            'pipeline_run': {
                'timestamp': datetime.now().isoformat(),
                'test_params': self.test_params,
                'test_results': self.test_results,
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'skipped': skipped_tests,
                    'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
                }
            }
        }
        
        # JSON dosyasına kaydet
        with open('pipeline_results.json', 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 {Colors.BOLD}Detaylı sonuçlar pipeline_results.json dosyasına kaydedildi{Colors.ENDC}")
        
        # Başarı durumu
        if failed_tests == 0:
            print(f"\n🎉 {Colors.GREEN}{Colors.BOLD}TÜM TESTLER BAŞARILI! SİSTEM HAZIR!{Colors.ENDC}")
            return True
        else:
            print(f"\n⚠️ {Colors.YELLOW}{Colors.BOLD}{failed_tests} TEST BAŞARISIZ. LÜTFEN KONTROL EDİN.{Colors.ENDC}")
            return False

    async def run_pipeline(self):
        """Ana pipeline'ı çalıştır"""
        self.log("🚀 ANALYTICS SYSTEM TEST PIPELINE BAŞLIYOR", "HEADER")
        
        # 1. Test parametreleri üret
        if not self.generate_test_params():
            return False
        
        # 2. JWT token üret
        if not self.generate_jwt_token():
            return False
        
        # 3. Backend API testleri
        if not self.test_backend_api():
            self.log("Backend API testleri başarısız, devam ediliyor...", "WARNING")
        
        # 4. Deepgram testleri
        await self.test_deepgram_connection()
        
        # 5. Sonuçları üret
        return self.generate_output()

def main():
    parser = argparse.ArgumentParser(description='Analytics System Test Pipeline')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Detaylı çıktı göster')
    parser.add_argument('--skip-deepgram', action='store_true',
                       help='Deepgram testlerini atla')
    
    args = parser.parse_args()
    
    pipeline = TestPipeline(verbose=args.verbose, skip_deepgram=args.skip_deepgram)
    
    try:
        success = asyncio.run(pipeline.run_pipeline())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⏹️ Pipeline kullanıcı tarafından durduruldu{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Pipeline hatası: {e}{Colors.ENDC}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

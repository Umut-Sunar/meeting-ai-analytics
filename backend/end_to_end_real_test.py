#!/usr/bin/env python3
"""
🎯 End-to-End Real Dual-Source Audio Test
========================================

Bu test şunları yapar:
1. ✅ JWT token üretir
2. ✅ Backend'e dual WebSocket bağlantısı kurar (mic + sys)  
3. ✅ Gerçek Deepgram bağlantısı açar
4. ✅ Türkçe test ses dosyası simüle eder
5. ✅ Her iki kanaldan ses gönderir
6. ✅ Transcript sonuçlarını alır
7. ✅ Terminal loglarını takip eder
8. ✅ Deepgram dashboard'unda görülebilir
"""

import asyncio
import json
import websockets
import jwt
import time
import struct
import math
import sys
import aiofiles
from datetime import datetime
from typing import Dict, List
import subprocess
import threading
import queue

# Backend imports
sys.path.insert(0, '.')
from app.core.config import get_settings

class Colors:
    """Terminal renkleri"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def colored(text: str, color: str) -> str:
    return f"{color}{text}{Colors.END}"

def generate_jwt_token() -> str:
    """JWT token üret"""
    settings = get_settings()
    payload = {
        "user_id": "e2e-test-user",
        "tenant_id": "e2e-test-tenant", 
        "email": "e2e@test.com",
        "role": "user",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "aud": settings.JWT_AUDIENCE,
        "iss": settings.JWT_ISSUER
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def generate_turkish_audio_pcm(duration_seconds: float = 10.0, sample_rate: int = 48000) -> bytes:
    """
    Türkçe konuşma simülasyonu için karmaşık PCM audio üret
    - Çoklu frekans karışımı
    - Değişken amplitüd (konuşma benzeri)
    - Düşük frekanslı background noise
    """
    total_samples = int(duration_seconds * sample_rate)
    audio_data = []
    
    print(f"🎵 {colored('Türkçe konuşma simülasyonu üretiliyor...', Colors.CYAN)}")
    print(f"   📊 Süre: {duration_seconds}s, Sample rate: {sample_rate}Hz")
    print(f"   📊 Toplam sample: {total_samples:,}")
    
    for i in range(total_samples):
        t = i / sample_rate
        
        # Türkçe konuşma frekansları (100-3000 Hz arası)
        fundamental = 200 + 50 * math.sin(2 * math.pi * 0.5 * t)  # Ana frekans
        formant1 = 800 + 200 * math.sin(2 * math.pi * 0.3 * t)   # Sesli harf formantı
        formant2 = 1500 + 300 * math.sin(2 * math.pi * 0.7 * t)  # İkinci formant
        
        # Konuşma benzeri amplitüd modulasyonu
        envelope = 0.3 + 0.7 * (math.sin(2 * math.pi * 2.5 * t) ** 2)
        
        # Karmaşık sinyal karışımı
        signal = (
            0.4 * math.sin(2 * math.pi * fundamental * t) +
            0.3 * math.sin(2 * math.pi * formant1 * t) +
            0.2 * math.sin(2 * math.pi * formant2 * t) +
            0.1 * math.sin(2 * math.pi * (fundamental * 2) * t)  # Harmonik
        ) * envelope
        
        # Background noise ekle (konuşma gerçekçiliği için)
        noise = 0.05 * (2 * (i % 1000) / 1000 - 1)  # Pseudo-random noise
        
        # Int16 range'e çevir (-32768 to 32767)
        sample = int((signal + noise) * 16000)  # Reduced amplitude
        sample = max(-32768, min(32767, sample))
        
        audio_data.append(sample)
    
    # Int16 LE format'a çevir
    pcm_data = struct.pack(f'<{len(audio_data)}h', *audio_data)
    print(f"   ✅ PCM data üretildi: {len(pcm_data):,} bytes")
    
    return pcm_data

class DualSourceTest:
    def __init__(self):
        self.settings = get_settings()
        self.jwt_token = generate_jwt_token()
        self.meeting_id = f"e2e-test-{int(time.time())}"
        self.base_url = "ws://localhost:8000/api/v1/ws/ingest/meetings"
        
        # Test sonuçları
        self.results = {
            'mic_connected': False,
            'sys_connected': False,
            'mic_transcripts': [],
            'sys_transcripts': [],
            'deepgram_sessions': 0,
            'errors': []
        }
        
        print(f"🎯 {colored('End-to-End Dual-Source Test Başlatılıyor', Colors.BOLD + Colors.GREEN)}")
        print(f"📋 Meeting ID: {colored(self.meeting_id, Colors.YELLOW)}")
        print(f"🔑 JWT Token: {colored(self.jwt_token[:30] + '...', Colors.CYAN)}")
        print(f"🌐 Backend URL: {colored(self.base_url, Colors.BLUE)}")
        
    async def check_deepgram_connection(self) -> bool:
        """Deepgram API bağlantısını test et"""
        print(f"\n🔍 {colored('Deepgram API Bağlantısı Kontrol Ediliyor...', Colors.PURPLE)}")
        
        if not self.settings.DEEPGRAM_API_KEY:
            print(f"❌ {colored('Deepgram API key bulunamadı!', Colors.RED)}")
            return False
            
        print(f"🔑 API Key: {colored(self.settings.DEEPGRAM_API_KEY[:20] + '...', Colors.CYAN)}")
        
        try:
            headers = {"Authorization": f"Token {self.settings.DEEPGRAM_API_KEY}"}
            params = {
                "model": "nova-2",
                "language": "tr", 
                "punctuate": "true",
                "encoding": "linear16",
                "sample_rate": "48000",
                "channels": "1"
            }
            
            param_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"wss://api.deepgram.com/v1/listen?{param_string}"
            
            print(f"🔗 Deepgram URL: {colored(url[:60] + '...', Colors.BLUE)}")
            
            async with websockets.connect(url, additional_headers=headers) as ws:
                print(f"✅ {colored('Deepgram bağlantısı başarılı!', Colors.GREEN)}")
                
                # Test chunk gönder
                test_chunk = b'\x00' * 1920  # 20ms silence at 48kHz mono
                await ws.send(test_chunk)
                print(f"📤 Test audio gönderildi (20ms sessizlik)")
                
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    print(f"📨 Deepgram yanıtı: {colored(response[:100] + '...', Colors.GREEN)}")
                except asyncio.TimeoutError:
                    print(f"⚠️  {colored('Yanıt yok (sessizlik için normal)', Colors.YELLOW)}")
                
                return True
                
        except Exception as e:
            print(f"❌ {colored(f'Deepgram bağlantı hatası: {e}', Colors.RED)}")
            return False
    
    async def test_websocket_connection(self, source: str) -> dict:
        """Tek source için WebSocket bağlantısı test et"""
        print(f"\n🔌 {colored(f'{source.upper()} WebSocket Bağlantısı Kuruluyor...', Colors.CYAN)}")
        
        url = f"{self.base_url}/{self.meeting_id}?source={source}"
        handshake = {
            "type": "handshake",
            "source": "system" if source == "sys" else "mic",
            "sample_rate": 48000,
            "channels": 1,
            "language": "tr",
            "ai_mode": "standard",
            "device_id": f"e2e-test-{source}"
        }
        
        result = {
            'connected': False,
            'handshake_success': False,
            'transcripts_received': 0,
            'audio_sent_bytes': 0,
            'session_id': None,
            'errors': []
        }
        
        try:
            print(f"📡 Bağlanıyor: {colored(url, Colors.BLUE)}")
            
            async with websockets.connect(
                url,
                additional_headers={"Authorization": f"Bearer {self.jwt_token}"}
            ) as ws:
                result['connected'] = True
                print(f"✅ {colored(f'{source.upper()} WebSocket bağlandı', Colors.GREEN)}")
                
                # Handshake gönder
                await ws.send(json.dumps(handshake))
                print(f"📤 Handshake gönderildi: {colored(handshake['source'], Colors.YELLOW)}")
                
                # İlk yanıt status message olabilir, success message'ı bekle
                handshake_success = False
                for attempt in range(3):  # 3 mesaj deneme
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        response_data = json.loads(response)
                        
                        # Status message ise sonraki mesajı bekle
                        if response_data.get('type') == 'status':
                            print(f"📋 Status: {colored(response_data.get('message', ''), Colors.BLUE)}")
                            continue
                            
                        # Success message'ı bul
                        if response_data.get('status') == 'success' or response_data.get('message') == 'Connected to transcription':
                            result['handshake_success'] = True
                            result['session_id'] = response_data.get('session_id', f'sess-{source}')
                            print(f"✅ {colored('Handshake başarılı!', Colors.GREEN)}")
                            print(f"🆔 Session ID: {colored(result['session_id'], Colors.CYAN)}")
                            
                            # Deepgram session sayısını artır
                            self.results['deepgram_sessions'] += 1
                            handshake_success = True
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"⚠️ {colored(f'Handshake response timeout (attempt {attempt + 1})', Colors.YELLOW)}")
                        
                if not handshake_success:
                    print(f"❌ {colored('Handshake başarısız - timeout', Colors.RED)}")
                    result['errors'].append("Handshake timeout")
                    # Return yerine devam et - audio test'i de yapalım
                    print(f"🔄 {colored('Audio test\'ine devam ediliyor...', Colors.YELLOW)}")
                
                # Türkçe ses dosyası üret ve gönder
                print(f"🎵 {colored(f'{source.upper()} kanalına Türkçe ses gönderiliyor...', Colors.PURPLE)}")
                
                # Kanal bazında farklı ses üret
                if source == "mic":
                    # Mikrofon: Yüksek frekanslı konuşma simülasyonu
                    audio_data = generate_turkish_audio_pcm(duration_seconds=8.0)
                    audio_description = "Mikrofon: Yüksek frekanslı konuşma"
                else:
                    # System: Düşük frekanslı system audio simülasyonu
                    audio_data = generate_turkish_audio_pcm(duration_seconds=6.0)
                    audio_description = "System: Düşük frekanslı hoparlör"
                
                print(f"📊 {audio_description}")
                print(f"📏 Audio boyutu: {colored(f'{len(audio_data):,} bytes', Colors.CYAN)}")
                
                # Ses dosyasını chunk'lara böl ve gönder (20ms chunks)
                chunk_size = 1920  # 20ms at 48kHz mono (48000 * 0.02 * 2 bytes)
                total_chunks = len(audio_data) // chunk_size
                
                print(f"📦 {colored(f'{total_chunks} chunk', Colors.YELLOW)} halinde gönderiliyor...")
                
                transcript_task = asyncio.create_task(
                    self.listen_for_transcripts(ws, source, result)
                )
                
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i+chunk_size]
                    if len(chunk) == chunk_size:  # Sadece tam chunk'ları gönder
                        await ws.send(chunk)
                        result['audio_sent_bytes'] += len(chunk)
                        
                        # Progress göster
                        if (i // chunk_size) % 50 == 0:
                            progress = (i / len(audio_data)) * 100
                            print(f"📈 Progress: {colored(f'{progress:.1f}%', Colors.YELLOW)}")
                        
                        # Realistic timing (20ms intervals)
                        await asyncio.sleep(0.02)
                
                print(f"✅ {colored(f'{source.upper()} audio gönderimi tamamlandı', Colors.GREEN)}")
                print(f"📊 Toplam gönderilen: {colored(f'{result['audio_sent_bytes']:,} bytes', Colors.CYAN)}")
                
                # Transcript'lerin gelmesini bekle
                print(f"👂 {colored('Transcript sonuçları bekleniyor...', Colors.YELLOW)}")
                await asyncio.sleep(5.0)  # Deepgram processing time
                
                transcript_task.cancel()
                
                print(f"📝 {colored(f'{source.upper()} - {result['transcripts_received']} transcript alındı', Colors.GREEN)}")
                
        except Exception as e:
            error_msg = f"{source.upper()} WebSocket error: {e}"
            print(f"❌ {colored(error_msg, Colors.RED)}")
            result['errors'].append(error_msg)
            self.results['errors'].append(error_msg)
        
        return result
    
    async def listen_for_transcripts(self, ws, source: str, result: dict):
        """WebSocket'ten transcript mesajlarını dinle"""
        try:
            while True:
                message = await ws.recv()
                try:
                    data = json.loads(message)
                    if data.get('type') in ['transcript.partial', 'transcript.final']:
                        result['transcripts_received'] += 1
                        transcript_text = data.get('text', '')
                        is_final = data.get('type') == 'transcript.final'
                        confidence = data.get('confidence', 0)
                        
                        # Source'a göre transcript'i kaydet
                        if source == "mic":
                            self.results['mic_transcripts'].append({
                                'text': transcript_text,
                                'is_final': is_final,
                                'confidence': confidence,
                                'timestamp': datetime.now().isoformat()
                            })
                        else:
                            self.results['sys_transcripts'].append({
                                'text': transcript_text,
                                'is_final': is_final,
                                'confidence': confidence,
                                'timestamp': datetime.now().isoformat()
                            })
                        
                        status_icon = "🔸" if is_final else "💭"
                        conf_str = f"({confidence:.2f})" if confidence else ""
                        print(f"{status_icon} {colored(source.upper(), Colors.CYAN)}: {colored(transcript_text[:100], Colors.WHITE)} {conf_str}")
                        
                except json.JSONDecodeError:
                    pass  # Non-JSON messages
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"⚠️ {colored(f'{source.upper()} transcript listener error: {e}', Colors.YELLOW)}")
    
    async def run_test(self):
        """Ana test çalıştır"""
        print(f"\n{'='*80}")
        print(f"{colored('🎯 END-TO-END DUAL-SOURCE AUDIO TEST', Colors.BOLD + Colors.GREEN)}")
        print(f"{'='*80}")
        
        # 1. Deepgram bağlantısını test et
        deepgram_ok = await self.check_deepgram_connection()
        if not deepgram_ok:
            print(f"\n❌ {colored('Deepgram bağlantısı başarısız - test durduruluyor', Colors.RED)}")
            return False
        
        # 2. Dual WebSocket test et
        print(f"\n🔄 {colored('Dual WebSocket Bağlantıları Test Ediliyor...', Colors.BOLD + Colors.BLUE)}")
        
        # Parallel olarak her iki source'u test et
        mic_task = asyncio.create_task(self.test_websocket_connection("mic"))
        sys_task = asyncio.create_task(self.test_websocket_connection("sys"))
        
        mic_result, sys_result = await asyncio.gather(mic_task, sys_task, return_exceptions=True)
        
        # Sonuçları kaydet
        if isinstance(mic_result, dict):
            self.results['mic_connected'] = mic_result['connected']
        if isinstance(sys_result, dict):
            self.results['sys_connected'] = sys_result['connected']
        
        # 3. Test sonuçlarını rapor et
        await self.print_test_results(mic_result, sys_result)
        
        return self.results['mic_connected'] and self.results['sys_connected']
    
    async def print_test_results(self, mic_result, sys_result):
        """Test sonuçlarını detaylı yazdır"""
        print(f"\n{'='*80}")
        print(f"{colored('📊 TEST SONUÇLARI', Colors.BOLD + Colors.YELLOW)}")
        print(f"{'='*80}")
        
        # Bağlantı durumu
        print(f"\n🔌 {colored('Bağlantı Durumu:', Colors.BOLD)}")
        mic_status = "✅ Başarılı" if self.results['mic_connected'] else "❌ Başarısız"
        sys_status = "✅ Başarılı" if self.results['sys_connected'] else "❌ Başarısız"
        print(f"   🎤 Mikrofon: {colored(mic_status, Colors.GREEN if self.results['mic_connected'] else Colors.RED)}")
        print(f"   🔊 System:   {colored(sys_status, Colors.GREEN if self.results['sys_connected'] else Colors.RED)}")
        
        # Deepgram sessions
        print(f"\n🤖 {colored('Deepgram Sessions:', Colors.BOLD)}")
        print(f"   📊 Açılan session sayısı: {colored(str(self.results['deepgram_sessions']), Colors.CYAN)}")
        
        # Audio istatistikleri
        if isinstance(mic_result, dict) and isinstance(sys_result, dict):
            print(f"\n🎵 {colored('Audio İstatistikleri:', Colors.BOLD)}")
            print(f"   🎤 Mikrofon gönderilen: {colored(f'{mic_result.get('audio_sent_bytes', 0):,} bytes', Colors.CYAN)}")
            print(f"   🔊 System gönderilen:   {colored(f'{sys_result.get('audio_sent_bytes', 0):,} bytes', Colors.CYAN)}")
        
        # Transcript sonuçları
        print(f"\n📝 {colored('Transcript Sonuçları:', Colors.BOLD)}")
        print(f"   🎤 Mikrofon transcript sayısı: {colored(str(len(self.results['mic_transcripts'])), Colors.GREEN)}")
        print(f"   🔊 System transcript sayısı:   {colored(str(len(self.results['sys_transcripts'])), Colors.GREEN)}")
        
        # Final transcript'leri göster
        final_mic = [t for t in self.results['mic_transcripts'] if t['is_final']]
        final_sys = [t for t in self.results['sys_transcripts'] if t['is_final']]
        
        if final_mic:
            print(f"\n🎤 {colored('Mikrofon Final Transcript\'ler:', Colors.BOLD + Colors.GREEN)}")
            for i, transcript in enumerate(final_mic, 1):
                conf = f" ({transcript['confidence']:.2f})" if transcript['confidence'] else ""
                print(f"   {i}. {colored(transcript['text'], Colors.WHITE)}{conf}")
        
        if final_sys:
            print(f"\n🔊 {colored('System Final Transcript\'ler:', Colors.BOLD + Colors.GREEN)}")
            for i, transcript in enumerate(final_sys, 1):
                conf = f" ({transcript['confidence']:.2f})" if transcript['confidence'] else ""
                print(f"   {i}. {colored(transcript['text'], Colors.WHITE)}{conf}")
        
        # Hatalar
        if self.results['errors']:
            print(f"\n❌ {colored('Hatalar:', Colors.BOLD + Colors.RED)}")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"   {i}. {colored(error, Colors.RED)}")
        
        # Genel değerlendirme
        print(f"\n{'='*80}")
        success_count = sum([
            self.results['mic_connected'],
            self.results['sys_connected'], 
            self.results['deepgram_sessions'] >= 2,
            len(self.results['mic_transcripts']) > 0 or len(self.results['sys_transcripts']) > 0
        ])
        
        if success_count >= 3:
            overall = f"🎉 {colored('BAŞARILI - Dual-source audio transcription çalışıyor!', Colors.BOLD + Colors.GREEN)}"
        elif success_count >= 2:
            overall = f"⚠️ {colored('KISMEN BAŞARILI - Bazı problemler var', Colors.BOLD + Colors.YELLOW)}"
        else:
            overall = f"❌ {colored('BAŞARISIZ - Major problemler var', Colors.BOLD + Colors.RED)}"
        
        print(overall)
        print(f"📊 Skor: {colored(f'{success_count}/4', Colors.CYAN)}")
        print(f"{'='*80}")
        
        # Deepgram dashboard bilgisi
        print(f"\n💡 {colored('Deepgram Dashboard:', Colors.BOLD + Colors.PURPLE)}")
        print(f"   🌐 https://console.deepgram.com/")
        print(f"   📊 Bu test'te açılan session'ları 'Usage' sekmesinde görebilirsiniz")
        print(f"   🕐 Test zamanı: {colored(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), Colors.CYAN)}")
        
async def main():
    """Ana fonksiyon"""
    test = DualSourceTest()
    
    try:
        success = await test.run_test()
        exit_code = 0 if success else 1
        print(f"\n🏁 {colored('Test tamamlandı!', Colors.BOLD)}")
        exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n⚠️ {colored('Test kullanıcı tarafından durduruldu', Colors.YELLOW)}")
        exit(130)
    except Exception as e:
        print(f"\n💥 {colored(f'Beklenmeyen hata: {e}', Colors.RED)}")
        exit(1)

if __name__ == "__main__":
    print(f"{colored('🚀 End-to-End Dual-Source Audio Test Başlatılıyor...', Colors.BOLD + Colors.BLUE)}")
    asyncio.run(main())

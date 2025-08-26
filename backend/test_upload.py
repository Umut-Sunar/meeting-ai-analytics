#!/usr/bin/env python3
"""
Test script for multipart upload functionality.
Creates a 5MB test file and uploads it using the ingest API.
"""

import asyncio
import os
import tempfile
import httpx
from typing import List, Dict

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
MEETING_ID = "test-meeting-001"
TEST_FILE_SIZE = 5 * 1024 * 1024  # 5MB
CHUNK_SIZE = 1024 * 1024  # 1MB chunks


async def create_test_file(size_bytes: int) -> str:
    """Create a test file with random data."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
    
    print(f"📝 Creating test file: {temp_file.name} ({size_bytes / 1024 / 1024:.1f}MB)")
    
    # Write random data
    remaining = size_bytes
    while remaining > 0:
        chunk_size = min(remaining, CHUNK_SIZE)
        data = os.urandom(chunk_size)
        temp_file.write(data)
        remaining -= chunk_size
    
    temp_file.close()
    return temp_file.name


async def start_upload(client: httpx.AsyncClient, file_path: str) -> Dict:
    """Start a multipart upload."""
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    
    # Calculate number of parts (5MB per part)
    part_size = 5 * 1024 * 1024  # 5MB
    part_count = (file_size + part_size - 1) // part_size
    
    request_data = {
        "file_type": "audio_raw",
        "file_name": file_name,
        "file_size": file_size,
        "content_type": "application/octet-stream",
        "part_count": part_count
    }
    
    print(f"🚀 Starting upload: {file_name} ({file_size} bytes, {part_count} parts)")
    
    response = await client.post(
        f"{API_BASE_URL}/meetings/{MEETING_ID}/ingest/start",
        json=request_data
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to start upload: {response.status_code} - {response.text}")
        return None
    
    return response.json()


async def upload_parts(client: httpx.AsyncClient, file_path: str, upload_info: Dict) -> List[Dict]:
    """Upload all file parts using presigned URLs."""
    file_size = os.path.getsize(file_path)
    upload_urls = upload_info["upload_urls"]
    part_size = 5 * 1024 * 1024  # 5MB
    
    uploaded_parts = []
    
    with open(file_path, 'rb') as f:
        for url_info in upload_urls:
            part_number = url_info["part_number"]
            upload_url = url_info["upload_url"]
            
            # Calculate part size
            start_pos = (part_number - 1) * part_size
            current_part_size = min(part_size, file_size - start_pos)
            
            # Read part data
            f.seek(start_pos)
            part_data = f.read(current_part_size)
            
            print(f"📤 Uploading part {part_number}/{len(upload_urls)} ({len(part_data)} bytes)")
            
            # Upload part
            upload_response = await client.put(
                upload_url,
                content=part_data,
                headers={"Content-Type": "application/octet-stream"}
            )
            
            if upload_response.status_code not in [200, 204]:
                print(f"❌ Failed to upload part {part_number}: {upload_response.status_code}")
                return None
            
            # Get ETag from response
            etag = upload_response.headers.get("ETag", "").strip('"')
            
            uploaded_parts.append({
                "part_number": part_number,
                "etag": etag,
                "size": len(part_data)
            })
            
            print(f"✅ Part {part_number} uploaded (ETag: {etag})")
    
    return uploaded_parts


async def complete_upload(client: httpx.AsyncClient, upload_info: Dict, parts: List[Dict]) -> Dict:
    """Complete the multipart upload."""
    request_data = {
        "upload_id": upload_info["upload_id"],
        "object_key": upload_info["object_key"],
        "parts": parts
    }
    
    print(f"🏁 Completing upload...")
    
    response = await client.post(
        f"{API_BASE_URL}/meetings/{MEETING_ID}/ingest/complete",
        json=request_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to complete upload: {response.status_code} - {response.text}")
        return None
    
    return response.json()


async def check_upload_status(client: httpx.AsyncClient, upload_id: str) -> Dict:
    """Check upload status."""
    response = await client.get(
        f"{API_BASE_URL}/meetings/{MEETING_ID}/ingest/{upload_id}/status"
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get status: {response.status_code} - {response.text}")
        return None
    
    return response.json()


async def test_upload_flow():
    """Test the complete upload flow."""
    print("🧪 Starting upload test...")
    
    # Create test file
    test_file = await create_test_file(TEST_FILE_SIZE)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Start upload
            upload_info = await start_upload(client, test_file)
            if not upload_info:
                return
            
            print(f"✅ Upload started: {upload_info['upload_id']}")
            print(f"   Object key: {upload_info['object_key']}")
            print(f"   Bucket: {upload_info['bucket_name']}")
            print(f"   Parts: {len(upload_info['upload_urls'])}")
            
            # 2. Check initial status
            status = await check_upload_status(client, upload_info['upload_id'])
            if status:
                print(f"📊 Status: {status['status']} ({status['parts_uploaded']}/{status['total_parts']} parts)")
            
            # 3. Upload parts
            uploaded_parts = await upload_parts(client, test_file, upload_info)
            if not uploaded_parts:
                return
            
            print(f"✅ All {len(uploaded_parts)} parts uploaded")
            
            # 4. Complete upload
            completion_result = await complete_upload(client, upload_info, uploaded_parts)
            if not completion_result:
                return
            
            print(f"🎉 Upload completed successfully!")
            print(f"   Audio Blob ID: {completion_result['audio_blob_id']}")
            print(f"   Final size: {completion_result['file_size']} bytes")
            print(f"   ETag: {completion_result['etag']}")
            print(f"   Completed at: {completion_result['completed_at']}")
            
            # 5. Final status check
            final_status = await check_upload_status(client, upload_info['upload_id'])
            if final_status:
                print(f"📊 Final status: {final_status['status']} ({final_status['parts_uploaded']}/{final_status['total_parts']} parts)")
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"🧹 Cleaned up test file: {test_file}")


async def test_api_health():
    """Test if the API is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API is healthy: {health_data['status']}")
                return True
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False


async def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 MinIO Upload Test Script")
    print("=" * 60)
    
    # Check API health
    if not await test_api_health():
        print("❌ API is not available. Make sure the backend is running.")
        return
    
    # Run upload test
    await test_upload_flow()
    
    print("=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

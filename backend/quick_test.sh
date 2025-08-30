#!/bin/bash
# 🚀 ANALYTICS SYSTEM QUICK TEST
# Tek komutla JWT token üret ve tüm testleri yap

cd "$(dirname "$0")"

echo "🚀 Analytics System Quick Test Pipeline"
echo "======================================"

# Virtual environment'ı aktif et
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found!"
    exit 1
fi

# Pipeline'ı çalıştır
echo ""
echo "🧪 Running test pipeline..."
python test_pipeline.py "$@"

# Exit code'u pipeline'dan al
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "🎉 Pipeline completed successfully!"
    echo "📋 JWT token saved to CURRENT_JWT_TOKEN.txt"
    echo "📄 Detailed results in pipeline_results.json"
else
    echo ""
    echo "❌ Pipeline failed with exit code: $exit_code"
fi

exit $exit_code

#!/bin/bash

echo "🚀 Crypto Compliance Copilot - Module 5 Demo"
echo "=============================================="
echo ""

# Check if backend is running
echo "🔍 Checking backend health..."
BACKEND_HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "ERROR")

if [[ "$BACKEND_HEALTH" == *"healthy"* ]]; then
    echo "✅ Backend is running and healthy"
else
    echo "❌ Backend is not running. Starting backend..."
    echo "Please run the following in another terminal:"
    echo "cd backend && python -m uvicorn app.main:app --reload"
    echo ""
fi

# Check if web dashboard is running
echo "🌐 Checking web dashboard..."
WEB_HEALTH=$(curl -s http://localhost:3000 2>/dev/null || echo "ERROR")

if [[ "$WEB_HEALTH" == *"html"* ]]; then
    echo "✅ Web dashboard is running"
else
    echo "❌ Web dashboard is not running. Starting..."
    echo "Please run: cd web-dashboard && npm run dev"
    echo ""
fi

echo ""
echo "🎯 Demo Instructions:"
echo "====================="
echo ""
echo "1. Open your browser to: http://localhost:3000"
echo "2. Login with demo credentials:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "3. Test the dashboard features:"
echo "   - View transaction monitoring table"
echo "   - Try manual override on transactions"
echo "   - Test bulk anchoring to blockchain"
echo "   - Check real-time updates"
echo ""
echo "4. Key features to demonstrate:"
echo "   - ✨ Real-time transaction monitoring"
echo "   - 🔧 Manual override system with audit trails"
echo "   - ⚓ Blockchain anchoring for immutable records"
echo "   - 🎨 Responsive design with compliance-focused UI"
echo "   - 🔍 Explorer integration for transaction verification"
echo ""

echo "📋 Module 5 Completed Features:"
echo "==============================="
echo "✅ Next.js 14.0.0 web application"
echo "✅ TypeScript for type safety"
echo "✅ Tailwind CSS for styling"
echo "✅ SWR for real-time data fetching"
echo "✅ JWT authentication (mock for MVP)"
echo "✅ Transaction monitoring table"
echo "✅ Manual override system"
echo "✅ Blockchain anchoring interface"
echo "✅ Explorer integration"
echo "✅ Responsive design"
echo "✅ Error handling and loading states"
echo ""

echo "🔧 Technical Implementation:"
echo "============================"
echo "- Pages: Login (/), Dashboard (/dashboard)"
echo "- Components: TransactionTable, OverrideModal, AnchorModal"
echo "- API Client: Full integration with Module 4 backend"
echo "- Real-time Updates: 5-second refresh interval"
echo "- Design System: Custom Tailwind theme for compliance"
echo ""

echo "🔗 Integration with Module 4:"
echo "============================="
echo "- Polygon Anchor Service"
echo "- FastAPI Backend APIs"
echo "- Smart Contract verification"
echo "- Explorer URL generation"
echo ""

echo "Ready for Module 6 (Flutter Mobile App)! 📱"

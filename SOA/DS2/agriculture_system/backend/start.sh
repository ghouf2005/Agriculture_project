#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   🌾 AI-Enhanced Crop Monitoring System                     ║"
echo "║   Week 4: Integration & Deployment                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Arrêter les conteneurs existants
echo "🛑 Stopping existing containers..."
docker-compose down

# Construire et démarrer les conteneurs
echo "🔨 Building and starting containers..."
docker-compose up --build -d

# Attendre que la DB et le backend soient prêts
echo "⏳ Waiting for services to be ready..."
sleep 15  # Vous pouvez ajuster si nécessaire

# Afficher l'état des conteneurs
echo ""
echo "📋 Container status:"
docker-compose ps
echo ""

# Afficher les URLs et accès
echo "✅ System is ready!"
echo ""
echo "🔗 Access points:"
echo "   🌐 Backend API: http://localhost:8000/api/"
echo "   🔧 Django Admin: http://localhost:8000/admin/"
echo ""
echo "👤 Default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📝 Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop: docker-compose down"
echo "   Restart: docker-compose restart"
echo ""
echo "📡 Sensor simulator is running in background, sending test data to API."
echo ""

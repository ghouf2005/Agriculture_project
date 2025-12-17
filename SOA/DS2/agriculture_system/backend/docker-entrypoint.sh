#!/bin/bash
set -e

# Attendre que PostgreSQL soit prêt
echo "🔄 Waiting for PostgreSQL..."
while ! nc -z db 5432; do
    sleep 0.2
done
echo "✅ PostgreSQL ready!"

# Lancer les migrations
echo "🔄 Running migrations..."
python manage.py migrate --noinput

# Créer superuser si nécessaire
echo "👤 Creating superuser..."
python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️ Superuser already exists')
EOF

# Charger données initiales si nécessaire
echo "🌱 Loading initial farm data..."
python manage.py shell <<EOF
from agriculture_app.models import FarmProfile, FieldPlot
from django.contrib.auth.models import User

user = User.objects.first()
if not FarmProfile.objects.exists():
    farm = FarmProfile.objects.create(owner=user, location="Tunis Region", size=50.5, crop_type="Wheat & Corn")
    FieldPlot.objects.create(farm=farm, name="Field A", crop_variety="Winter Wheat")
    FieldPlot.objects.create(farm=farm, name="Field B", crop_variety="Spring Corn")
    FieldPlot.objects.create(farm=farm, name="Field C", crop_variety="Barley")
    FieldPlot.objects.create(farm=farm, name="Field D", crop_variety="Oats")
    print('✅ Initial farm and fields created')
else:
    print('ℹ️ Farm data already exists')
EOF

# Lancer le simulateur de capteurs pour générer anomalies
echo "📡 Running sensor simulator..."
python simulator/sensor_simulator.py &

# Démarrer Django
echo "🚀 Starting Django..."
exec "$@"

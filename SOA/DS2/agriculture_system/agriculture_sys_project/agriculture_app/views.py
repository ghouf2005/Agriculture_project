from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import FarmProfile, FieldPlot, SensorReading, AnomalyEvent, AgentRecommendation
from .serializers import (
    FarmProfileSerializer,
    FieldPlotSerializer,
    SensorReadingSerializer,
    AnomalyEventSerializer,
    AgentRecommendationSerializer
)
from .services import process_sensor_reading, train_model_for_plot, get_anomaly_statistics


# ---------------------------------------------------
# FARM LIST (ADMIN or FARMER)
# GET /api/farms/
# ---------------------------------------------------
class FarmListView(generics.ListAPIView):
    queryset = FarmProfile.objects.all()
    serializer_class = FarmProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


# ---------------------------------------------------
# LIST PLOTS OF A FARM
# GET /api/farms/<farm_id>/plots/
# ---------------------------------------------------
class PlotByFarmView(generics.ListAPIView):
    serializer_class = FieldPlotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        farm_id = self.kwargs["farm_id"]
        return FieldPlot.objects.filter(farm_id=farm_id)


# ---------------------------------------------------
# POST SENSOR DATA WITH ML ANALYSIS
# POST /api/sensor-readings/create/
# ---------------------------------------------------
class SensorReadingCreateView(generics.CreateAPIView):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Sauvegarder la lecture
        reading = serializer.save()
        
        # ✨ NOUVEAU : Analyser avec le ML module
        results = process_sensor_reading(reading)
        
        # Log les résultats
        if results['anomaly_created']:
            print(f"✅ Anomalie créée : ID {results['anomaly_event'].id}")
        else:
            print(f"✅ Lecture normale : {reading.sensor_type} = {reading.value}")


# ---------------------------------------------------
# LIST SENSOR READINGS BY PLOT
# GET /api/sensor-readings/?plot=<id>
# ---------------------------------------------------
class SensorReadingListView(generics.ListAPIView):
    serializer_class = SensorReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        plot_id = self.request.query_params.get("plot")
        qs = SensorReading.objects.all()
        if plot_id:
            qs = qs.filter(plot_id=plot_id)
        return qs


# ---------------------------------------------------
# LIST ANOMALIES
# GET /api/anomalies/?plot=<id>
# ---------------------------------------------------
class AnomalyListView(generics.ListAPIView):
    serializer_class = AnomalyEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        plot_id = self.request.query_params.get("plot")
        qs = AnomalyEvent.objects.all()
        if plot_id:
            qs = qs.filter(plot_id=plot_id)
        return qs


# ---------------------------------------------------
# LIST RECOMMENDATIONS
# GET /api/recommendations/?anomaly=<id>
# ---------------------------------------------------
class RecommendationListView(generics.ListAPIView):
    serializer_class = AgentRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        anomaly_id = self.request.query_params.get("anomaly")
        qs = AgentRecommendation.objects.all()
        if anomaly_id:
            qs = qs.filter(anomaly_event_id=anomaly_id)
        return qs


# ---------------------------------------------------
# ✨ NOUVEAU : TRAIN ML MODEL
# POST /api/ml/train/?plot=<id>
# ---------------------------------------------------
class TrainModelView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        plot_id = request.query_params.get('plot')
        
        if not plot_id:
            return Response(
                {'error': 'plot parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que le plot existe
        try:
            plot = FieldPlot.objects.get(id=plot_id)
        except FieldPlot.DoesNotExist:
            return Response(
                {'error': 'Plot not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Entraîner le modèle
        min_samples = request.data.get('min_samples', 100)
        success = train_model_for_plot(plot_id, min_samples)
        
        if success:
            return Response({
                'message': f'Model trained successfully for plot {plot_id}',
                'plot': plot.name
            })
        else:
            return Response(
                {'error': 'Not enough data to train model'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ---------------------------------------------------
# ✨ NOUVEAU : ANOMALY STATISTICS
# GET /api/anomalies/stats/?plot=<id>
# ---------------------------------------------------
class AnomalyStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        plot_id = request.query_params.get('plot')
        stats = get_anomaly_statistics(plot_id)
        
        return Response({
            'plot_id': plot_id,
            'statistics': stats
        })
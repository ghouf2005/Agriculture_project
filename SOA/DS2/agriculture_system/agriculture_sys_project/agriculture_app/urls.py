from rest_framework import routers
from django.urls import path,include

from .views import FieldPlotViewSet,FarmProfileViewSet,SensorReadingViewSet,AnomalyEventViewSet,AgentRecommendationViewSet
router=routers.DefaultRouter()

router.register(r'FieldPlot', FieldPlotViewSet)
router.register(r'FarmProfile', FarmProfileViewSet)
router.register(r'SensorReading', SensorReadingViewSet)
router.register(r'AnomalyEvent', AnomalyEventViewSet)
router.register(r'AgentRecommendation', AgentRecommendationViewSet)

urlpatterns=[
    path('',include(router.urls))
]



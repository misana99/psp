from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Test
from .serializer import TestSerializer

# Create your views here.
@api_view(['GET'])
def get_user(req):
    return Response(TestSerializer([
        {'activity': 'studies', 'status': 'In progress', 'requested': '2025/03/23'},
        {'activity': 'reading', 'status': 'Completed', 'requested': '2025/02/15'},
        {'activity': 'writing', 'status': 'Pending', 'requested': '2025/03/10'},
        {'activity': 'research', 'status': 'In progress', 'requested': '2025/03/05'},
        {'activity': 'presentation', 'status': 'Not started', 'requested': '2025/04/01'},
    ], many=True).data)


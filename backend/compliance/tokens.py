from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class AuditraTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):

        token = super().get_token(user)

        # Add user information to JWT
        token['username'] = user.username
        token['role'] = user.role

        return token


class AuditraTokenObtainPairView(TokenObtainPairView):

    serializer_class = AuditraTokenObtainPairSerializer
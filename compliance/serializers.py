from rest_framework import serializers
from .models import Log, Rule, Violation

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = '__all__'

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = '__all__'

class ViolationSerializer(serializers.ModelSerializer):
    rule = RuleSerializer(read_only=True)
    log = LogSerializer(read_only=True)

    class Meta:
        model = Violation
        fields = '__all__'
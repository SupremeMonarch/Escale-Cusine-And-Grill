# serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["id", "address", "date_of_birth", "phone_number"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(source="userprofile", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "profile"]
        read_only_fields = ["id", "username"]

class UserRegistrationSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password", "profile"]

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )

        if profile_data:
            for attr, value in profile_data.items():
                setattr(user.userprofile, attr, value)
            user.userprofile.save()

        return user

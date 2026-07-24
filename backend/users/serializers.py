"""
用户序列化器
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserRegisterSerializer(serializers.ModelSerializer):
    """注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'nickname', 'student_id', 'college', 'major']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError('两次密码不一致')
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError('该学号/用户名已注册')
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            username=attrs['username'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError('用户名或密码错误')
        if not user.is_active:
            raise serializers.ValidationError('该账号已被禁用')
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    level_title = serializers.CharField(read_only=True)
    avatar_emoji = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'nickname', 'avatar', 'avatar_emoji',
            'gender', 'phone', 'student_id', 'college', 'major',
            'total_points', 'available_points', 'level', 'level_title',
            'streak_days', 'total_carbon_reduction', 'total_tasks_done',
            'created_at',
        ]
        read_only_fields = [
            'id', 'total_points', 'available_points', 'level',
            'streak_days', 'total_carbon_reduction', 'total_tasks_done',
            'created_at',
        ]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """个人资料更新序列化器"""

    class Meta:
        model = User
        fields = ['nickname', 'avatar', 'gender', 'phone', 'college', 'major']

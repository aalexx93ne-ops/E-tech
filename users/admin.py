from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from .models import User
from appx.validators import avatar_validator


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'phone', 'is_staff', 'created_at']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'avatar', 'birth_date')}),
        ('Address', {'fields': ('city', 'address', 'postal_code')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('phone',)}),
    )

    readonly_fields = ['created_at', 'updated_at']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'avatar':
            from django.forms import ImageField
            field = super().formfield_for_dbfield(db_field, request, **kwargs)
            field = ImageField(validators=avatar_validator)
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)

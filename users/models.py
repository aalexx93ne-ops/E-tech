from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name='Phone')
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, verbose_name='Avatar')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Birth Date')
    
    # Address fields
    city = models.CharField(max_length=100, blank=True, verbose_name='City')
    address = models.CharField(max_length=255, blank=True, verbose_name='Address')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='Postal Code')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email

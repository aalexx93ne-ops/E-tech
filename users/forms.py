from django import forms
from .models import User


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'avatar', 'birth_date',
                  'city', 'address', 'postal_code']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

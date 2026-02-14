from django import forms

class OrderCreateForm(forms.Form):
    first_name = forms.CharField(max_length=50, label='Имя')
    last_name = forms.CharField(max_length=50, label='Фамилия')
    email = forms.EmailField(label='Email')
    address = forms.CharField(max_length=250, label='Адрес')
    city = forms.CharField(max_length=100, label='Город')

from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(attrs={'class': 'rating-input'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Напишите ваш отзыв здесь...',
                'minlength': 10,
                'maxlength': 2000
            }),
        }

    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        # Базовая очистка от потенциально опасных тегов (хотя Django экранирует по умолчанию)
        # Мы можем добавить дополнительную логику, если нужно
        return comment

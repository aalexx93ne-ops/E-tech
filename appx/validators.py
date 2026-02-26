from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.template.defaultfilters import filesizeformat


def avatar_validator(value):
    """Валидатор для аватаров пользователей"""
    # Проверка расширения
    FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp'])(value)
    # Проверка размера (5MB)
    if value.size > 5 * 1024 * 1024:
        raise ValidationError(
            f'Размер файла не должен превышать 5MB. Текущий размер: {filesizeformat(value.size)}'
        )


def product_image_validator(value):
    """Валидатор для изображений товаров"""
    # Проверка расширения
    FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'webp'])(value)
    # Проверка размера (10MB)
    if value.size > 10 * 1024 * 1024:
        raise ValidationError(
            f'Размер файла не должен превышать 10MB. Текущий размер: {filesizeformat(value.size)}'
        )


def banner_image_validator(value):
    """Валидатор для баннеров"""
    # Проверка расширения
    FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp'])(value)
    # Проверка размера (10MB)
    if value.size > 10 * 1024 * 1024:
        raise ValidationError(
            f'Размер файла не должен превышать 10MB. Текущий размер: {filesizeformat(value.size)}'
        )

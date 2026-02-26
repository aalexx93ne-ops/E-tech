"""
Генератор безопасного SECRET_KEY для Django
Запустите этот скрипт один раз при создании проекта и скопируйте вывод в .env
"""
import secrets
import string
import sys

# Установка UTF-8 кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def generate_secret_key(length=50):
    """
    Генерирует криптографически стойкий SECRET_KEY.
    Использует secrets module (Python 3.6+), который предназначен
    для криптографически безопасных случайных чисел.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


if __name__ == '__main__':
    key = generate_secret_key()
    print("=" * 60)
    print("СКОПИРУЙТЕ ЭТОТ КЛЮЧ В ВАШ .env ФАЙЛ:")
    print("=" * 60)
    print(f"SECRET_KEY={key}")
    print("=" * 60)
    print("\nВАЖНО:")
    print("  1. Никогда не коммитьте .env в git")
    print("  2. Используйте уникальный ключ для каждого окружения")
    print("  3. Для production используйте переменные окружения")

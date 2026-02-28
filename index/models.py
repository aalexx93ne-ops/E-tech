from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.core.validators import MinLengthValidator, MaxLengthValidator
from appx.validators import product_image_validator, banner_image_validator
import re


class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    slug = models.SlugField("URL", unique=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField("Название бренда", max_length=100)
    slug = models.SlugField("URL", unique=True, null=True, blank=True)

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Brand.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField("Название тега", max_length=100)
    slug = models.SlugField("URL", unique=True)

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class Banner(models.Model):
    image = models.ImageField(
        "Изображение",
        upload_to='banners/',
        validators=[banner_image_validator]
    )
    alt_text = models.CharField("Описание", max_length=255)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def __str__(self):
        return self.alt_text


class Discount(models.Model):
    name = models.CharField("Название скидки", max_length=100)
    percent = models.PositiveIntegerField("Процент скидки")
    start_date = models.DateTimeField("Начало акции", null=True, blank=True)
    end_date = models.DateTimeField("Конец акции", null=True, blank=True)

    class Meta:
        verbose_name = "Скидка"
        verbose_name_plural = "Скидки"

    def is_active(self):
        now = timezone.now()
        return (self.start_date is None or self.start_date <= now) and \
               (self.end_date is None or self.end_date >= now)

    def __str__(self):
        return f"{self.name} ({self.percent}%)"


class Product(models.Model):
    name = models.CharField("Название товара", max_length=255)
    slug = models.SlugField("URL", unique=True, blank=True)
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='products', blank=True)
    discount = models.ForeignKey(
        Discount, on_delete=models.SET_NULL, null=True, blank=True)
    main_image = models.ImageField(
        "Главное изображение",
        upload_to='products/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-id']

    def get_final_price(self):
        if self.discount and self.discount.is_active():
            return round(self.price - (self.price * self.discount.percent / 100), 2)
        return self.price

    def has_discount(self):
        return self.discount and self.discount.is_active()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('index:product_detail', kwargs={'slug': self.slug})


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        "Доп. изображение",
        upload_to='products/gallery/',
        validators=[product_image_validator]
    )
    alt_text = models.CharField(
        "Описание изображения", max_length=255, blank=True)

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"

    def __str__(self):
        return f"Image for {self.product.name}"


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пользователь")
    name = models.CharField("Имя пользователя", max_length=100)
    rating = models.PositiveSmallIntegerField(
        "Оценка", choices=[(i, f"{i} {'★' * i}") for i in range(1, 6)])
    comment = models.TextField(
        "Комментарий",
        validators=[
            MinLengthValidator(10, message="Комментарий должен содержать не менее 10 символов"),
            MaxLengthValidator(2000, message="Комментарий не должен превышать 2000 символов"),
        ]
    )
    tags = models.JSONField("Теги", default=list, blank=True)
    is_verified_purchase = models.BooleanField("Проверенная покупка", default=False)
    created_at = models.DateTimeField("Дата", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
        ]

    def __str__(self):
        return f"Review for {self.product.name} by {self.name}"

    def save(self, *args, **kwargs):
        # Автоматическая проверка верифицированной покупки, если есть пользователь
        if self.user and not self.is_verified_purchase:
            from orders.models import OrderItem
            self.is_verified_purchase = OrderItem.objects.filter(
                order__user=self.user,
                product=self.product,
                order__paid=True
            ).exists()
        
        # Генерация тегов перед сохранением
        if self.comment:
            self.tags = self.extract_tags()
            
        super().save(*args, **kwargs)

    def extract_tags(self):
        """
        Улучшенный алгоритм выделения тегов согласно ТЗ:
        - Учитывает частицу 'не' (не понравился экран)
        - Частичное совпадение слов из характеристик (память -> оперативная память)
        """
        text = self.comment.lower()
        # Список стоп-слов (базовый)
        stop_words = {'и', 'а', 'но', 'же', 'бы', 'ли', 'в', 'на', 'с', 'к', 'по', 'о', 'об', 'из', 'за', 'под', 'над', 'через', 'для', 'от', 'до', 'у', 'при', 'очень', 'особенно'}
        
        # Получение ключевых слов из характеристик (слова длиннее 2 букв)
        spec_types = list(self.product.specifications.values_list('spec_type__name', flat=True))
        keywords = set()
        for spec in spec_types:
            words = re.findall(r'\w+', spec.lower())
            keywords.update([w for w in words if len(w) > 2])

        found_tags = []
        # Разбиваем на фразы по знакам препинания
        phrases = re.split(r'[,;:.!?\n]+', text)
        
        for phrase in phrases:
            words = re.findall(r'\w+', phrase)
            for i, word in enumerate(words):
                # Если текущее слово - это ключевое слово (или часть характеристики)
                if word in keywords:
                    tag_parts = []
                    
                    # Проверяем 2 слова ДО ключевого во фразе
                    look_back = 2
                    start_idx = max(0, i - look_back)
                    context_before = words[start_idx:i]
                    
                    # Ищем "не" в контексте
                    has_negation = 'не' in context_before
                    
                    # Собираем части тега (игнорируя стоп-слова и ДРУГИЕ ключевые слова)
                    for w in context_before:
                        if w == 'не' or (w not in stop_words and w not in keywords):
                            tag_parts.append(w)
                    
                    tag_parts.append(word)
                    
                    # Проверяем 1 слово ПОСЛЕ ключевого во фразе
                    if i + 1 < len(words):
                        next_word = words[i+1]
                        # Не берем стоп-слова, частицу "не" или другие ключевые слова
                        if next_word not in stop_words and next_word != 'не' and next_word not in keywords:
                            tag_parts.append(next_word)
                    
                    # Если получилось больше одного слова (т.е. описание + характеристика)
                    if len(tag_parts) > 1:
                        # Если есть "не", оно должно быть в начале для ясности
                        if has_negation and 'не' in tag_parts:
                            tag_parts.remove('не')
                            tag_parts.insert(0, 'не')
                        
                        found_tags.append("_".join(tag_parts))

        # Убираем дубликаты и берем первые 5
        unique_tags = []
        for tag in found_tags:
            if tag not in unique_tags:
                unique_tags.append(tag)
        
        return unique_tags[:5]


class Stock(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField("Количество на складе")
    is_available = models.BooleanField("В наличии", default=True)

    class Meta:
        verbose_name = "запись остатков"
        verbose_name_plural = "Остатки"

    def __str__(self):
        return f"Stock for {self.product.name}: {self.quantity}"


class SpecificationType(models.Model):
    """Тип характеристики (например: 'Диагональ экрана', 'Процессор')"""
    name = models.CharField("Название характеристики", max_length=100, unique=True)
    slug = models.SlugField("URL", unique=True, blank=True)

    class Meta:
        verbose_name = "Тип характеристики"
        verbose_name_plural = "Типы характеристик"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while SpecificationType.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductSpecification(models.Model):
    """Значение характеристики для конкретного товара"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='specifications')
    spec_type = models.ForeignKey(
        SpecificationType, on_delete=models.CASCADE, verbose_name="Характеристика")
    value = models.CharField("Значение", max_length=255)

    class Meta:
        verbose_name = "элемент характеристик"
        verbose_name_plural = "Характеристики товаров"
        ordering = ['spec_type__name']
        unique_together = ['product', 'spec_type']

    def __str__(self):
        return f"{self.spec_type.name}: {self.value} ({self.product.name})"

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


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
    image = models.ImageField("Изображение", upload_to='banners/')
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
        "Главное изображение", upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField("Добавлен", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

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
        "Доп. изображение", upload_to='products/gallery/')
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
    name = models.CharField("Имя пользователя", max_length=100)
    rating = models.PositiveSmallIntegerField(
        "Оценка", choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"Review for {self.product.name} by {self.name}"


class Stock(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField("Количество на складе")
    is_available = models.BooleanField("В наличии", default=True)

    class Meta:
        verbose_name = "Остаток"
        verbose_name_plural = "Остатки"

    def __str__(self):
        return f"Stock for {self.product.name}: {self.quantity}"

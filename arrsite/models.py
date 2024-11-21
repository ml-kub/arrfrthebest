from django.db import models
from django.utils import timezone

class User(models.Model):
    iin_bin = models.CharField(max_length=12, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.iin_bin

class CompanyData(models.Model):
    bin_iin = models.CharField(max_length=12, unique=True)
    name = models.CharField(max_length=255)
    registration_date = models.DateField()
    last_updated = models.DateTimeField(auto_now=True)
    
    # Основная информация
    status = models.CharField(max_length=100)
    head_fullname = models.CharField(max_length=255)
    
    # Налоговая информация
    is_ndspayer = models.BooleanField(default=False)
    tax_debt = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Лицензии
    has_licenses = models.BooleanField(default=False)
    licenses_quantity = models.IntegerField(default=0)
    
    # Аналитические показатели
    reliability_index = models.DecimalField(max_digits=5, decimal_places=2)
    financial_activity = models.DecimalField(max_digits=5, decimal_places=2)
    market_presence = models.IntegerField()
    business_stability = models.IntegerField()
    company_age = models.IntegerField()
    
    # JSON поля для хранения детальной информации
    registration_history = models.JSONField(default=dict)
    financial_data = models.JSONField(default=dict)
    contact_info = models.JSONField(default=dict)
    analytics_data = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = 'Данные компании'
        verbose_name_plural = 'Данные компаний'
    
    def __str__(self):
        return f"{self.name} ({self.bin_iin})"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('danger', 'Важное'),
    ]
    
    REPLY_TYPES = [
        ('comment', 'Комментарий'),
        ('completed', 'Исполнено'),
        ('rejected', 'Не исполнено'),
    ]

    company = models.ForeignKey(CompanyData, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='info')
    reply_type = models.CharField(max_length=10, choices=REPLY_TYPES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    is_global = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        if self.is_global:
            return f"Глобальное уведомление: {self.message[:50]}"
        return f"{self.get_type_display()} для {self.company.name}: {self.message[:50]}"

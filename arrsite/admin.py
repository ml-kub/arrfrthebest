from django.contrib import admin
from .models import CompanyData, Notification

@admin.register(CompanyData)
class CompanyDataAdmin(admin.ModelAdmin):
    list_display = ('bin_iin', 'name', 'status', 'registration_date', 'reliability_index', 'last_updated')
    list_filter = ('status', 'is_ndspayer', 'has_licenses')
    search_fields = ('bin_iin', 'name', 'head_fullname')
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('bin_iin', 'name', 'status', 'registration_date', 'head_fullname')
        }),
        ('Налоговая информация', {
            'fields': ('is_ndspayer', 'tax_debt')
        }),
        ('Лицензии', {
            'fields': ('has_licenses', 'licenses_quantity')
        }),
        ('Аналитические показатели', {
            'fields': ('reliability_index', 'financial_activity', 'market_presence', 
                      'business_stability', 'company_age')
        }),
        ('Детальная информация', {
            'classes': ('collapse',),
            'fields': ('registration_history', 'financial_data', 'contact_info', 'analytics_data')
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('company', 'message', 'type', 'created_at', 'is_read', 'created_by')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('company__name', 'company__bin_iin', 'message')
    readonly_fields = ('created_at',)

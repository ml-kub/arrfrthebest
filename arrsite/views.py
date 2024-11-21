from django.shortcuts import render, redirect
from django.contrib import messages
import requests
import json
from datetime import datetime
from .models import CompanyData, Notification, Announcement
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import models
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth import logout
from bs4 import BeautifulSoup

DEFAULT_NEWS_IMAGE = '/static/images/default.png'

DEFAULT_ANALYTICS = {
    'risk_assessment': {'score': 0, 'factors': []},
    'payment_stability': 0,
    'market_diversity': {'score': 0},
    'payment_growth': 0
}

def safe_float(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def get_data_from_api(number):
    """
    Функция для получения данных из API, пробует оба эндпоинта
    """
    token = 'ac9cdef70fdb4c75b09d4ed83db6eae2'
    base_url = 'https://pk.uchet.kz/api/v2'
    headers = {'accept': 'application/json'}

    # Сначала пробуем как ИИН
    iin_url = f'{base_url}/get_iin_info/?token={token}&iin={number}'
    response = requests.get(iin_url, headers=headers)
    
    if response.status_code == 200 and not response.json().get('error'):
        return response.json()

    # Если не получилось, пробуем как БИН
    bin_url = f'{base_url}/get_bin_info/?token={token}&bin={number}'
    response = requests.get(bin_url, headers=headers)
    
    if response.status_code == 200 and not response.json().get('error'):
        return response.json()
    
    return None

def register(request):
    if request.method == 'POST':
        number = request.POST.get('iin_bin')
        if number and number.isdigit() and len(number) == 12:
            try:
                api_data = get_data_from_api(number)
                
                if api_data:
                    # Создаем пользователя, если его нет
                    username = number  # Используем БИН/ИИН как username
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'first_name': api_data.get('name_ru', '')[:30],  # Ограничиваем длину
                            'is_staff': False,
                            'is_active': True
                        }
                    )
                    
                    # Входим как пользователь
                    login(request, user)
                    
                    # Редирект на профиль
                    return redirect('profile', iin_bin=number)
                else:
                    messages.error(request, 'Данные не найдены')
                    return redirect('register')
                    
            except Exception as e:
                print(f"API Error: {str(e)}")
                messages.error(request, 'Ошибка при получении данных')
                return redirect('register')
        else:
            messages.error(request, 'Пожалуйста, введите 12 цифр')
            return redirect('register')
    return render(request, 'register.html')

def profile(request, iin_bin):
    try:
        # Сначала пробуем получить данные из базы
        company = CompanyData.objects.filter(bin_iin=iin_bin).first()
        
        # Проверяем, есть ли данные и не устарели ли они
        if company and (timezone.now() - company.last_updated).days < 1:
            # Используем данные из базы
            context = {
                'company_info': {
                    'name': company.name,
                    'bin_iin': company.bin_iin,  # Добавили БИН/ИИН
                    'registration_date': company.registration_date,
                    'status': company.status,
                    'head_fullname': company.head_fullname,
                    'e080': company.registration_history.get('e080', {}),
                    'actions': company.registration_history.get('actions', []),
                    'stat_gov': company.analytics_data.get('industry_data', {}),
                    'payments_totals': company.financial_data.get('payments', {}),
                },
                'contact_info': company.contact_info,
                'financial_info': {
                    'tax_debt': company.tax_debt,
                    'is_ndspayer': company.is_ndspayer,
                    'pension_contributions': company.financial_data.get('tax_debt_details', {}).get('pension_contribution_arrear', 0),
                    'social_contributions': company.financial_data.get('tax_debt_details', {}).get('social_contribution_arrear', 0),
                    'payments': company.financial_data.get('payments', []),
                },
                'documents': company.registration_history,
                'licenses': {
                    'has_licenses': company.has_licenses,
                    'quantity': company.licenses_quantity,
                    'actual_date': company.analytics_data.get('licenses', {}).get('relevance_date'),
                },
                'inspections': company.analytics_data.get('inspections', {
                    'degree_of_risk': company.analytics_data.get('risk_assessment', {}).get('degree_of_risk'),
                    'calculate_date': company.analytics_data.get('risk_assessment', {}).get('calculate_date'),
                    'start_date': company.analytics_data.get('risk_assessment', {}).get('start_date'),
                    'finish_date': company.analytics_data.get('risk_assessment', {}).get('finish_date'),
                }),
                'goszakup': company.analytics_data.get('goszakup', {}),
                'analytics': {
                    'company_age': company.company_age,
                    'company_age_percentage': min(company.company_age * 10, 100) if company.company_age else 0,
                    'reliability_index': company.reliability_index,
                    'financial_activity': company.financial_activity,
                    'market_presence': company.market_presence,
                    'business_stability': company.business_stability,
                    'tax_compliance': company.analytics_data.get('tax_compliance'),
                    'payment_stability': company.analytics_data.get('payment_stability'),
                    'market_diversity': company.analytics_data.get('market_diversity', {}),
                    'risk_assessment': company.analytics_data.get('risk_assessment', {}),
                    'industry_data': company.analytics_data.get('industry_data', {}),
                    'growth_indicators': company.analytics_data.get('growth_indicators', {}),
                    'notifications': company.notifications.all()
                },
                'legal_status': {
                    'status': company.status,
                    'registration_date': company.registration_date,
                    'last_update': company.registration_history.get('last_rereg_date'),
                },
                'enterprise_classification': company.analytics_data.get('industry_data', {
                    'krp_name': company.analytics_data.get('industry_data', {}).get('krp_name'),
                    'oked_name': company.analytics_data.get('industry_data', {}).get('oked_name'),
                    'kfs_name': company.analytics_data.get('industry_data', {}).get('kfs_name')
                }),
                'registration_history': {
                    'actions': company.registration_history.get('actions', []),
                    'dynamics': company.financial_data.get('payments', [])
                }
            }
            
            # Получаем параметры фильтрации
            reply_type = request.GET.get('reply_type')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            
            # Получаем уведомления с учетом прав доступа
            notifications = Notification.objects.filter(
                models.Q(company=company) | models.Q(is_global=True),
                parent__isnull=True  # Только основные уведомления
            )
            
            if reply_type:
                notifications = notifications.filter(replies__reply_type=reply_type).distinct()
            
            if date_from:
                try:
                    date_from = datetime.strptime(date_from, '%Y-%m-%d')
                    notifications = notifications.filter(created_at__gte=date_from)
                except ValueError:
                    pass
                    
            if date_to:
                try:
                    date_to = datetime.strptime(date_to, '%Y-%m-%d')
                    notifications = notifications.filter(created_at__lte=date_to)
                except ValueError:
                    pass
            
            notifications = notifications.prefetch_related(
                models.Prefetch(
                    'replies',
                    queryset=Notification.objects.filter(
                        models.Q(is_company_reply=False) |  # Показываем все ответы админов
                        models.Q(company=company, is_company_reply=True)  # И только свои ответы для компании
                    )
                ),
                'created_by'
            ).order_by('-created_at')
            
            context['notifications'] = notifications
            context['news'] = get_kapital_news()
            context['announcements'] = Announcement.objects.filter(is_active=True).order_by('-created_at')
            
            return render(request, 'profile.html', context)
            
        # Если данных нет или они устарели, получаем из API
        api_data = get_data_from_api(iin_bin)
        
        if not api_data:
            messages.error(request, 'Данные не найдены в API')
            return redirect('register')
            
        # Безопасное получение и преобразование значений с timezone
        registration_date = None
        try:
            registration_date_str = api_data.get('registration_date', '')
            if registration_date_str:
                # Преобразуем в datetime с timezone
                registration_date = timezone.make_aware(
                    datetime.strptime(registration_date_str, '%Y-%m-%d')
                )
        except (ValueError, TypeError):
            registration_date = timezone.now()

        # Теперь безопасно вычисляем возраст компании
        company_age = 5
        if registration_date:
            delta = timezone.now() - registration_date
            company_age = max(delta.days // 365, 0) if delta.days > 0 else 0

        # Все значения заданы фиксированно
        tax_debt = 0  # Добавили определение tax_debt
        reliability_index = 75
        financial_activity = 70
        market_presence = 65
        business_stability = 80
        company_age_percentage = 60
        tax_compliance = 75
        total_score = 70
        tax_penalty = 0
        age_bonus = 15

        # Обновляем analytics_data с фиксированными значениями
        analytics_data = {
            'risk_assessment': {'score': 65, 'factors': []},
            'payment_stability': 70,
            'market_diversity': {
                'score': 75,
                'has_licenses': bool(api_data.get('elicense', {}).get('has_licenses')),
                'in_goszakup': bool(api_data.get('goszakup', {}).get('is_participant'))
            },
            'growth_indicators': {
                'payment_growth': 65,
                'age_factor': 70,
                'total_score': 75
            }
        }

        # Формируем контекст для шаблона
        context = {
            'company_info': {
                'name': api_data.get('name_ru'),
                'registration_date': registration_date,
                'status': api_data.get('status'),
                'head_fullname': api_data.get('head_fullname'),
                'e080': api_data.get('e080', {}),
                'stat_gov': {
                    'krp_name_ru': api_data.get('stat_gov', {}).get('krp_name_ru'),
                    'kfs_name_ru': api_data.get('stat_gov', {}).get('kfs_name_ru'),
                    'oked_name_ru': api_data.get('stat_gov', {}).get('oked_name_ru'),
                    'kse_name_ru': api_data.get('stat_gov', {}).get('kse_name_ru')
                },
                'payments_totals': {
                    'totals': api_data.get('payments_totals', {}).get('totals', [])
                }
            },
            'contact_info': {
                'address': api_data.get('address_ru'),
                'region': api_data.get('region_kato_code'),
                'kato_code': api_data.get('kato_code'),
            },
            'financial_info': {
                'tax_debt': api_data.get('tax_debt', {}).get('total_tax_arrear', 0),
                'pension_contributions': api_data.get('tax_debt', {}).get('pension_contribution_arrear', 0),
                'social_contributions': api_data.get('tax_debt', {}).get('social_contribution_arrear', 0),
                'payments': api_data.get('payments_totals', {}).get('totals', []),
            },
            'documents': {
                'e034': api_data.get('e034', {}),
                'e080': api_data.get('e080', {}),
                'e083': api_data.get('e083', {})
            },
            'licenses': {
                'has_licenses': api_data.get('elicense', {}).get('has_licenses', False),
                'quantity': api_data.get('elicense', {}).get('quantity'),
                'actual_date': api_data.get('elicense', {}).get('relevance_date'),
            },
            'inspections': {
                'degree_of_risk': api_data.get('degree_of_risk', {}).get('degree_of_risk_ru'),
                'calculate_date': api_data.get('degree_of_risk', {}).get('calculate_date'),
                'start_date': api_data.get('degree_of_risk', {}).get('start_date'),
                'finish_date': api_data.get('degree_of_risk', {}).get('finish_date'),
            },
            'goszakup': {
                'is_participant': api_data.get('goszakup', {}).get('is_participant', False),
                'registration_date': api_data.get('goszakup', {}).get('regdate'),
                'is_unreliable': api_data.get('goszakup_unreliable', {}).get('is_unreliable', False),
            },
            'analytics': {
                'company_age': company_age,
                'company_age_percentage': min(company_age * 10, 100) if company_age else 0,
                'reliability_index': reliability_index,
                'financial_activity': financial_activity,
                'market_presence': int(market_presence),
                'business_stability': int(business_stability),
                
                # Новые показатели
                'tax_compliance': tax_compliance,  # Налоговая дисциплина
                'payment_stability': DEFAULT_ANALYTICS['payment_stability'],
                'market_diversity': analytics_data['market_diversity'],
                'risk_assessment': analytics_data['risk_assessment'],
                'industry_data': {
                    'krp_name': api_data.get('stat_gov', {}).get('krp_name_ru'),
                    'oked_name': api_data.get('stat_gov', {}).get('oked_name_ru'),
                    'kfs_name': api_data.get('stat_gov', {}).get('kfs_name_ru')
                },
                'growth_indicators': analytics_data['growth_indicators'],
                'notifications': get_company_notifications(api_data)  # Новая функция для уведомлений
            },
        }
        
        # Сохраняем или обновляем данные в базе
        company, created = CompanyData.objects.update_or_create(
            bin_iin=iin_bin,
            defaults={
                'name': api_data.get('name_ru', ''),
                'registration_date': registration_date,
                'status': api_data.get('status', ''),
                'head_fullname': api_data.get('head_fullname', ''),
                'is_ndspayer': api_data.get('ndspayer', {}).get('is_ndspayer', False),
                'tax_debt': tax_debt,
                'has_licenses': api_data.get('elicense', {}).get('has_licenses', False),
                'licenses_quantity': api_data.get('elicense', {}).get('quantity', 0),
                'reliability_index': reliability_index,
                'financial_activity': financial_activity,
                'market_presence': market_presence,
                'business_stability': business_stability,
                'company_age': company_age,
                
                # JSON поля
                'registration_history': {
                    'e080': api_data.get('e080', {}),
                    'actions': api_data.get('e080', {}).get('reg_actions_ru', []),
                    'last_rereg_date': api_data.get('e080', {}).get('last_rereg_date_ru')
                },
                'financial_data': {
                    'payments': api_data.get('payments_totals', {}).get('totals', []),
                    'tax_debt_details': api_data.get('tax_debt', {}),
                },
                'contact_info': {
                    'address': api_data.get('address_ru'),
                    'region': api_data.get('region_kato_code'),
                    'kato_code': api_data.get('kato_code'),
                },
                'analytics_data': {
                    'licenses': api_data.get('elicense', {}),
                    'inspections': {
                        'degree_of_risk': api_data.get('degree_of_risk', {}),
                        'inspections_list': api_data.get('inspections', [])
                    },
                    'industry_data': {
                        'krp_name': api_data.get('stat_gov', {}).get('krp_name_ru'),
                        'oked_name': api_data.get('stat_gov', {}).get('oked_name_ru'),
                        'kfs_name': api_data.get('stat_gov', {}).get('kfs_name_ru')
                    },
                    'risk_assessment': analytics_data['risk_assessment'],
                    'company_age': company_age,
                    'company_age_percentage': min(company_age * 10, 100) if company_age else 0,
                    'reliability_index': reliability_index,
                    'financial_activity': financial_activity,
                    'market_presence': market_presence,
                    'business_stability': business_stability,
                    'tax_compliance': tax_compliance,  # Используем вычисленное значение
                    'payment_stability': DEFAULT_ANALYTICS['payment_stability'],
                    'market_diversity': analytics_data['market_diversity'],
                    'risk_assessment': analytics_data['risk_assessment'],
                    'growth_indicators': analytics_data['growth_indicators'],
                    'notifications': get_company_notifications(api_data)  # Новая функция для уведомлений
                }
            }
        )
        
        context['news'] = get_kapital_news()
        return render(request, 'profile.html', context)
        
    except Exception as e:
        print(f"Error in profile view: {str(e)}")
        messages.error(request, 'Ошибка при получении данных')
        return redirect('register')

def get_company_notifications(api_data):
    """Генерирует уведомления на основе данных компании"""
    notifications = []
    
    # Проверка налоговой задолженности
    tax_debt = api_data.get('tax_debt', {}).get('total_tax_arrear', 0)
    if tax_debt > 0:
        notifications.append({
            'type': 'warning',
            'message': f'Имееся налоговая задолженность: {tax_debt:,.2f} ₸',
            'date': datetime.now().strftime('%Y-%m-%d')
        })

    # Проверка лицензий
    licenses = api_data.get('elicense', {})
    if licenses.get('has_licenses'):
        for license in licenses.get('licenses', []):
            if license.get('status') == 'Приостановлена':
                notifications.append({
                    'type': 'danger',
                    'message': f'Лицензия {license.get("number")} приостановлена',
                    'date': license.get('date_suspend')
                })

    # Проверка проверок
    inspections = api_data.get('inspections', [])
    upcoming_inspections = [i for i in inspections if i.get('status') == 'Планируется']
    if upcoming_inspections:
        notifications.append({
            'type': 'info',
            'message': f'Запланировано проверок: {len(upcoming_inspections)}',
            'date': upcoming_inspections[0].get('start_date')
        })

    return notifications

@login_required
def create_notification(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        notification_type = request.POST.get('type', 'info')
        is_global = request.POST.get('is_global') == 'true'
        
        try:
            if is_global:
                notification = Notification.objects.create(
                    message=message,
                    type=notification_type,
                    created_by=request.user,
                    is_global=True
                )
            else:
                company_id = request.POST.get('company')
                company = CompanyData.objects.get(id=company_id)
                notification = Notification.objects.create(
                    company=company,
                    message=message,
                    type=notification_type,
                    created_by=request.user
                )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'})

def logout_view(request):
    logout(request)
    return redirect('register')

@login_required
def get_notifications(request, company_id):
    notifications = Notification.objects.filter(company_id=company_id)
    return JsonResponse({
        'notifications': list(notifications.values(
            'id', 'message', 'type', 'created_at', 'is_read'
        ))
    })

@user_passes_test(lambda u: u.is_staff)
def notifications_management(request):
    # Получаем параметры фильтрации из запроса
    reply_type = request.GET.get('reply_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_companies = request.GET.getlist('companies')  # Получаем список выбранных компаний
    
    # Базовый запрос
    notifications = Notification.objects.filter(parent__isnull=True)
    
    # Применяем фильтры
    if selected_companies:
        notifications = notifications.filter(
            models.Q(company__id__in=selected_companies) |
            models.Q(is_global=True)  # Включаем глобальные уведомления
        )
    
    if reply_type:
        notifications = notifications.filter(replies__reply_type=reply_type).distinct()
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            notifications = notifications.filter(created_at__gte=date_from)
        except ValueError:
            pass
            
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            notifications = notifications.filter(created_at__lte=date_to)
        except ValueError:
            pass
    
    notifications = notifications.prefetch_related(
        'replies',
        'company',
        'created_by'
    ).order_by('-created_at')

    context = {
        'companies': CompanyData.objects.all().order_by('name'),
        'notifications': notifications,
        'is_admin': True,
        'reply_types': Notification.REPLY_TYPES,
        'selected_filters': {
            'reply_type': reply_type,
            'date_from': date_from,
            'date_to': date_to,
            'selected_companies': [int(id) for id in selected_companies] if selected_companies else []
        }
    }
    return render(request, 'notifications_management.html', context)

@login_required
def create_notification_reply(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        parent_id = data.get('parent_id')
        message = data.get('message', '')
        reply_type = data.get('reply_type')
        
        try:
            parent = Notification.objects.get(id=parent_id)
            
            # Получаем компанию по БИН/ИИН текущего пользователя
            company = CompanyData.objects.get(bin_iin=request.user.username)
            
            # Создаем ответ от имени компании
            reply = Notification.objects.create(
                message=message,
                created_by=request.user,
                parent=parent,
                company=company,
                type='info',
                reply_type=reply_type,
                is_company_reply=True
            )
            
            return JsonResponse({
                'status': 'success',
                'reply': {
                    'id': reply.id,
                    'message': reply.message,
                    'created_at': reply.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'reply_type': reply.reply_type,
                    'created_by': company.name
                }
            })
            
        except CompanyData.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Компания не найдена'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Метод не поддерживается'
    })

def safe_calculation(default_value=0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Проверяем на деление на ноль и None
                if result is None or isinstance(result, float) and not result.is_integer():
                    return default_value
                return result
            except (ZeroDivisionError, TypeError, ValueError):
                return default_value
        return wrapper
    return decorator

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('notifications_management')
        else:
            messages.error(request, 'Неверные учетные данные')
            return redirect('admin_login')
            
    return render(request, 'admin_login.html')

def get_kapital_news():
    try:
        # Примерный URL для запросов (заменить на актуальный)
        response = requests.get('https://kapital.kz/finance')
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем все блоки с новостями
        news_items = soup.select('.main-news__item')

        news_list = []
        for item in news_items:
            title_tag = item.select_one('.main-news__name')
            title = title_tag.text.strip() if title_tag else "Без заголовка"
            link = title_tag['href'] if title_tag else None
            link = link if link.startswith("http") else f"https://kapital.kz{link}"

            image_tag = item.select_one('.main-news__img img')
            image = image_tag['src'] if image_tag else DEFAULT_NEWS_IMAGE

            date_tag = item.select_one('.information-article__date')
            date = date_tag.text.strip() if date_tag else "Дата неизвестна"

            description_tag = item.select_one('.main-news__anons')
            description = description_tag.text.strip() if description_tag else "Описание отсутствует"

            tags = [tag.text.strip() for tag in item.select('.main-news__tag a')]

            news_list.append({
                'title': title,
                'link': link,
                'image': image,
                'date': date,
                'description': description,
                'tags': tags
            })

        return news_list

    except Exception as e:
        print(f"Ошибка при парсинге новостей: {e}")
        return []

@user_passes_test(lambda u: u.is_staff)
def create_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        tags = request.POST.get('tags', 'news')  # По умолчанию 'news'
        
        try:
            announcement = Announcement.objects.create(
                title=title,
                description=description,
                image=image,
                tags=tags,
                created_by=request.user,
                is_active=True
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'})

@user_passes_test(lambda u: u.is_staff)
def announcements_management(request):
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_tags = request.GET.getlist('tags')
    
    announcements = Announcement.objects.all()
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            announcements = announcements.filter(created_at__gte=date_from)
        except ValueError:
            pass
            
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            announcements = announcements.filter(created_at__lte=date_to)
        except ValueError:
            pass
            
    if selected_tags:
        announcements = announcements.filter(tags__in=selected_tags)
    
    context = {
        'announcements': announcements,
        'tags': Announcement.TAGS,
        'selected_filters': {
            'date_from': date_from,
            'date_to': date_to,
            'tags': selected_tags
        }
    }
    return render(request, 'announcements_management.html', context)

@user_passes_test(lambda u: u.is_staff)
def get_announcement(request, announcement_id):
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        return JsonResponse({
            'id': announcement.id,
            'title': announcement.title,
            'description': announcement.description,
            'tags': announcement.tags,
            'is_active': announcement.is_active,
            'image': announcement.image.url if announcement.image else None
        })
    except Announcement.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Объявление не найдено'})

@user_passes_test(lambda u: u.is_staff)
def edit_announcement(request, announcement_id):
    if request.method == 'POST':
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            
            announcement.title = request.POST.get('title', announcement.title)
            announcement.description = request.POST.get('description', announcement.description)
            announcement.tags = request.POST.get('tags', announcement.tags)
            announcement.is_active = request.POST.get('is_active') == 'true'
            
            if 'image' in request.FILES:
                announcement.image = request.FILES['image']
            
            announcement.save()
            return JsonResponse({'status': 'success'})
        except Announcement.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Объявление не найдено'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'})

@user_passes_test(lambda u: u.is_staff)
def delete_announcement(request, announcement_id):
    if request.method == 'POST':
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            announcement.delete()
            return JsonResponse({'status': 'success'})
        except Announcement.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Объявление не найдено'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'})

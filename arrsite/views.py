from django.shortcuts import render, redirect
from django.contrib import messages
import requests
import json
from datetime import datetime
from .models import CompanyData, Notification
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import models

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
                    # Вместо рендера напрямую, делаем редирект на profile с параметром
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
                    'company_age_percentage': min(company.company_age * 10, 100),
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
            
            # Получаем все уведомления для компании И глобальные уведомления
            notifications = Notification.objects.filter(
                models.Q(company=company) | models.Q(is_global=True),
                parent__isnull=True  # Получаем только основные уведомления, не ответы
            ).prefetch_related(
                'replies',  # Подгружаем ответы
                'created_by'  # Подгружаем информацию о создателе
            ).order_by('-created_at')
            
            context['notifications'] = notifications
            
            return render(request, 'profile.html', context)
            
        # Если данных нет или они устарели, получаем из API
        api_data = get_data_from_api(iin_bin)
        
        if not api_data:
            messages.error(request, 'Данные не найдены')
            return redirect('register')
            
        # Существующий код обработки API данных
        registration_date = datetime.strptime(api_data.get('registration_date', ''), '%Y-%m-%d')
        company_age = (datetime.now() - registration_date).days // 365
        
        # Расчет индекса надежности (более сложная формула)
        reliability_index = 70  # Базовое значен
        
        # Налоговые задолженности (до -30 баллов)
        tax_debt = api_data.get('tax_debt', {}).get('total_tax_arrear', 0)
        if tax_debt > 0:
            tax_penalty = min(30, (tax_debt / 1000000) * 5)  # 5 баллов за каждый миллион долга
            reliability_index -= tax_penalty
        
        # Возраст компании (до +20 баллов)
        age_bonus = min(20, company_age * 2)
        reliability_index += age_bonus
        
        # Лицензии (+15 баллов)
        if api_data.get('elicense', {}).get('has_licenses', False):
            reliability_index += 15
        
        # История проверок
        inspections = api_data.get('inspections', [])
        if inspections:
            violations = sum(1 for i in inspections if i.get('has_violations', False))
            inspection_penalty = min(20, violations * 5)  # До -20 баллов за нарушения
            reliability_index -= inspection_penalty
        
        # Участие в госзакупках (+10 баллов)
        if api_data.get('goszakup', {}).get('is_participant', False):
            reliability_index += 10
        
        # Расчет финансовой активности (более сложная формула)
        financial_activity = 0
        payments = api_data.get('payments_totals', {}).get('totals', [])
        if payments:
            # Анализируем тренд платежей
            last_year_payments = [payment.get('sum', 0) for payment in payments[-12:]]
            if last_year_payments:
                avg_payment = sum(last_year_payments) / len(last_year_payments)
                payment_trend = sum(1 for p in last_year_payments if p > avg_payment) / len(last_year_payments)
                
                # Базовая активность от объема платежей
                volume_score = min(60, (sum(last_year_payments) / 1000000) * 5)
                
                # Бонус за стабильный рост
                trend_bonus = payment_trend * 40
                
                financial_activity = volume_score + trend_bonus
        
        # Добавляем новые показатели
        market_presence = 0
        if api_data.get('goszakup', {}).get('is_participant', False):
            market_presence += 40
        if api_data.get('elicense', {}).get('has_licenses', False):
            market_presence += 30
        if company_age > 3:
            market_presence += 30
            
        # Расчет бизнес-стабильности
        business_stability = min(100, (
            (reliability_index * 0.4) +  # 40% от индекса надежности
            (financial_activity * 0.3) +  # 30% от финансовой активности
            (market_presence * 0.3)  # 30% от присутствия на рынке
        ))
        
        # Улучшенный расчет индекса надежности
        def calculate_reliability_index():
            base_score = 50  # Базовое значение
            
            # Возраст компании (до 25 баллов)
            age_factor = min(25, (company_age ** 0.7) * 3)
            
            # Налоговая дисциплина (до -35 баллов)
            tax_penalty = 0
            if tax_debt > 0:
                tax_ratio = tax_debt / (sum(last_year_payments) if last_year_payments else 1)
                tax_penalty = min(35, tax_ratio * 100)
            
            # Проверки и нарушения (до -20 баллов)
            inspection_penalty = 0
            if inspections:
                violation_ratio = len([i for i in inspections if i.get('has_violations', False)]) / len(inspections)
                inspection_penalty = violation_ratio * 20
            
            # Лицензии и разрешения (до 15 баллов)
            license_bonus = 0
            if api_data.get('elicense', {}).get('has_licenses', False):
                license_count = api_data.get('elicense', {}).get('quantity', 0)
                license_bonus = min(15, license_count * 5)
            
            # Участие в госзакупках (до 20 баллов)
            goszakup_bonus = 0
            if api_data.get('goszakup', {}).get('is_participant', False):
                contracts = api_data.get('goszakup', {}).get('contracts_count', 0)
                goszakup_bonus = min(20, (contracts ** 0.5) * 5)
            
            # Финансовая стабильность (до 25 баллов)
            financial_bonus = 0
            if last_year_payments:
                payment_stability = calculate_payment_stability(last_year_payments)
                financial_bonus = payment_stability * 25
            
            return max(0, min(100, base_score + age_factor - tax_penalty - inspection_penalty + 
                            license_bonus + goszakup_bonus + financial_bonus))

        # Улучшенный расчет финансовой активности
        def calculate_financial_activity():
            if not payments:
                return 0
            
            last_year_payments = [payment.get('sum', 0) for payment in payments[-12:]]
            if not last_year_payments:
                return 0
            
            # Объем платежей (40%)
            total_payments = sum(last_year_payments)
            volume_score = min(40, (total_payments / 10000000) * 20)
            
            # Стабильность платежей (30%)
            stability_score = calculate_payment_stability(last_year_payments) * 30
            
            # Рост платежей (30%)
            growth_score = calculate_payment_growth(last_year_payments) * 30
            
            return volume_score + stability_score + growth_score

        def calculate_payment_stability(payments):
            if len(payments) < 2:
                return 0
            
            # Рассчитываем коэффициент вариации
            mean = sum(payments) / len(payments)
            variance = sum((x - mean) ** 2 for x in payments) / len(payments)
            std_dev = variance ** 0.5
            cv = std_dev / mean if mean > 0 else 0
            
            # Преобразуем в оценку (меньше вариации = выше стабильность)
            return max(0, min(1, 1 - cv))

        def calculate_payment_growth(payments):
            if len(payments) < 2:
                return 0
            
            # Рассчитываем средний рост
            growth_rates = [(payments[i] - payments[i-1]) / payments[i-1] 
                          if payments[i-1] > 0 else 0 
                          for i in range(1, len(payments))]
            
            avg_growth = sum(growth_rates) / len(growth_rates)
            
            # Преобразуем в оценку от 0 до 1
            return max(0, min(1, (avg_growth + 0.2) / 0.4))  # Нормализуем: 20% рост = 1

        # Расчет рыночного разнообразия
        def calculate_market_diversity():
            score = 0
            
            # Лицензии (30%)
            if api_data.get('elicense', {}).get('has_licenses', False):
                license_count = api_data.get('elicense', {}).get('quantity', 0)
                score += min(30, license_count * 10)
            
            # Госзакупки (30%)
            if api_data.get('goszakup', {}).get('is_participant', False):
                contracts = api_data.get('goszakup', {}).get('contracts_count', 0)
                score += min(30, (contracts ** 0.5) * 10)
            
            # Возраст и стабильность (40%)
            age_score = min(40, company_age * 4)
            score += age_score
            
            return score

        # Расчет оценки рисков
        def calculate_risk_assessment():
            risk_factors = {
                'tax_debt': tax_penalty if 'tax_penalty' in locals() else 0,
                'inspections': inspection_penalty if 'inspection_penalty' in locals() else 0,
                'financial_instability': 100 - calculate_payment_stability(last_year_payments) * 100 if last_year_payments else 50,
                'age_risk': max(0, 50 - company_age * 5)
            }
            
            # Взвешенная оценка рисков
            weighted_risk = (
                risk_factors['tax_debt'] * 0.3 +
                risk_factors['inspections'] * 0.25 +
                risk_factors['financial_instability'] * 0.25 +
                risk_factors['age_risk'] * 0.2
            )
            
            return {
                'score': max(0, 100 - weighted_risk),
                'factors': risk_factors,
                'level': get_risk_level(weighted_risk)
            }

        def get_risk_level(risk_score):
            if risk_score < 20:
                return 'Низкий риск'
            elif risk_score < 40:
                return 'Умеренный риск'
            elif risk_score < 60:
                return 'Повышенный риск'
            else:
                return 'Высокий риск'

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
                'company_age_percentage': min(company_age * 10, 100),
                'reliability_index': calculate_reliability_index(),
                'financial_activity': calculate_financial_activity(),
                'market_presence': int(market_presence),
                'business_stability': int(business_stability),
                
                # Новые показатели
                'tax_compliance': max(0, 100 - (tax_debt / 1000000 * 10)),  # Налоговая дисциплина
                'payment_stability': calculate_payment_stability(last_year_payments) * 100 if 'payment_trend' in locals() else 0,  # Стабильность платежей
                'market_diversity': {
                    'score': calculate_market_diversity(),
                    'has_licenses': api_data.get('elicense', {}).get('has_licenses', False),
                    'in_goszakup': api_data.get('goszakup', {}).get('is_participant', False)
                },
                'risk_assessment': calculate_risk_assessment(),
                'industry_data': {
                    'krp_name': api_data.get('stat_gov', {}).get('krp_name_ru'),
                    'oked_name': api_data.get('stat_gov', {}).get('oked_name_ru'),
                    'kfs_name': api_data.get('stat_gov', {}).get('kfs_name_ru')
                },
                'growth_indicators': {
                    'payment_growth': calculate_payment_growth(last_year_payments) * 100 if 'payment_trend' in locals() else 0,
                    'age_factor': age_bonus,
                    'total_score': round((
                        (reliability_index * 0.4) +
                        (financial_activity * 0.3) +
                        (market_presence * 0.3)
                    ), 1)  # Округляем до одного знака после запятой
                },
                'notifications': get_company_notifications(api_data)  # Новая функция для уведомлений
            },
        }
        
        # Сохраняем или обновляем данные в базе
        company_data = CompanyData.objects.update_or_create(
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
                    'risk_assessment': calculate_risk_assessment(),
                    'company_age': company_age,
                    'company_age_percentage': min(company_age * 10, 100),
                    'reliability_index': reliability_index,
                    'financial_activity': financial_activity,
                    'market_presence': market_presence,
                    'business_stability': business_stability,
                    'tax_compliance': max(0, 100 - (tax_debt / 1000000 * 10)),  # Налоговая дисциплина
                    'payment_stability': calculate_payment_stability(last_year_payments) * 100 if 'payment_trend' in locals() else 0,  # Стабильность платежей
                    'market_diversity': {
                        'score': calculate_market_diversity(),
                        'has_licenses': api_data.get('elicense', {}).get('has_licenses', False),
                        'in_goszakup': api_data.get('goszakup', {}).get('is_participant', False)
                    },
                    'risk_assessment': calculate_risk_assessment(),
                    'growth_indicators': {
                        'payment_growth': calculate_payment_growth(last_year_payments) * 100 if 'payment_trend' in locals() else 0,
                        'age_factor': age_bonus,
                        'total_score': round((
                            (reliability_index * 0.4) +
                            (financial_activity * 0.3) +
                            (market_presence * 0.3)
                        ), 1)  # Округляем до одного знака после запятой
                    },
                    'notifications': get_company_notifications(api_data)  # Новая функция для уведомлений
                }
            }
        )
        
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
        company_id = request.POST.get('company_id')
        message = request.POST.get('message')
        notification_type = request.POST.get('type', 'info')
        
        try:
            company = CompanyData.objects.get(id=company_id)
            notification = Notification.objects.create(
                company=company,
                message=message,
                type=notification_type,
                created_by=request.user
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Уведомление создано'
            })
        except CompanyData.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Компания не найдена'
            }, status=404)
    return JsonResponse({
        'status': 'error',
        'message': 'Метод не поддерживается'
    }, status=405)

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
    context = {
        'companies': CompanyData.objects.all().order_by('name'),
        'notifications': Notification.objects.all().select_related('company', 'created_by').order_by('-created_at')
    }
    return render(request, 'notifications_management.html', context)

@user_passes_test(lambda u: u.is_staff)
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

@login_required
def create_notification_reply(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        parent_id = data.get('parent_id')
        message = data.get('message', '')
        reply_type = data.get('reply_type')
        
        try:
            parent = Notification.objects.get(id=parent_id)
            reply = Notification.objects.create(
                message=message,
                created_by=request.user,
                parent=parent,
                company=parent.company,
                type='info',
                reply_type=reply_type
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Метод не поддерживается'})

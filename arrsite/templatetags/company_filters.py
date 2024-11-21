from django import template

register = template.Library()

@register.filter
def short_company_name(name):
    """
    Удаляет организационно-правовую форму из названия компании
    """
    replacements = [
        'Товарищество с ограниченной ответственностью',
        'ТОО',
        'Акционерное общество',
        'АО',
        'Индивидуальный предприниматель',
        'ИП'
    ]
    
    result = name
    for text in replacements:
        result = result.replace(text, '').strip()
        # Удаляем кавычки в начале и конце
        result = result.strip('"').strip()
    
    return result 
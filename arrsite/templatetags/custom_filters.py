from django import template

register = template.Library()

@register.filter
def format_payment(amount):
    """Форматирует сумму платежа для отображения"""
    try:
        amount = float(amount)
        if amount >= 1000000000:  # миллиарды
            return f"{amount/1000000000:.1f} млрд ₸"
        elif amount >= 1000000:  # миллионы
            return f"{amount/1000000:.1f} млн ₸"
        elif amount >= 1000:  # тысячи
            return f"{amount/1000:.1f} тыс ₸"
        else:
            return f"{amount:.0f} ₸"
    except (ValueError, TypeError):
        return "0 ₸" 

@register.filter
def sub(value, arg):
    """Вычитает arg из value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0 
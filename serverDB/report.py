import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, timezone
import argparse
import sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Регистрируем кириллический шрифт
def register_cyrillic_font():
    try:
        # Пути к возможным расположениям шрифтов
        font_paths = [
            # Windows
            'C:/Windows/Fonts/arial.ttf',
            # Linux
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            # Mac
            '/Library/Fonts/Arial.ttf',
            # Текущая директория
            os.path.join(os.path.dirname(__file__), 'arial.ttf'),
            os.path.join(os.path.dirname(__file__), 'DejaVuSans.ttf')
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                return True
    except Exception as e:
        print(f"Ошибка регистрации шрифта: {e}")
    return False

# Часовой пояс UTC+4
TZ_UTC4 = timezone(timedelta(hours=4))

# Определение словаря кодов погодных условий
CONDITION_CODES = {
    1000: "Ясно",
    1003: "Переменная облачность",
    1006: "Облачно",
    1009: "Пасмурно",
    1030: "Дымка",
    1063: "Возможен дождь",
    1066: "Возможен снег",
    1069: "Возможен мокрый снег",
    1072: "Возможен ледяной дождь",
    1087: "Возможна гроза",
    1114: "Метель",
    1117: "Сильная метель",
    1135: "Туман",
    1147: "Ледяной туман",
    1150: "Легкая морось",
    1153: "Морось",
    1168: "Ледяная морось",
    1171: "Сильная ледяная морось",
    1180: "Легкий дождь",
    1183: "Дождь",
    1186: "Умеренный дождь",
    1189: "Сильный дождь",
    1192: "Ливень",
    1195: "Сильный ливень",
    1198: "Легкий ледяной дождь",
    1201: "Сильный ледяной дождь",
    1204: "Легкий мокрый снег",
    1207: "Сильный мокрый снег",
    1210: "Легкий снег",
    1213: "Снег",
    1216: "Умеренный снег",
    1219: "Сильный снег",
    1222: "Снегопад",
    1225: "Сильный снегопад",
    1237: "Ледяные зерна",
    1240: "Легкий ливень",
    1243: "Сильный ливень",
    1246: "Проливной ливень",
    1249: "Легкий снег с дождем",
    1252: "Сильный снег с дождем",
    1255: "Легкий снегопад",
    1258: "Сильный снегопад",
    1261: "Легкий град",
    1264: "Сильный град",
    1273: "Гроза с дождем",
    1276: "Сильная гроза с дождем",
    1279: "Гроза со снегом",
    1282: "Сильная гроза со снегом"
}

def get_condition_name(code):
    return CONDITION_CODES.get(code, f"Неизвестный код: {code}")

def fetch_day_data(date_str):
    """Получает данные за указанный день в UTC+4"""
    conn = sqlite3.connect('temperature_data.db')
    c = conn.cursor()
    
    # Определяем границы суток в UTC+4
    start_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TZ_UTC4)
    end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
    
    # Конвертируем в UTC
    start_utc = start_dt.astimezone(timezone.utc)
    end_utc = end_dt.astimezone(timezone.utc)
    
    c.execute('''
        SELECT 
            timestamp, 
            offlineTemperature, 
            onlineTemperature, 
            isOpen,
            conditionCode
        FROM readings 
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    ''', (
        int(start_utc.timestamp()),
        int(end_utc.timestamp())
    ))
    
    raw_data = c.fetchall()
    conn.close()
    
    # Конвертируем timestamp в UTC+4
    converted_data = []
    for row in raw_data:
        dt_utc = datetime.fromtimestamp(row[0], timezone.utc)
        dt_local = dt_utc.astimezone(TZ_UTC4)
        time_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
        
        converted_data.append((
            time_str, row[1], row[2], row[3], row[4]
        ))
    
    return converted_data

def calculate_stats(data):
    if not data:
        return None
    
    total_open = sum(row[3] for row in data)
    total_minutes = len(data)
    open_percentage = (total_open / total_minutes) * 100 if total_minutes > 0 else 0
    
    offline_temps = [row[1] for row in data]
    online_temps = [row[2] for row in data]
    condition_codes = [row[4] for row in data]
    
    condition_stats = {}
    for code in condition_codes:
        condition_stats[code] = condition_stats.get(code, 0) + 1
    most_common_condition = max(condition_stats, key=condition_stats.get) if condition_stats else None
    
    return {
        'date': date_str,
        'total_readings': total_minutes,
        'open_minutes': total_open,
        'open_percentage': round(open_percentage, 1),
        'avg_offline': round(sum(offline_temps) / total_minutes, 1) if total_minutes > 0 else 0,
        'min_offline': min(offline_temps) if offline_temps else 0,
        'max_offline': max(offline_temps) if offline_temps else 0,
        'avg_online': round(sum(online_temps) / total_minutes, 1) if total_minutes > 0 else 0,
        'min_online': min(online_temps) if online_temps else 0,
        'max_online': max(online_temps) if online_temps else 0,
        'condition_stats': condition_stats,
        'most_common_condition': most_common_condition
    }

def save_txt_report(stats, filename):
    """Сохраняет отчет в текстовом формате"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"=== Отчет по температуре за {stats['date']} (UTC+4) ===\n\n")
        f.write(f"Всего записей: {stats['total_readings']}\n")
        f.write(f"Время открытого состояния: {stats['open_minutes']} минут ({stats['open_percentage']}%)\n\n")
        
        f.write("Offline температура:\n")
        f.write(f"  Средняя: {stats['avg_offline']:.1f}°C\n")
        f.write(f"  Минимальная: {stats['min_offline']:.1f}°C\n")
        f.write(f"  Максимальная: {stats['max_offline']:.1f}°C\n\n")
        
        f.write("Online температура:\n")
        f.write(f"  Средняя: {stats['avg_online']:.1f}°C\n")
        f.write(f"  Минимальная: {stats['min_online']:.1f}°C\n")
        f.write(f"  Максимальная: {stats['max_online']:.1f}°C\n\n")
        
        f.write("Погодные условия:\n")
        if stats['condition_stats']:
            common_code = stats['most_common_condition']
            f.write(f"  Наиболее частое условие: {common_code} ({get_condition_name(common_code)})\n")
            f.write("  Распределение условий:\n")
            for code, count in sorted(stats['condition_stats'].items()):
                f.write(f"    {get_condition_name(code)} ({code}): {count} записей\n")
        else:
            f.write("  Данные о погодных условиях отсутствуют.\n")
        
        f.write("\n=== Конец отчета ===\n")

def create_pdf_report(stats, image_path, filename):
    """Создает PDF отчет с графиком и статистикой"""
    # Регистрируем кириллический шрифт
    font_registered = register_cyrillic_font()
    
    # Создаем кастомные стили
    styles = getSampleStyleSheet()
    
    # Стиль для заголовка
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName='CyrillicFont' if font_registered else 'Helvetica',
        fontSize=18,
        alignment=1,  # центрирование
        spaceAfter=12
    )
    
    # Стиль для основного текста
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontName='CyrillicFont' if font_registered else 'Helvetica',
        fontSize=12,
        leading=14,
        spaceAfter=6
    )
    
    # Стиль для подзаголовков
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontName='CyrillicFont' if font_registered else 'Helvetica-Bold',
        fontSize=14,
        spaceAfter=6
    )
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    story = []
    
    # Заголовок отчета
    title = f"Отчет по температуре за {stats['date']} (UTC+4)"
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 24))
    
    # Основная статистика
    story.append(Paragraph("<b>Основная статистика:</b>", heading_style))
    
    stats_text = [
        f"<b>Всего записей:</b> {stats['total_readings']}",
        f"<b>Время открытого состояния:</b> {stats['open_minutes']} минут ({stats['open_percentage']}%)",
    ]
    
    for line in stats_text:
        story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 8))
    
    story.append(Spacer(1, 12))
    
    # Статистика по температуре
    story.append(Paragraph("<b>Температура:</b>", heading_style))
    
    temp_text = [
        "<b>Температура в помещении:</b>",
        f"  Средняя: {stats['avg_offline']:.1f}°C",
        f"  Минимальная: {stats['min_offline']:.1f}°C",
        f"  Максимальная: {stats['max_offline']:.1f}°C",
        "",
        "<b>Температура на улице:</b>",
        f"  Средняя: {stats['avg_online']:.1f}°C",
        f"  Минимальная: {stats['min_online']:.1f}°C",
        f"  Максимальная: {stats['max_online']:.1f}°C",
    ]
    
    for line in temp_text:
        story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 6))
    
    story.append(Spacer(1, 12))
    
    # Погодные условия
    story.append(Paragraph("<b>Погодные условия:</b>", heading_style))
    
    if stats['condition_stats']:
        common_code = stats['most_common_condition']
        weather_text = [
            f"<b>Наиболее частое условие:</b> {common_code} ({get_condition_name(common_code)})",
            "<b>Распределение условий:</b>"
        ]
        
        for line in weather_text:
            story.append(Paragraph(line, normal_style))
            story.append(Spacer(1, 6))
        
        for code, count in sorted(stats['condition_stats'].items()):
            story.append(Paragraph(f"    {get_condition_name(code)} ({code}): {count} записей", normal_style))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Данные о погодных условиях отсутствуют.", normal_style))
    
    story.append(Spacer(1, 24))
    
    # Добавляем график
    story.append(Paragraph("<b>Графики показателей:</b>", heading_style))
    story.append(Spacer(1, 12))
    img = Image(image_path, width=6*inch, height=4.5*inch)
    story.append(img)
    
    # Создаем PDF
    doc.build(story)

def plot_data(data, date_str, save_only=False):
    """Создает графики температуры и состояния, возвращает путь к файлу"""
    if not data:
        print("Нет данных для отображения")
        return None
    
    plt.figure(figsize=(12, 12))
    
    timestamps = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in data]
    offline_temp = [row[1] for row in data]
    online_temp = [row[2] for row in data]
    is_open = [row[3] for row in data]
    condition_codes = [row[4] for row in data]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    
    # График температур
    ax1.plot(timestamps, offline_temp, 'b-', label="Offline Temperature")
    ax1.plot(timestamps, online_temp, 'r-', label="Online Temperature")
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title(f"Temperature Monitoring - {date_str} (UTC+4)")
    ax1.legend()
    ax1.grid(True)
    
    # График состояния
    ax2.step(timestamps, is_open, 'g-', where='post')
    ax2.set_ylabel("State (0=Closed, 1=Open)")
    ax2.set_title("Open/Closed State")
    ax2.set_ylim(-0.1, 1.1)
    ax2.yaxis.set_ticks([0, 1])
    ax2.grid(True)
    
    # График кодов погоды
    ax3.stem(timestamps, condition_codes, linefmt='b-', markerfmt='bo', basefmt=' ')
    ax3.set_ylabel("Condition Code")
    ax3.set_title("Weather Conditions")
    ax3.grid(True)
    
    # Форматирование времени (UTC+4)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=TZ_UTC4))
    ax3.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Сохранение графика
    image_filename = f"temperature_report_{date_str}.png"
    plt.savefig(image_filename)
    
    if not save_only:
        plt.show()
    
    plt.close()
    return image_filename

def generate_report(date_arg=None):
    global date_str
    
    # Определение даты отчета (UTC+4)
    if date_arg is None:
        now = datetime.now(TZ_UTC4)
        date_str = now.strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(date_arg, "%Y-%m-%d")
            date_str = date_arg
        except ValueError:
            print("Ошибка: неверный формат даты. Используйте ГГГГ-ММ-ДД.")
            return
    
    print(f"Генерация отчета за {date_str} (UTC+4)...")
    data = fetch_day_data(date_str)
    
    if not data:
        print(f"Данные за {date_str} не найдены.")
        return
    
    stats = calculate_stats(data)
    
    # Вывод статистики в консоль
    print("\n=== Статистика за день ===")
    print(f"Дата: {stats['date']} (UTC+4)")
    print(f"Всего записей: {stats['total_readings']}")
    print(f"Время открытого состояния: {stats['open_minutes']} минут ({stats['open_percentage']}%)")
    print("\nOffline температура:")
    print(f"  Средняя: {stats['avg_offline']:.1f}°C")
    print(f"  Минимальная: {stats['min_offline']:.1f}°C")
    print(f"  Максимальная: {stats['max_offline']:.1f}°C")
    print("\nOnline температура:")
    print(f"  Средняя: {stats['avg_online']:.1f}°C")
    print(f"  Минимальная: {stats['min_online']:.1f}°C")
    print(f"  Максимальная: {stats['max_online']:.1f}°C")
    print("\nПогодные условия:")
    if stats['condition_stats']:
        common_code = stats['most_common_condition']
        print(f"  Наиболее частое условие: {common_code} ({get_condition_name(common_code)})")
        print("  Распределение условий:")
        for code, count in sorted(stats['condition_stats'].items()):
            print(f"    {get_condition_name(code)} ({code}): {count} записей")
    else:
        print("  Данные о погодных условиях отсутствуют.")
    
    # Генерация графиков и отчетов
    image_filename = plot_data(data, date_str, save_only=True)
    
    # Сохранение текстового отчета
    txt_filename = f"temperature_report_{date_str}.txt"
    save_txt_report(stats, txt_filename)
    print(f"\nТекстовый отчет сохранен как: {txt_filename}")
    
    # Генерация PDF отчета
    pdf_filename = f"temperature_report_{date_str}.pdf"
    create_pdf_report(stats, image_filename, pdf_filename)
    print(f"PDF отчет сохранен как: {pdf_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate temperature report')
    parser.add_argument('date', nargs='?', help='Date in YYYY-MM-DD format')
    args = parser.parse_args()
    
    generate_report(args.date)
import os
import datetime
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = os.environ.get('GMAIL_USER', '')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
DESTINATARIOS = os.environ.get('DESTINATARIOS', '').split(',')
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')

if not GMAIL_USER or not GMAIL_APP_PASSWORD:
    print("ERROR: Faltan credenciales (GMAIL_USER o GMAIL_APP_PASSWORD)")
    exit(1)

if not NEWS_API_KEY:
    print("ERROR: Falta NEWS_API_KEY")
    exit(1)

hoy = datetime.datetime.now()
ayer = hoy - datetime.timedelta(days=1)

print(f"Buscando noticias desde {ayer.strftime('%Y-%m-%d')} hasta {hoy.strftime('%Y-%m-%d')}\n")

keywords_busqueda = [
    "Argentina economy",
    "Argentina politics",
    "Argentina peso dollar",
    "Argentina inflation BCRA",
    "Argentina bonds debt",
    "Milei Argentina",
    "Argentina central bank",
    "Argentina IMF"
]

todas_noticias = []

print("🔍 Buscando noticias en News API...")

for keyword in keywords_busqueda:
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': keyword,
            'from': ayer.strftime('%Y-%m-%d'),
            'to': hoy.strftime('%Y-%m-%d'),
            'language': 'es,en',
            'sortBy': 'publishedAt',
            'apiKey': NEWS_API_KEY,
            'pageSize': 15
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            for article in articles:
                if article.get('title') and article.get('url'):
                    try:
                        fecha_pub = datetime.datetime.strptime(
                            article['publishedAt'], 
                            '%Y-%m-%dT%H:%M:%SZ'
                        )
                        
                        todas_noticias.append({
                            'titulo': article['title'],
                            'descripcion': article.get('description', ''),
                            'link': article['url'],
                            'fecha': fecha_pub.strftime('%Y-%m-%d %H:%M'),
                            'fuente': article.get('source', {}).get('name', 'Desconocida')
                        })
                    except:
                        pass
            
            print(f"  ✓ {keyword}: {len(articles)} artículos")
        else:
            print(f"  ⚠️ Error en {keyword}: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error en {keyword}: {str(e)}")

titulos_vistos = set()
noticias_unicas = []
for noticia in todas_noticias:
    if noticia['titulo'] not in titulos_vistos:
        noticias_unicas.append(noticia)
        titulos_vistos.add(noticia['titulo'])

noticias_unicas.sort(key=lambda x: x['fecha'], reverse=True)

print(f"\n📰 Total encontradas: {len(noticias_unicas)} noticias\n")

if noticias_unicas:
    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>📰 Resumen de Noticias - Argentina & Mercados</h2>
        <p><strong>Fecha:</strong> {hoy.strftime('%d/%m/%Y %H:%M')}</p>
        <p><strong>Período:</strong> Últimas 24 horas</p>
        <hr>
    """
    
    for i, noticia in enumerate(noticias_unicas[:30], 1):
        descripcion = noticia.get('descripcion', '')
        cuerpo_html += f"""
        <p>
            <strong>{i}. [{noticia['fecha']}]</strong> {noticia['titulo']}<br>
            {f'<em>{descripcion}</em><br>' if descripcion else ''}
            <small>Fuente: {noticia['fuente']}</small><br>
            <a href="{noticia['link']}" target="_blank">Leer más →</a>
        </p>
        """
    
    cuerpo_html += """
        <hr>
        <p><small>Este resumen fue generado automáticamente usando News API.</small></p>
    </body>
    </html>
    """
    
    try:
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = f"📰 Resumen de Noticias - {hoy.strftime('%d/%m/%Y')}"
        mensaje["From"] = GMAIL_USER
        mensaje["To"] = ", ".join(DESTINATARIOS)
        
        parte_html = MIMEText(cuerpo_html, "html")
        mensaje.attach(parte_html)
        
        servidor = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        servidor.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        servidor.sendmail(GMAIL_USER, DESTINATARIOS, mensaje.as_string())
        servidor.quit()
        
        print("✅ ¡Email enviado exitosamente!")
        print(f"   Destinatarios: {', '.join(DESTINATARIOS)}")
        
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")
        exit(1)
        
else:
    print("❌ No se encontraron noticias para enviar.")

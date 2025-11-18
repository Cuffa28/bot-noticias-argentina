import os
import feedparser
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
    print("ERROR: Faltan credenciales")
    exit(1)

hoy = datetime.datetime.now()
hace_2_dias = hoy - datetime.timedelta(days=2)

print(f"Buscando noticias desde {hace_2_dias.strftime('%Y-%m-%d')} hasta {hoy.strftime('%Y-%m-%d')}\n")

todas_noticias = []

# PARTE 1: Intentar News API (fuentes internacionales)
if NEWS_API_KEY:
    print("🔍 Intentando News API (Bloomberg, Reuters, Financial Times)...")
    keywords_busqueda = [
        "Argentina economy",
        "Argentina politics",
        "Argentina peso",
        "Argentina inflation",
        "Milei Argentina"
    ]
    
    for keyword in keywords_busqueda:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': keyword,
                'from': hace_2_dias.strftime('%Y-%m-%d'),
                'to': hoy.strftime('%Y-%m-%d'),
                'language': 'es,en',
                'sortBy': 'publishedAt',
                'apiKey': NEWS_API_KEY,
                'pageSize': 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            
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
                
                print(f"  ✓ News API - {keyword}: {len(articles)} artículos")
            else:
                print(f"  ⚠️ News API - {keyword}: Error {response.status_code}")
        except Exception as e:
            print(f"  ⚠️ News API - {keyword}: {str(e)[:50]}")
else:
    print("⚠️ NEWS_API_KEY no configurada, usando solo RSS")

# PARTE 2: RSS argentino (siempre como respaldo)
print("\n🔍 Buscando en fuentes RSS argentinas...")

feeds_rss = {
    "Ámbito Financiero": "https://www.ambito.com/rss/economia.xml",
    "Cronista - Economía": "https://www.cronista.com/economia/feed/",
    "Cronista - Finanzas": "https://www.cronista.com/finanzas/feed/",
    "Infobae Economía": "https://www.infobae.com/economia/feed/",
    "La Nación Economía": "https://www.lanacion.com.ar/economia/rss/",
    "Google News - Argentina": "https://news.google.com/rss/search?q=argentina+economia+when:2d&hl=es-AR",
    "Google News - Dólar": "https://news.google.com/rss/search?q=dolar+argentina+when:2d&hl=es-AR",
    "Google News - BCRA": "https://news.google.com/rss/search?q=bcra+when:2d&hl=es-AR",
}

palabras_clave = [
    "argentina", "mercado", "dólar", "bono", "inflación",
    "cepo", "blue", "precio", "economía", "bcra",
    "caputo", "milei", "reforma", "ley", "impuesto",
    "reservas", "deuda", "dolar", "peso"
]

def extraer_de_rss(url_feed, nombre_fuente):
    noticias_temp = []
    try:
        feed = feedparser.parse(url_feed)
        for entry in feed.entries:
            try:
                fecha_pub = datetime.datetime(*entry.published_parsed[:6])
                if fecha_pub >= hace_2_dias:
                    titulo = entry.title.lower()
                    if any(palabra in titulo for palabra in palabras_clave):
                        noticias_temp.append({
                            'titulo': entry.title,
                            'descripcion': '',
                            'link': entry.link,
                            'fecha': fecha_pub.strftime('%Y-%m-%d %H:%M'),
                            'fuente': nombre_fuente
                        })
            except:
                pass
    except:
        pass
    return noticias_temp

for nombre, url in feeds_rss.items():
    noticias = extraer_de_rss(url, nombre)
    todas_noticias.extend(noticias)
    if noticias:
        print(f"  ✓ {nombre}: {len(noticias)} noticias")

# Eliminar duplicados
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
        <p><strong>Período:</strong> Últimas 48 horas</p>
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
        <p><small>Este resumen fue generado automáticamente (News API + RSS).</small></p>
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

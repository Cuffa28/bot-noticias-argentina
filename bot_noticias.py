import os
import feedparser
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = os.environ.get('GMAIL_USER', '')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', '')
DESTINATARIOS = os.environ.get('DESTINATARIOS', '').split(',')

if not GMAIL_USER or not GMAIL_APP_PASSWORD:
    print("ERROR: Faltan credenciales")
    exit(1)

hoy = datetime.datetime.now()
hace_2_dias = hoy - datetime.timedelta(days=2)

print(f"Buscando noticias desde {hace_2_dias.strftime('%Y-%m-%d')} hasta {hoy.strftime('%Y-%m-%d')}\n")

feeds_rss = {
    "Ámbito Financiero": "https://www.ambito.com/rss/economia.xml",
    "Cronista - Economía": "https://www.cronista.com/economia/feed/",
    "Cronista - Finanzas": "https://www.cronista.com/finanzas/feed/",
    "Infobae Economía": "https://www.infobae.com/economia/feed/",
    "Google News - BCRA": "https://news.google.com/rss/search?q=bcra+reservas+when:2d&hl=es-AR",
    "Google News - Bonos": "https://news.google.com/rss/search?q=bonos+argentina+when:2d&hl=es-AR",
    "Google News - Repo Pases": "https://news.google.com/rss/search?q=repo+pases+bcra+when:2d&hl=es-AR",
    "Google News - Mercados": "https://news.google.com/rss/search?q=mercado+financiero+argentina+when:2d&hl=es-AR",
}

palabras_clave_incluir = [
    "repo", "pase", "lebac", "lecap", "tasa",
    "bono", "bonos", "al30", "gd30", "ae38", "treasury",
    "reservas", "bcra", "central",
    "colocación", "licitación", "subasta",
    "riesgo país", "spread", "paridad",
    "reestructuración", "deuda externa",
    "caputo", "milei", "política monetaria",
    "inflación", "ipc", 
    "superávit", "déficit", "fiscal",
    "fmi", "desembolso"
]

palabras_clave_excluir = [
    "dólar blue", "blue cerró", "blue cotiza", "dólar oficial",
    "dólar hoy", "cotización del dólar", "valor del dólar",
    "precio del dólar", "dólar mep", "dólar ccl", 
    "dólar mayorista", "dólar minorista",
    "euro hoy", "euro cotiza", "real cotiza",
    "pronóstico del dólar", "qué pasará con el dólar",
    "a cuánto cotiza", "cuánto está el dólar"
]

def extraer_de_rss(url_feed, nombre_fuente):
    noticias_temp = []
    try:
        feed = feedparser.parse(url_feed)
        for entry in feed.entries:
            try:
                fecha_pub = datetime.datetime(*entry.published_parsed[:6])
                if fecha_pub >= hace_2_dias:
                    titulo = entry.title
                    titulo_lower = titulo.lower()
                    
                    # Primero verificar si tiene alguna palabra a excluir
                    tiene_excluir = any(palabra in titulo_lower for palabra in palabras_clave_excluir)
                    if tiene_excluir:
                        continue
                    
                    # Luego verificar si tiene alguna palabra a incluir
                    tiene_incluir = any(palabra in titulo_lower for palabra in palabras_clave_incluir)
                    if tiene_incluir:
                        noticias_temp.append({
                            'titulo': titulo,
                            'link': entry.link,
                            'fecha': fecha_pub.strftime('%Y-%m-%d %H:%M'),
                            'fuente': nombre_fuente
                        })
            except:
                pass
    except:
        pass
    return noticias_temp

todas_noticias = []

print("🔍 Buscando en fuentes RSS...")
for nombre, url in feeds_rss.items():
    noticias = extraer_de_rss(url, nombre)
    todas_noticias.extend(noticias)
    if noticias:
        print(f"  ✓ {nombre}: {len(noticias)} noticias")

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
    
    for i, noticia in enumerate(noticias_unicas[:25], 1):
        cuerpo_html += f"""
        <p>
            <strong>{i}. [{noticia['fecha']}]</strong> {noticia['titulo']}<br>
            <small>Fuente: {noticia['fuente']}</small><br>
            <a href="{noticia['link']}" target="_blank">Leer más →</a>
        </p>
        """
    
    cuerpo_html += """
        <hr>
        <p><small>Este resumen fue generado automáticamente - Noticias financieras filtradas.</small></p>
    </body>
    </html>
    """
    
    try:
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = f"📰 Resumen Financiero - {hoy.strftime('%d/%m/%Y')}"
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

import os
import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ldap_utils import load_env, get_emails_for_role

# Cargar variables de entorno
load_env()

DB_FILE = os.path.join(os.path.dirname(__file__), "canibalizacion.db")

def parse_division(path: str) -> str:
    """Parsea la división a partir de la ruta jerárquica del equipo"""
    if not path:
        return "Otros"
    parts = [p.strip().upper() for p in path.split(">")]
    first_part = parts[0] if parts else ""
    if "DIVISION A" in first_part or "DIV A" in first_part or "DIV-A" in first_part:
        return "DIV- A"
    elif "DIVISION B" in first_part or "DIV B" in first_part or "DIV-B" in first_part:
        return "DIV- B"
    elif "FACILITIES" in first_part:
        return "Facilities"
    elif "UTILITIES" in first_part:
        return "Utilities"
    return "Otros"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def enviar_correo(subject: str, html_body: str, to_emails: list):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.office365.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "system_metrics@goodyear.com")
    smtp_pass = os.environ.get("SMTP_PASS", "medicioncontrolanalisis015")
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    smtp_use_ssl = os.environ.get("SMTP_USE_SSL", "False").lower() in ("true", "1", "yes")

    to_emails = [email.strip() for email in to_emails if email and "@" in email]
    if not to_emails:
        print("WARNING: No hay destinatarios válidos para el correo.")
        return False
        
    print(f"Enviando correo '{subject}' a {to_emails}...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_emails)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    try:
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            
        if smtp_use_tls:
            server.starttls()
            
        if smtp_pass:
            server.login(smtp_user, smtp_pass)
            
        server.sendmail(smtp_user, to_emails, msg.as_string())
        server.quit()
        print("¡Correo enviado con éxito!")
        return True
    except Exception as e:
        print(f"ERROR: No se pudo enviar el correo por SMTP: {e}")
        return False

def generar_reporte_html(titulo: str, subtitulo: str, stats: dict, delays: list) -> str:
    """Genera la plantilla de correo HTML ejecutivo para los reportes semanales"""
    # Filas de la tabla de resumen
    resumen_rows = ""
    divisions = ["DIV- A", "DIV- B", "Facilities", "Utilities"]
    
    total_equipos = 0
    total_con = 0
    total_sin = 0
    total_ontime = 0
    total_atrasadas = 0
    
    for div in divisions:
        div_data = stats.get(div, {"equipos": set(), "con_codigo": 0, "sin_codigo": 0, "ontime": 0, "atrasadas": 0})
        num_equipos = len(div_data["equipos"])
        
        total_equipos += num_equipos
        total_con += div_data["con_codigo"]
        total_sin += div_data["sin_codigo"]
        total_ontime += div_data["ontime"]
        total_atrasadas += div_data["atrasadas"]
        
        resumen_rows += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #d1d5db; font-weight: bold;">{div}</td>
            <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center;">{num_equipos}</td>
            <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center;">{div_data['con_codigo']}</td>
            <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center;">{div_data['sin_codigo']}</td>
            <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center; color: #15803d; font-weight: bold;">{div_data['ontime']}</td>
            <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center; color: #b91c1c; font-weight: bold;">{div_data['atrasadas']}</td>
        </tr>
        """
        
    # Fila de TOTAL
    resumen_rows += f"""
    <tr style="background-color: #fef3c7; font-weight: bold;">
        <td style="padding: 10px; border: 1px solid #d1d5db;">TOTAL</td>
        <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center;">{total_equipos}</td>
        <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center;">{total_con}</td>
        <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center;">{total_sin}</td>
        <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center; color: #15803d;">{total_ontime}</td>
        <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center; color: #b91c1c;">{total_atrasadas}</td>
    </tr>
    """

    # Filas de la tabla de detalles de atrasos
    delay_rows = ""
    if not delays:
        delay_rows = """
        <tr>
            <td colspan="5" style="padding: 15px; border: 1px solid #d1d5db; text-align: center; color: #6b7280; font-style: italic;">
                No hay retrasos de cumplimiento registrados.
            </td>
        </tr>
        """
    else:
        for d in delays:
            delay_rows += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #d1d5db; font-weight: bold;">{d['maq']}</td>
                <td style="padding: 10px; border: 1px solid #d1d5db;">{d['area']}</td>
                <td style="padding: 10px; border: 1px solid #d1d5db;">{d['desc']}</td>
                <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center; color: #b91c1c; font-weight: bold;">{d['fecha']}</td>
                <td style="padding: 10px; border: 1px solid #d1d5db; text-align: center; background-color: #fee2e2; color: #b91c1c; font-weight: bold;">{d['dias']}</td>
            </tr>
            """

    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; color: #1f2937; margin: 0; padding: 0; }}
            .container {{ max-width: 750px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-top: 6px solid #FFDE00; }}
            .header {{ background-color: #111827; color: #ffffff; padding: 25px; text-align: center; }}
            .header h2 {{ margin: 0; font-size: 22px; font-weight: 600; letter-spacing: 0.5px; }}
            .header p {{ margin: 5px 0 0 0; font-size: 14px; color: #9ca3af; }}
            .content {{ padding: 25px; }}
            .section-title {{ font-size: 16px; font-weight: 600; color: #111827; margin-top: 25px; margin-bottom: 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .footer {{ background-color: #f9fafb; text-align: center; padding: 20px; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{titulo}</h2>
                <p>{subtitulo}</p>
            </div>
            <div class="content">
                <div class="section-title">Resumen Semanal de Canibalización</div>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 13px;">
                    <thead>
                        <tr style="background-color: #111827; color: #ffffff;">
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: left;">Área</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 12%;">Equipos</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 18%;">Partes con código</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 18%;">Partes sin código</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 15%;">OnTime</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 15%;">Atrasadas</th>
                        </tr>
                    </thead>
                    <tbody>
                        {resumen_rows}
                    </tbody>
                </table>
                
                <div class="section-title" style="color: #b91c1c;">Detalle de atrasos en cumplimiento</div>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="background-color: #b91c1c; color: #ffffff;">
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: left; width: 20%;">Maq</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: left; width: 25%;">Área</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: left; width: 25%;">Desc Corta</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 18%;">Fecha Compromiso</th>
                            <th style="padding: 10px; border: 1px solid #d1d5db; text-align: center; width: 12%;">Días Atraso</th>
                        </tr>
                    </thead>
                    <tbody>
                        {delay_rows}
                    </tbody>
                </table>
            </div>
            <div class="footer">
                <strong>Gestión de Repuestos</strong><br>
                Planta Goodyear – Chile
            </div>
        </div>
    </body>
    </html>
    """

def compile_stats_and_delays(records_to_summarize, all_records):
    """Compila las estadísticas por división y la lista de retrasos"""
    stats = {}
    divisions = ["DIV- A", "DIV- B", "Facilities", "Utilities"]
    for div in divisions:
        stats[div] = {
            "equipos": set(),
            "con_codigo": 0,
            "sin_codigo": 0,
            "ontime": 0,
            "atrasadas": 0
        }
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Compilar estadísticas
    for r in records_to_summarize:
        div = parse_division(r["maquina_donante"])
        if div not in stats:
            continue
            
        stats[div]["equipos"].add(r["maquina_donante"])
        
        # Con/Sin código
        codigo_bodega = r.get("codigo_bodega") or ""
        if codigo_bodega.strip():
            stats[div]["con_codigo"] += 1
        else:
            stats[div]["sin_codigo"] += 1
            
        # OnTime vs Atrasadas
        normalizado = bool(r["normalizado"])
        fecha_compromiso = r["tiempo_reposicion"]
        
        if normalizado:
            stats[div]["ontime"] += 1
        else:
            if fecha_compromiso < today_str:
                stats[div]["atrasadas"] += 1
            else:
                stats[div]["ontime"] += 1
                
    # 2. Compilar detalles de atrasos (de todos los registros pendientes en la DB)
    delays = []
    for r in all_records:
        if not bool(r["normalizado"]):
            fecha_compromiso = r["tiempo_reposicion"]
            if fecha_compromiso and fecha_compromiso < today_str:
                # Calcular días de retraso
                try:
                    fecha_c = datetime.strptime(fecha_compromiso, "%Y-%m-%d")
                    dias_atraso = (datetime.now() - fecha_c).days
                except:
                    dias_atraso = 0
                
                # Formatear Área y Máquina
                path_parts = [p.strip() for p in r["maquina_donante"].split(">")]
                maq = path_parts[-1] if path_parts else "N/A"
                area = " > ".join(path_parts[:-1]) if len(path_parts) > 1 else "N/A"
                
                delays.append({
                    "maq": maq,
                    "area": area,
                    "desc": (r["repuesto_nombre"] or "Sin nombre")[:30],
                    "fecha": fecha_compromiso,
                    "dias": max(0, dias_atraso)
                })
                
    # Ordenar retrasos de mayor a menor días de atraso
    delays.sort(key=lambda x: x["dias"], reverse=True)
    return stats, delays

def ejecutar_reportes():
    print("Iniciando generación de reportes semanales...")
    if not os.path.exists(DB_FILE):
        print(f"ERROR: No existe la base de datos en {DB_FILE}")
        return
        
    conn = get_db_connection()
    all_records = [dict(row) for row in conn.execute("SELECT * FROM registros").fetchall()]
    conn.close()
    
    # Rango de última semana para Item 2
    date_7_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    weekly_records = [r for r in all_records if r["fecha_registro"] >= date_7_days_ago]
    
    print(f"Registros totales en DB: {len(all_records)}")
    print(f"Registros creados en los últimos 7 días: {len(weekly_records)}")
    
    # ----------------------------------------------------
    # ITEM 2: Reporte Semanal de Partes Sustraídas (Últimos 7 días)
    # ----------------------------------------------------
    
    # a. Distribución por Área (Planners y Técnicos de la división)
    divisions = ["DIV- A", "DIV- B", "Facilities", "Utilities"]
    for div in divisions:
        div_records = [r for r in weekly_records if parse_division(r["maquina_donante"]) == div]
        
        # Recolectar correos únicos
        recipients = []
        for r in div_records:
            if r.get("correo_responsable"):
                recipients.append(r["correo_responsable"])
            if r.get("correo_tecnico"):
                recipients.append(r["correo_tecnico"])
                
        recipients = list(set([e.strip() for e in recipients if e and "@" in e]))
        
        if recipients and div_records:
            div_stats, div_delays = compile_stats_and_delays(div_records, all_records)
            html = generar_reporte_html(
                titulo="Resumen Semanal de Canibalización",
                subtitulo=f"Reporte del Área/División: {div}",
                stats=div_stats,
                delays=[d for d in div_delays if parse_division(d["area"]) == div]
            )
            enviar_correo(f"Resumen Semanal de Canibalización - Área {div}", html, recipients)
            
    # b. De División: ETL
    etl_emails = get_emails_for_role('etl')
    if etl_emails and weekly_records:
        etl_stats, etl_delays = compile_stats_and_delays(weekly_records, all_records)
        html = generar_reporte_html(
            titulo="Resumen Semanal de Canibalización",
            subtitulo="Consolidado Planta - Reporte para ETL",
            stats=etl_stats,
            delays=etl_delays
        )
        enviar_correo("Resumen Semanal de Canibalización - Consolidado ETL", html, etl_emails)
        
    # c. De Planta: Planificador de Bodega (solo con código de bodega)
    bodega_emails = get_emails_for_role('bodega')
    # Filtrar registros semanales que tengan código de bodega
    bodega_records = [r for r in weekly_records if (r.get("codigo_bodega") or "").strip()]
    if bodega_emails and bodega_records:
        bodega_stats, bodega_delays = compile_stats_and_delays(bodega_records, all_records)
        html = generar_reporte_html(
            titulo="Resumen Semanal de Canibalización",
            subtitulo="Consolidado de Partes con Código de Bodega - Reporte para Planificador de Bodega",
            stats=bodega_stats,
            delays=[d for d in bodega_delays if d["maq"] in [r["maquina_donante"].split(">")[-1].strip() for r in bodega_records]]
        )
        enviar_correo("Resumen Semanal de Canibalización - Partes con Código de Bodega", html, bodega_emails)

    # ----------------------------------------------------
    # ITEM 3: Reporte Semanal de SIN REPOSICIÓN (Pendientes y Retrasadas)
    # ----------------------------------------------------
    gerente_emails = get_emails_for_role('gerente')
    pending_records = [r for r in all_records if not bool(r["normalizado"])]
    
    if gerente_emails and pending_records:
        gerente_stats, gerente_delays = compile_stats_and_delays(pending_records, all_records)
        html = generar_reporte_html(
            titulo="Resumen Semanal de Canibalizaciones SIN REPOSICIÓN",
            subtitulo="Reporte Ejecutivo para Gerente de Ingeniería",
            stats=gerente_stats,
            delays=gerente_delays
        )
        enviar_correo("Resumen Semanal de Canibalizaciones SIN REPOSICIÓN", html, gerente_emails)
        
    print("Finalizó la distribución de reportes semanales.")

if __name__ == "__main__":
    ejecutar_reportes()

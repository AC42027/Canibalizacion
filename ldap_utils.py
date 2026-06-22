import os
from ldap3 import Server, Connection, SUBTREE

def load_env():
    """Carga de forma manual las variables de entorno desde el archivo .env"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val

def get_ldap_connection():
    """Establece y retorna una conexión bind a LDAP usando la configuración de .env"""
    load_env()
    server_address = os.environ.get("LDAP_SERVER", "10.107.194.214")
    port = int(os.environ.get("LDAP_PORT", "3268"))
    user = os.environ.get("LDAP_USER", "la\\LDA1425")
    password = os.environ.get("LDAP_PASS", "teBa9GFkCJvZrVPtHQDYLGyL")
    
    # Resolver problema de barras invertidas duplicadas en la cadena cargada
    if "\\\\" in user:
        user = user.replace("\\\\", "\\")
        
    # Forzar puerto seguro 3269 (Global Catalog SSL) si el puerto es 3268 para evitar bloqueos/hangs
    if port == 3268:
        port = 3269
        
    use_ssl = True
    server = Server(server_address, port=port, use_ssl=use_ssl, connect_timeout=5)
    conn = Connection(server, user=user, password=password, auto_bind=True, receive_timeout=5)
    return conn

def get_emails_for_role(role_name: str) -> list:
    """
    Retorna la lista de correos electrónicos únicos registrados en LDAP para un rol determinado.
    Los roles soportados son:
      - 'planner': Planners en Santiago
      - 'etl': Ingenieros/Coordinadores de Confiabilidad, Mantenimiento, Utilities y Facilities
      - 'bodega': Especialistas de Bodega
      - 'gerente': Gerente de Ingeniería Sr
    """
    try:
        conn = get_ldap_connection()
        search_base = "DC=la,DC=ad,DC=goodyear,DC=com"
        
        # Filtros de búsqueda basados en los criterios solicitados y validados
        if role_name == 'planner':
            search_filter = "(&(objectCategory=person)(objectClass=user)(title=Planner)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT))"
        elif role_name == 'etl':
            search_filter = ("(&(objectCategory=person)(objectClass=user)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT)"
                             "(department=*ENGINEERING*)"
                             "(|(title=Reliability Manager)(title=Maintenance Engineer)(title=Utilities Coordinator)(title=Facilities Coordinator)))")
        elif role_name == 'bodega':
            search_filter = "(&(objectCategory=person)(objectClass=user)(title=Store Room Specialist)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT))"
        elif role_name == 'gerente':
            search_filter = "(&(objectCategory=person)(objectClass=user)(title=Engineering Manager Sr)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT))"
        else:
            return []
            
        conn.search(search_base, search_filter, search_scope=SUBTREE, attributes=['mail'])
        emails = []
        for entry in conn.entries:
            if entry.mail:
                val = entry.mail.value
                if isinstance(val, list):
                    emails.extend([v for v in val if v])
                elif val:
                    emails.append(val)
        conn.unbind()
        return sorted(list(set(emails)))
    except Exception as e:
        print(f"ERROR: No se pudo obtener correos de LDAP para el rol {role_name}: {e}")
        return []

def get_members_for_role(role_name: str) -> list:
    """
    Retorna la lista de diccionarios con {'nombre': str, 'correo': str}
    para los usuarios pertenecientes al rol consultado desde LDAP.
    """
    try:
        conn = get_ldap_connection()
        search_base = "DC=la,DC=ad,DC=goodyear,DC=com"
        
        if role_name == 'planner':
            search_filter = "(&(objectCategory=person)(objectClass=user)(title=Planner)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT))"
        elif role_name == 'etl':
            search_filter = ("(&(objectCategory=person)(objectClass=user)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT)"
                             "(department=*ENGINEERING*)"
                             "(|(title=Reliability Manager)(title=Maintenance Engineer)(title=Utilities Coordinator)(title=Facilities Coordinator)))")
        elif role_name == 'bodega':
            search_filter = "(&(objectCategory=person)(objectClass=user)(title=Store Room Specialist)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT))"
        elif role_name == 'gerente':
            search_filter = "(&(objectCategory=person)(objectClass=user)(title=Engineering Manager Sr)(physicalDeliveryOfficeName=Santiago-CL-SANTIAGO-DE-CHILE-PLT))"
        else:
            return []
            
        conn.search(search_base, search_filter, search_scope=SUBTREE, attributes=['cn', 'mail'])
        members = []
        for entry in conn.entries:
            if entry.mail and entry.mail.value:
                mail_val = entry.mail.value[0] if isinstance(entry.mail.value, list) else entry.mail.value
                cn_val = entry.cn.value if entry.cn else mail_val.split("@")[0]
                members.append({
                    "nombre": cn_val,
                    "correo": mail_val.strip()
                })
        conn.unbind()
        
        unique_members = {}
        for m in members:
            unique_members[m["correo"].lower()] = m
            
        return sorted(list(unique_members.values()), key=lambda x: x["nombre"])
    except Exception as e:
        print(f"ERROR: No se pudo obtener miembros de LDAP para el rol {role_name}: {e}")
        return []

def authenticate_user_ldap(username: str, password_user: str) -> dict:
    """
    Intenta autenticar a un usuario mediante LDAP.
    1. Se conecta con las credenciales de servicio (LDAP_USER, LDAP_PASS).
    2. Busca el DN (Distinguished Name) del usuario por sAMAccountName.
    3. Si lo encuentra, intenta hacer un nuevo bind usando ese DN y la contraseña provista.
    4. Si el bind tiene éxito, retorna los datos del usuario.
    """
    try:
        load_env()
        server_address = os.environ.get("LDAP_SERVER", "ldapsCLSLA.la.ad.goodyear.com")
        port = int(os.environ.get("LDAP_PORT", "3268"))
        service_user = os.environ.get("LDAP_USER", "la\\LDA1425")
        service_pass = os.environ.get("LDAP_PASS", "teBa9GFkCJvZrVPtHQDYLGyL")
        
        # Limpiar el nombre de usuario
        if "\\" in username:
            username = username.split("\\")[-1]
            
        # Resolver barras invertidas en el usuario de servicio
        if "\\\\" in service_user:
            service_user = service_user.replace("\\\\", "\\")
            
        # Forzar puerto seguro 3269 si el puerto es 3268 para evitar bloqueos/hangs
        if port == 3268:
            port = 3269
            
        server = Server(server_address, port=port, use_ssl=True, connect_timeout=5)
        
        # 1. BIND con usuario de servicio
        conn = Connection(server, user=service_user, password=service_pass, auto_bind=True, receive_timeout=5)
        search_base = "DC=la,DC=ad,DC=goodyear,DC=com"
        search_filter = f"(&(objectCategory=person)(objectClass=user)(sAMAccountName={username}))"
        
        conn.search(search_base, search_filter, search_scope=SUBTREE, attributes=['cn', 'mail', 'displayName', 'title', 'department'])
        
        if not conn.entries:
            conn.unbind()
            return {"success": False, "error": "Usuario no encontrado en el Directorio Activo."}
            
        entry = conn.entries[0]
        user_dn = entry.entry_dn
        
        nombre_completo = entry.displayName.value if entry.displayName else (entry.cn.value if entry.cn else username)
        correo = entry.mail.value if entry.mail else ""
        if isinstance(correo, list):
            correo = correo[0] if correo else ""
        title = entry.title.value if entry.title else ""
        department = entry.department.value if entry.department else ""
        
        conn.unbind()
        
        # 2. BIND con credenciales del propio usuario para validar contraseña
        bind_success = False
        bind_errors = []
        
        # Determinar el dominio del usuario de servicio
        domain = "la"
        if "\\" in service_user:
            domain = service_user.split("\\")[0]
            
        user_domain_format = f"{domain}\\{username}"
        
        for bind_user in [user_domain_format, user_dn]:
            try:
                user_conn = Connection(server, user=bind_user, password=password_user, auto_bind=True, receive_timeout=5)
                user_conn.unbind()
                bind_success = True
                break
            except Exception as bind_err:
                bind_errors.append(f"{bind_user}: {bind_err}")
                
        if not bind_success:
            return {"success": False, "error": f"Contraseña incorrecta o error de bind: {'; '.join(bind_errors)}"}
            
        # Inferir el rol para compatibilidad con el sistema actual
        rol = "usuario"
        title_lower = str(title).lower()
        dept_lower = str(department).lower()
        
        if "planner" in title_lower:
            rol = "planificador"
        elif "engineering" in dept_lower or "ingenieria" in dept_lower:
            if any(x in title_lower for x in ["reliability", "maintenance", "utilities", "facilities", "confiabilidad", "mantenimiento"]):
                rol = "ingeniero_confiabilidad"
            elif "manager" in title_lower or "gerente" in title_lower:
                rol = "admin"
        elif "store room" in title_lower or "bodega" in title_lower:
            rol = "bodega"
            
        return {
            "success": True,
            "usuario": username,
            "nombre": nombre_completo,
            "correo": correo,
            "rol": rol,
            "departamento": department,
            "puesto": title
        }
            
    except Exception as e:
        return {"success": False, "error": f"Error de conexión LDAP: {str(e)}"}



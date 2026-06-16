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

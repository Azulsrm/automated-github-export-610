# Librerías necesarias
import pandas as pd                                     # Manipulación de datos
import numpy as np                                      # Operaciones numéricas
import requests                                         # Llamadas HTTP
import re                                               # Expresiones regulares
from math import radians, sin, cos, sqrt, atan2         # Cálculos trigonométricos / distancia geográfica
from datetime import datetime                           # Fechas y tiempos
from io import BytesIO                                  # Manejo de datos binarios

def main():
    
    # ID del archivo de 02. Soriana Palenque  (Respuestas)
    sheet_id = "1QcNpFwsJANgme-cxlSM0TMoVHfWB1ASgkanJAFwIzJw" 

    def leer_hoja(sheet_id, nombre_hoja):
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        response = requests.get(url)
        file = BytesIO(response.content)
        df = pd.read_excel(file, sheet_name=nombre_hoja, dtype=str).replace(r'^\s*$', pd.NA, regex=True)
        return df

    df = leer_hoja(sheet_id, "Respuestas de formulario 1")
    enc_df = leer_hoja(sheet_id, "ENC")

# 🔹Limpieza inicial del dataset

#----------------------- Etapa 1. Eliminación de columnas innecesarias  -----------------------------

    ## Son 5 columnas que se utilizan unicamente cunado se siembra la tarjeta digital
    df = df.drop(columns=['¿Quisiera que habilitemos su app y su tarjeta digital para que pueda obtener todos los beneficios?',
        ' ¿La descarga de la App fue exitosa?',
        '¿Cuál es la razón por la cual no desea o no se pudo descargar la Aplicación? ',
        'En vista de que no hemos podido descargar la App ¿Le gustaría obtener la tarjeta física Soriana YA?',
        'Registro de 13 dígitos de la tarjeta digital'], errors='ignore')

#----------------------- Etapa 2. Renombrado de columnas ------------------------------------
    df = df.rename(columns={
        'Marca temporal': 'marca_temporal',
        'Dirección de correo electrónico': 'correo_encuestador',
        'Buen día ¿Ya cuenta con su tarjeta Soriana Ya?\n*Mostrar Tarjeta*': 'tarjeta_existente',
        'Dígitos del 9 al 16': 'ultimos8_tarjeta',
        'Correo electrónico:': 'correo_cliente',
        'Dominio:': 'dominio_correo',
        '¿Origen del número telefónico?': 'origen_telefono',
        'Teléfono': 'telefono',
        'Nombre': 'nombre',
        'Apellido Paterno': 'apellido_paterno',
        'Apellido Materno': 'apellido_materno',
        'Género': 'genero',
        'Día de Nacimiento': 'dia_nacimiento',
        'Mes de Nacimiento': 'mes_nacimiento',
        'Año de Nacimiento': 'anio_nacimiento',
        '¿A qué lugar prefiere acudir para realizar sus compras?': 'preferencia_compra',
        'Posición GPS': 'posicion_gps',
        'Calle': 'calle',
        'Colonia': 'colonia',
        'Código Postal': 'codigo_postal',
        'Después de todo lo que le he indicado, podría decirme ¿Ya conocía este programa de lealtad?': 'conocia_programa',
        'Código de verificación': 'codigo_verificacion',
    })

# ----------------------- Etapa 3. Creación de columnas auxiliares  ------------------------------------

    ## -------------------1. fila_forms: Número de registro en la base original
    df['fila_forms'] = df.index + 2
    df['formato'] = 'Mercado'
    df['Sucursal'] = 610
    df['Tienda'] = 'Palenque'

    ## ------------------- 2.nombre_completo: Concatenación del nombre del encuestado
    df['nombre_completo'] = (
        df[['nombre', 'apellido_paterno', 'apellido_materno']]
        .fillna('').astype(str)
        .agg(' '.join, axis=1)
        .str.strip()
    )

    ## ------------------ 3. correo_completo: Concatenación del correo del encuestado
    # --- 1. Preparar valores base ---
    df['correo_cliente'] = df['correo_cliente'].astype(str).str.strip()
    df['dominio_correo'] = df['dominio_correo'].astype(str).str.strip()
    
    # --- 2. Limpiar y crear correo_completo ---
    caracteres_prohibidos = [' ', ',', ';', '/', '\\', '%', '&']
    regex_acentos = re.compile(r'[áéíóúÁÉÍÓÚüÜñÑ]')
    reemplazos = str.maketrans('áéíóúÁÉÍÓÚüÜñÑ', 'aeiouAEIOUuunn')
    
    def limpiar_correo(correo):
        correo = str(correo).lower().strip()
        correo = correo.translate(reemplazos)
        correo = correo.replace(' ', '').replace('@@', '@')
        for c in caracteres_prohibidos:
            correo = correo.replace(c, '')
        if '@' in correo:
            usuario, dominio = correo.split('@', 1)
            if dominio.startswith("gmail"):
                usuario = usuario.replace('.', '').replace('_', '')
                correo = usuario + '@' + dominio
        return correo
    
    # Concatenar y limpiar solo si ambos campos no están vacíos
    df['correo_completo'] = df.apply(
        lambda row: limpiar_correo(row['correo_cliente'] + row['dominio_correo'])
        if row['correo_cliente'] and row['dominio_correo'] else None,
        axis=1
    )
    #-------------------- 4.Fecha_completa
    ##-------------------- Máscara para registros con día, mes y año no nulos --------------------
    mask_fecha_completa = df[['anio_nacimiento', 'mes_nacimiento', 'dia_nacimiento']].notna().all(axis=1)
    # -------------------- Crear columna fecha_completa solo donde hay datos --------------------
    df['fecha_completa'] = pd.NaT  # Inicializamos con NaT (equivalente a nulo para fechas)

    df.loc[mask_fecha_completa, 'fecha_completa'] = pd.to_datetime(
        df.loc[mask_fecha_completa, ['anio_nacimiento', 'mes_nacimiento', 'dia_nacimiento']].rename(
            columns={
                'anio_nacimiento': 'year',
                'mes_nacimiento': 'month',
                'dia_nacimiento': 'day'
            }
        ),
        errors='coerce'
    )
## ----------------- 4. telefono_validador
    ### Asegurarse de que los campos sean texto y quitar espacios
    df['telefono'] = df['telefono'].astype(str).str.strip()
    df['codigo_verificacion'] = df['codigo_verificacion'].astype(str).str.strip()
    
    ### Reemplazar valores vacíos o inválidos por NaN
    df['telefono'] = df['telefono'].replace(['', 'nan', 'None'], np.nan)
    df['codigo_verificacion'] = df['codigo_verificacion'].replace(['', 'nan', 'None'], np.nan)
    
    ### Validar que teléfono tenga exactamente 10 dígitos y que solo contenga números
    df['telefono'] = df['telefono'].where(df['telefono'].str.match(r'^\d{10}$'))
    
    ### Validar que código tenga exactamente 2 dígitos (rellenar con ceros si hace falta)
    df['codigo_verificacion'] = df['codigo_verificacion'].where(df['codigo_verificacion'].str.match(r'^\d{1,2}$')).str.zfill(2)
    
    ### Crear columna final solo si ambos datos son válidos
    mask = df['telefono'].notna() & df['codigo_verificacion'].notna()
    df['telefono_codigo'] = np.where(mask,
        df['telefono'] + df['codigo_verificacion'],
        np.nan
    )
    
    ### Validación extra: forzar que 'telefono_validador' tenga exactamente 12 dígitos
    df['telefono_codigo'] = df['telefono_codigo'].where(df['telefono_codigo'].str.match(r'^\d{12}$'))

##----------------------- Etapa 4. Conversión de tipos de datos ------------------------------------
    columnas_a_convertir = [
        'ultimos8_tarjeta',
        'telefono',
        'dia_nacimiento',
        'mes_nacimiento',
        'anio_nacimiento',
        'codigo_postal'
    ]

    df[columnas_a_convertir] = df[columnas_a_convertir].astype('Int64')  # Soporta NaN

    # ----------------------- Validación de estructura -------------------------------------
    tipos_df = pd.DataFrame({
        'N° Variable': range(1, len(df.columns) + 1),
        'Columna': df.columns,
        'Tipo de dato': [df[col].dtype for col in df.columns]
    })

    print(tipos_df.to_string(index=False))

# ▶ Módulos de validación
    
    # Regla 1: Nombre nulo
    df['nulo_nombre'] = df['nombre'].isna() | (df['nombre'].astype(str).str.strip() == '')

    # Regla 2: Apellido paterno nulo
    df['nulo_apellido_paterno'] = df['apellido_paterno'].isna() | (df['apellido_paterno'].astype(str).str.strip() == '')

    # Regla 3: Apellido materno nulo
    df['nulo_apellido_materno'] = df['apellido_materno'].isna() | (df['apellido_materno'].astype(str).str.strip() == '')

    # Regla 4: Teléfono  nulo
    df['nulo_telefono'] = df['telefono'].isna() | (df['telefono'].astype(str).str.strip() == '')

    # Regla 5: Correo cliente  nulo
    df['nulo_correo_cliente'] = df['correo_cliente'].isna() | (df['correo_cliente'].astype(str).str.strip() == '')

    # Regla 6: Número de tarjeta nulo
    df['nulo_ultimos8_tarjeta'] = df['ultimos8_tarjeta'].isna() | (df['ultimos8_tarjeta'].astype(str).str.strip() == '')

    # Regla 7: Dia de nacimiento nulo
    df['nulo_dia_nacimiento'] = df['dia_nacimiento'].isna() | (df['dia_nacimiento'].astype(str).str.strip() == '')

    # Regla 8: Mes de nacimiento nulo
    df['nulo_mes_nacimiento'] = df['mes_nacimiento'].isna() | (df['mes_nacimiento'].astype(str).str.strip() == '')

    # Regla 9: Año de nacimiento nulo
    df['nulo_anio_nacimiento'] = df['anio_nacimiento'].isna() | (df['anio_nacimiento'].astype(str).str.strip() == '')

    # Consolidado del módulo
    df['registro_nulo'] = (
        df['nulo_nombre'] |
        df['nulo_apellido_paterno'] |
        df['nulo_apellido_materno'] |
        df['nulo_telefono'] |
        df['nulo_correo_cliente'] |
        df['nulo_ultimos8_tarjeta'] |
        df['nulo_dia_nacimiento'] |
        df['nulo_mes_nacimiento'] |
        df['nulo_anio_nacimiento']
    ).astype(int)

    # ---------------------------------------------------
    # Etiqueta nulo_existe_tarjeta:
    # ---------------------------------------------------

    ## Justifica los campos vacíos cuando el encuestado (sí) cuenta con una tarjeta Soriana activa
    df['nulo_existe_tarjeta'] = (
        (df['registro_nulo'] == 1) & (df['tarjeta_existente'].astype(str).str.strip().str.lower() == 'sí')
    ).astype(int)

    # -------------------------------------- Resumen ---------------------------------
    print("Total registros con al menos un campo nulo:", df['registro_nulo'].sum())
    print("Registros nulos justificados por tarjeta existente:", df['nulo_existe_tarjeta'].sum())

# 🔹 Módulo 1: Detección de registros duplicados

    # Regla 1: Número de tarjeta duplicado (excluyendo nulos)
    df['duplicado_ultimos8_tarjeta'] = 0
    df.loc[df['ultimos8_tarjeta'].notna(), 'duplicado_ultimos8_tarjeta'] = (
        df[df['ultimos8_tarjeta'].notna()]
        .duplicated(subset='ultimos8_tarjeta', keep=False)
        .astype(int)
    )

    # Regla 2: Nombre completo (excluyendo nulos)
    df['duplicado_nombre'] = 0
    mask_nombre = df[['nombre', 'apellido_paterno', 'apellido_materno']].notna().all(axis=1)
    df.loc[mask_nombre, 'duplicado_nombre'] = (
        df[mask_nombre]
        .duplicated(subset=['nombre', 'apellido_paterno', 'apellido_materno'], keep=False)
        .astype(int)
    )

    # Regla 3: Correo del cliente duplicado (excluyendo nulos)
    df['duplicado_correo_cliente'] = 0
    df.loc[df['correo_cliente'].notna(), 'duplicado_correo_cliente'] = (
        df[df['correo_cliente'].notna()]
        .duplicated(subset='correo_cliente', keep=False)
        .astype(int)
    )

    # Regla 4: Teléfono duplicado (excluyendo nulos)
    df['duplicado_telefono'] = 0
    df.loc[df['telefono'].notna(), 'duplicado_telefono'] = (
        df[df['telefono'].notna()]
        .duplicated(subset='telefono', keep=False)
        .astype(int)
    )

    # Regla 5: Posición GPS duplicada (excluyendo nulos)
    df['duplicado_posicion_gps'] = 0
    df.loc[df['posicion_gps'].notna(), 'duplicado_posicion_gps'] = (
        df[df['posicion_gps'].notna()]
        .duplicated(subset='posicion_gps', keep=False)
        .astype(int)
    )

    # Consolidado del módulo
    df['registro_duplicado'] = (
        df['duplicado_ultimos8_tarjeta'] |
        df['duplicado_nombre'] |
        df['duplicado_correo_cliente'] |
        df['duplicado_telefono'] |
        df['duplicado_posicion_gps']
    ).astype(int)

    # ---------------------------------------------------------
    # Etiqueta tipo_duplicado: Clasifica el tipo de duplicado
    # ---------------------------------------------------------
    duplicados = [
        ('duplicado_ultimos8_tarjeta', 'Tarjeta'),
        ('duplicado_nombre', 'Nombre'),
        ('duplicado_correo_cliente', 'Correo'),
        ('duplicado_telefono', 'Teléfono'),
        ('duplicado_posicion_gps', 'Posición GPS')
    ]
    num_total_duplicados = len(duplicados)

    def obtener_tipo_duplicado(row):
        tipos = [nombre for col, nombre in duplicados if row.get(col) == 1]
        if len(tipos) == num_total_duplicados:
            return 'Todos los campos'
        return ', '.join(tipos) if tipos else None


    df['tipo_duplicado'] = df.apply(obtener_tipo_duplicado, axis=1)

    # --------------------------------------------------------------------------
    # Etiqueta fila_duplicado: Indica las filas donde está duplicado el registro
    # --------------------------------------------------------------------------

    ## Paso 1: construir todos los diccionarios de valores duplicados
    campos = {
        'Tarjeta': ('ultimos8_tarjeta', {}),
        'Correo': ('correo_cliente', {}),
        'Teléfono': ('telefono', {}),
        'Posición GPS': ('posicion_gps', {}),
        'Nombre': ('nombre_completo', {})
    }

    ## Rellenar los diccionarios con fila_forms por valor
    for etiqueta, (col, dic) in campos.items():
        for _, row in df.iterrows():
            val = row[col]
            if pd.notna(val) and val != '':
                dic.setdefault(val, []).append(row['fila_forms'])

    ## Paso 2: función que une todas las filas duplicadas según tipo_duplicado
    def obtener_fila_duplicado(row):
        if pd.isna(row['tipo_duplicado']):
            return None

        duplicados_en_filas = set()
        tipos = [tipo.strip() for tipo in row['tipo_duplicado'].split(',')]

        for tipo in tipos:
            if tipo in campos:
                col, dic = campos[tipo]
                val = row[col]
                if pd.notna(val) and val in dic and len(dic[val]) > 1:
                    duplicados_en_filas.update(dic[val])

        if duplicados_en_filas:
            return ', '.join(map(str, sorted(duplicados_en_filas)))
        return None

    ## Paso 3: aplicar la función
    df['fila_duplicado'] = df.apply(obtener_fila_duplicado, axis=1)

    # ------------------------------------------------------------------------------------
    # Etiqueta frecuencia_duplicado: Indica cuantas veces se repite el registro duplicado
    # -----------------------------------------------------------------------------------

    # Crear columna con la frecuencia del valor repetido según el tipo de duplicado
    def obtener_frecuencia_duplicado(row):
        if pd.isna(row['tipo_duplicado']):
            return None

        tipos = [tipo.strip() for tipo in row['tipo_duplicado'].split(',')]
        max_frecuencia = 1  # mínimo siempre aparece una vez

        for tipo in tipos:
            if tipo in campos:
                col, dic = campos[tipo]
                val = row[col]
                if pd.notna(val):
                    frecuencia = len(dic.get(val, []))
                    if frecuencia > max_frecuencia:
                        max_frecuencia = frecuencia
        return max_frecuencia

    # Aplicar al DataFrame
    df['frecuencia_duplicado'] = df.apply(obtener_frecuencia_duplicado, axis=1)

    # -------------------------------------- Resumen ---------------------------------
    print("Total de registros duplicados detectados:", df['registro_duplicado'].sum())

# 🔹 Módulo 2: Correos electrónicos inválidos
    #------------------------------- Máscara para valores nulos -------------------
    mask_correo = (
        df['correo_cliente'].notna() &
        df['dominio_correo'].notna() &
        df['correo_cliente'].str.strip().ne('') &
        df['dominio_correo'].str.strip().ne('')
    )

    # Inicializar todas las variables en 0
    df['correo_sin_arroba'] = 0
    df['correo_dominio_invalido'] = 0
    df['correo_formato_invalido'] = 0
    df['correo_longitud_invalida'] = 0
    df['correo_soriana'] = 0
    df['correo_numerico'] = 0

    # Regla 1: correo_sin_arroba  (excluyendo nulos)
    df.loc[mask_correo, 'correo_sin_arroba'] = (
        ~df.loc[mask_correo, 'correo_completo'].str.contains('@')
    ).astype(int)

    # Regla 2: correo_dominio_invalido  (excluyendo nulos)
    dominios_validos = [
        '@gmail.com', '@hotmail.com', '@yahoo.com', '@yahoo.com.mx',
        '@live.com', '@outlook.es', '@icloud.com', '@outlook.com', '@live.com.mx',
    ]
    df.loc[mask_correo, 'correo_dominio_invalido'] = (
        ~df.loc[mask_correo, 'dominio_correo'].isin(dominios_validos)
    ).astype(int)
    
    # Regla 3: correo_formato_invalido  (excluyendo nulos)
    def formato_invalido(correo):
        if '@' not in correo or correo.count('@') != 1:
            return 1
        parte_usuario, parte_dominio = correo.split('@', 1)
        if not parte_usuario or not parte_dominio or '.' not in parte_dominio:
            return 1
        return 0

    df.loc[mask_correo, 'correo_formato_invalido'] = df.loc[
        mask_correo, 'correo_completo'
    ].apply(formato_invalido)

    # Regla 4: correo_longitud_invalida  (excluyendo nulos)
    df.loc[mask_correo, 'correo_longitud_invalida'] = (
        df.loc[mask_correo, 'correo_completo'].str.len() < 6
    ).astype(int)

    # Regla 5: correo_soriana  (excluyendo nulos)
    df.loc[mask_correo, 'correo_soriana'] = (
        df.loc[mask_correo, 'dominio_correo'].str.lower() == '@soriana.com'
    ).astype(int)

    #Regla 6: correo_numerico
    df.loc[mask_correo, 'correo_numerico'] = df.loc[
        mask_correo, 'correo_cliente'
    ].apply(lambda x: int(str(x).isdigit()))

    # Consolidado del módulo
    df['correo_invalido'] = (
        df['correo_sin_arroba'] |
        df['correo_dominio_invalido'] |
        df['correo_formato_invalido'] |
        df['correo_longitud_invalida'] |
        df['correo_soriana'] |
        df['correo_numerico']
    ).astype(int)

    # --------------------------------------------------------------
    # Etiqueta tipo_correo: Clasifica el tipo de error en el correo
    # --------------------------------------------------------------

    errores_correo = [
        ('correo_sin_arroba', 'Sin arroba'),
        ('correo_dominio_invalido', 'Dominio inválido'),
        ('correo_formato_invalido', 'Formato inválido'),
        ('correo_longitud_invalida', 'Longitud'),
        ('correo_soriana', 'Dominio Soriana'),
        ('correo_numerico', 'Solo números')
    ]

    # Función para construir tipo_correo con todas las causas concatenadas
    def obtener_tipo_error_correo(row):
        errores = [nombre for col, nombre in errores_correo if row.get(col) == 1]
        return ', '.join(errores) if errores else None

    # Aplicar al DataFrame
    df['tipo_correo'] = df.apply(obtener_tipo_error_correo, axis=1)

    # -------------------------------------- Resumen ---------------------------------
    print("Total de registros con correo inválido (solo si hay correo real):", df['correo_invalido'].sum())

# 🔹 Módulo 3: Teléfonos inválidos

    #------------------------------- Máscara para valores nulos -------------------
    mask_telefono_valido = df['telefono'].notna()

    # Convertimos teléfono a string seguro
    df['telefono_str'] = df['telefono'].astype(str)

    # Regla 1: telefono_longitud_incorrecta  (excluyendo nulos)
    df['telefono_longitud_incorrecta'] = 0
    df.loc[mask_telefono_valido, 'telefono_longitud_incorrecta'] = (
        df.loc[mask_telefono_valido, 'telefono_str'].str.len() != 10
    ).astype(int)

    # Regla 2: telefono_caracteres_invalidos  (excluyendo nulos)
    df['telefono_caracteres_invalidos'] = 0
    df.loc[mask_telefono_valido, 'telefono_caracteres_invalidos'] = (
        df.loc[mask_telefono_valido, 'telefono_str'].str.contains(r'\D')
    ).astype(int)

    # Regla 3: telefono_fuera_rango  (excluyendo nulos)
    df['telefono_fuera_rango'] = 0
    df.loc[mask_telefono_valido, 'telefono_fuera_rango'] = (
        (df.loc[mask_telefono_valido, 'telefono'] < 1000000000) |
        (df.loc[mask_telefono_valido, 'telefono'] > 9999999999)
    ).astype(int)

    # Regla 4: telefono_lada_invalida  (excluyendo nulos)
    df['telefono_lada_invalida'] = 0
    lada_invalidas_regex = r'^(000|123)'
    df.loc[mask_telefono_valido, 'telefono_lada_invalida'] = (
        df.loc[mask_telefono_valido, 'telefono_str'].str.match(lada_invalidas_regex)
    ).astype(int)

    # Consolidado del módulo
    df['telefono_invalido'] = (
        df['telefono_longitud_incorrecta'] |
        df['telefono_caracteres_invalidos'] |
        df['telefono_fuera_rango'] |
        df['telefono_lada_invalida']
    ).astype(int)

    # --------------------------------------------------------------
    # Etiqueta tipo_telefono: Clasifica el tipo de error en el teléfono
    # --------------------------------------------------------------

    # Reglas y etiquetas
    reglas_telefono = [
        ('telefono_longitud_incorrecta', 'Longitud'),
        ('telefono_caracteres_invalidos', 'Caracteres inválidos'),
        ('telefono_fuera_rango', 'Rango atípico'),
        ('telefono_lada_invalida', 'Lada inválida')
    ]

    def obtener_tipo_telefono(row):
        errores = [nombre for col, nombre in reglas_telefono if row.get(col) == 1]
        return ', '.join(errores) if errores else None

    df['tipo_telefono'] = df.apply(obtener_tipo_telefono, axis=1)


    # -------------------------------------- Resumen ----------------------------------------------------
    print("✅ Total de registros con teléfono inválido (excluyendo nulos):", df['telefono_invalido'].sum())

# 🔹 Módulo 4: Fechas de nacimiento inválidas

    # Inicializar columnas
    df['fecha_dia_invalido'] = 0
    df['fecha_mes_invalido'] = 0
    df['fecha_anio_invalido'] = 0
    df['fecha_no_real'] = 0
    df['fecha_edad_invalida'] = 0

    # Regla 1: Día fuera de rango
    df['fecha_dia_invalido'] = (
        ~df['dia_nacimiento'].between(1, 31)
    ).fillna(False).astype(int)

    # Regla 2: Mes fuera de rango
    df['fecha_mes_invalido'] = (
        ~df['mes_nacimiento'].between(1, 12)
    ).fillna(False).astype(int)

    # Regla 3: Año fuera de rango
    df['fecha_anio_invalido'] = (
        ~df['anio_nacimiento'].between(1920, 2006)
    ).fillna(False).astype(int)

    # Regla 4: Fecha no real (si fecha_completa es NaT)
    df['fecha_no_real'] = df['fecha_completa'].isna().astype(int)

    # Regla 5: Edad fuera del rango 18-105
    from datetime import datetime

    def edad_invalida(fecha):
        if pd.isna(fecha):
            return 0  # Ya se cuenta como 'no real'
        hoy = datetime.now()
        edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
        return int(not (18 <= edad <= 105))

    df['fecha_edad_invalida'] = df['fecha_completa'].apply(edad_invalida)

    # Consolidado
    df['fecha_invalida'] = (
        df['fecha_dia_invalido'] |
        df['fecha_mes_invalido'] |
        df['fecha_anio_invalido'] |
        df['fecha_no_real'] |
        df['fecha_edad_invalida']
    ).astype(int)
    
    # --------------------------------------------------------------
    # Etiqueta tipo_fecha: Clasifica el tipo de error en la fecha
    # --------------------------------------------------------------
    def tipo_fecha(row):
        errores = []
        if row['fecha_dia_invalido']: errores.append('Día inválido')
        if row['fecha_mes_invalido']: errores.append('Mes inválido')
        if row['fecha_anio_invalido']: errores.append('Año inválido')
        if row['fecha_no_real']: errores.append('Fecha no real')
        if row['fecha_edad_invalida']: errores.append('Edad inválida')
        return ', '.join(errores) if errores else None

    df['tipo_fecha_nacimiento'] = df.apply(tipo_fecha, axis=1)

    # -------------------------------------- Resumen ----------------------------------------------------
    print("✅ Total de registros con fecha inválida:", df['fecha_invalida'].sum())

# 🔹 Módulo 5: Posición GPS inválida 
    
    # Inicializamos columnas de error
    df['gps_sin_coma'] = 0
    df['latitud_invalida'] = 0
    df['longitud_invalida'] = 0
    df['gps_formato_roto'] = 0

    # Función para validar cada posición
    def validar_gps(pos):
        if pd.isna(pos):
            return (1, 1, 1, 1)  # Todo inválido si está vacío

        pos = str(pos).strip()

        if ',' not in pos:
            return (1, 1, 1, 1)  # Sin coma, todo roto

        partes = pos.split(',')
        if len(partes) != 2:
            return (1, 1, 1, 1)  # Más de una coma o sin coordenadas claras

        lat_txt, lon_txt = partes[0].strip(), partes[1].strip()

        # Quitar letras y símbolos típicos
        lat_clean = re.sub(r'[^0-9\.\-]', '', lat_txt)
        lon_clean = re.sub(r'[^0-9\.\-]', '', lon_txt)

        # Verificar solo un punto decimal
        if lat_clean.count('.') > 1 or lon_clean.count('.') > 1:
            return (0, 1, 1, 1)
        try:
            lat = float(lat_clean)
            if not -90 <= lat <= 90:
                return (0, 1, 0, 1)
        except:
            return (0, 1, 0, 1)
        try:
            lon = float(lon_clean)
            if not -180 <= lon <= 180:
                return (0, 0, 1, 1)
        except:
            return (0, 0, 1, 1)
        # Si todo bien:
        return (0, 0, 0, 0)

    # Aplicar la función
    df[['gps_sin_coma', 'latitud_invalida', 'longitud_invalida', 'gps_formato_roto']] = df['posicion_gps'].apply(validar_gps).apply(pd.Series)

    # Columna final de validación
    df['coordenada_invalida'] = (
        df['gps_sin_coma'] |
        df['latitud_invalida'] |
        df['longitud_invalida'] |
        df['gps_formato_roto']
    ).astype(int)

    # Etiqueta del tipo de error
    def motivo_error(row):
        errores = []
        if row['gps_sin_coma']: errores.append('Sin coma')
        if row['latitud_invalida']: errores.append('Latitud inválida')
        if row['longitud_invalida']: errores.append('Longitud inválida')
        if row['gps_formato_roto']: errores.append('Formato roto')
        return ', '.join(errores) if errores else None


    df['motivo_error_coordenada'] = df.apply(motivo_error, axis=1)

    # -------------------------------------- Resumen ----------------------------------------------------
    print("✅ Total de registros con posición gps inválida:", df['coordenada_invalida'].sum())

    # Coordenada fija
    lat_fija = 27.442758
    lon_fija = -99.543487

    # Función para calcular la distancia
    def calcular_distancia(row):
        if row['coordenada_invalida'] == 1:
            return None  # Saltar si la coordenada es inválida

        try:
            # Extraer y limpiar
            lat_txt, lon_txt = row['posicion_gps'].split(',')
            lat = float(re.sub(r'[^0-9\.\-]', '', lat_txt.strip()))
            lon = float(re.sub(r'[^0-9\.\-]', '', lon_txt.strip()))

            # Conversión a radianes
            lat1 = radians(lat_fija)
            lon1 = radians(lon_fija)
            lat2 = radians(lat)
            lon2 = radians(lon)

            # Diferencias
            dlat = lat2 - lat1
            dlon = lon2 - lon1

            # Fórmula de Haversine
            a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            R = 6371000  # radio de la Tierra en metros

            return R * c
        except:
            return None

    # Aplicar al DataFrame
    df['Distancia (m)'] = df.apply(calcular_distancia, axis=1)

# ▶ Validaciones cruzadas externas

    # 1. Asegurar que los correos estén en formato string y en minúsculas (para evitar fallos por mayúsculas)
    df['correo_encuestador'] = df['correo_encuestador'].astype(str).str.strip().str.lower()
    enc_df['CORREO'] = enc_df['CORREO'].astype(str).str.strip().str.lower()

    # 2. Eliminar duplicados en enc_df por CORREO (por si hay duplicados en la base)
    enc_df = enc_df.drop_duplicates(subset='CORREO')

    # ------------------------------------------------------------------------------------
    # Etiqueta Encuestador, Coordinador y Supervisor
    # ------------------------------------------------------------------------------------

    # 3. Merge por correo_encuestador
    df = df.merge(
        enc_df[['CORREO', 'ENCUESTADOR', 'COORDINADOR', 'SUPERVISOR']].rename(columns={
            'CORREO': 'correo_encuestador',
            'ENCUESTADOR': 'Encuestador',
            'COORDINADOR': 'Coordinador',
            'SUPERVISOR': 'Supervisor'
        }),
        on='correo_encuestador',
        how='left'
    )

    # -------------------------------------- Resumen ----------------------------------------------------
    asignados = df['Encuestador'].notna().sum()
    no_asignados = df['Encuestador'].isna().sum()
    total = df.shape[0]

    print(f"✅ Cruce realizado por correo. Registros con Encuestador asignado: {asignados}")
    print(f"❌ Sin asignar: {no_asignados}")
    print(f"📊 Total de registros: {total} | Columnas: {df.shape[1]}")

# ▶ Total de registros inválidos

    df['registro_invalido'] = (
        df['registro_nulo'] |
        df['registro_duplicado'] |
        df['correo_invalido'] |
        df['telefono_invalido'] |
        df['fecha_invalida']
    ).astype(int)

    # =================================================================================
    # Etiqueta tipo_registro_invalido: Clasifica el tipo de registro inválido
    # =================================================================================

    def tipo_registro(row):
        errores = []
        if row['registro_nulo']: errores.append("Nulo")
        if row['registro_duplicado']: errores.append("Duplicado")
        if row['correo_invalido']: errores.append("Correo inválido")
        if row['telefono_invalido']: errores.append("Teléfono inválido")
        if row['fecha_invalida']: errores.append("Fecha de nacimiento inválida")
        return ', '.join(errores) if errores else None

    df['tipo_registro_invalido'] = df.apply(tipo_registro, axis=1)

    # -------------------------------------- Resumen ----------------------------------------------------
    print("✅ Total de registros inválidos globales:", df['registro_invalido'].sum())

# 🔹Resultados 
    
    # Mostrar número de filas y columnas
    print(f"📊 El DataFrame tiene {df.shape[0]} filas y {df.shape[1]} columnas.\n")

    # Mostrar listado de columnas y sus tipos
    print("📌 Columnas y tipos de dato:")
    print(df.dtypes.reset_index().rename(columns={"index": "Columna", 0: "Tipo de dato"}).to_string(index=False))

    # Ejemplo corto para no exceder el tamaño:
    df['formato'] = 'Mercado'
    df['Sucursal'] = 610
    df['Tienda'] = 'Palenque'

    output_file = "Respuestas_610.xlsx"
    df.to_excel(output_file, index=False)
    print(f"✅ Exportación lista: {output_file} ({df.shape[0]} filas)")
    
    from datetime import datetime
    print("🕒 Script ejecutado a:", datetime.utcnow().isoformat(), "UTC")

    output_file = "Respuestas_610.xlsx"
    df.to_excel(output_file, index=False)
    print(f"✅ Exportación lista: {output_file} ({df.shape[0]} filas)")

if __name__ == "__main__":
    main()

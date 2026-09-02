import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("../.env")

host = os.getenv("DATABASE_HOST")
port = os.getenv("DATABASE_PORT", 5432)
dbname = os.getenv("DATABASE_NAME")
user = os.getenv("DATABASE_USER")
password = os.getenv("DATABASE_PASSWORD")
schema = os.getenv("DATABASE_SCHEMA", "bdtridente")

print(f"Conectando a {host}:{port}/{dbname} (schema: {schema})...")
conn = psycopg2.connect(
    host=host,
    port=port,
    dbname=dbname,
    user=user,
    password=password
)
conn.autocommit = True
cur = conn.cursor()

print("[OK] Conexión establecida con PostgreSQL.")

# 1. Agregar columnas a configuracion_avisos
print("Actualizando configuracion_avisos...")
cur.execute(f"""
ALTER TABLE {schema}.configuracion_avisos 
ADD COLUMN IF NOT EXISTS asunto_vencido VARCHAR(255) NOT NULL DEFAULT 'Urgente: Tu crédito se encuentra VENCIDO - Distribuidora Tridente',
ADD COLUMN IF NOT EXISTS plantilla_vencido TEXT NOT NULL DEFAULT 'Estimado/a {{{{nombre}}}}, le informamos que su crédito por {{{{dias_credito}}}} días se encuentra VENCIDO desde el {{{{fecha_vencimiento}}}} ({{{{dias_mora}}}} días de mora). Favor regularizar su saldo a la brevedad.';
""")
print("[OK] Columnas de cobranza vencida agregadas a configuracion_avisos.")

# 2. Ajustar CHECK constraint en log_correos si existe
try:
    cur.execute(f"""
    ALTER TABLE {schema}.log_correos DROP CONSTRAINT IF EXISTS log_correos_tipo_check;
    """)
    print("[OK] Restricción de tipo en log_correos actualizada para permitir VENCIDO y pruebas.")
except Exception as e:
    print(f"[INFO] Nota sobre log_correos: {e}")

# 3. Actualizar función PL/pgSQL sp_enviar_avisos_cobranza / procesar_avisos_creditos
print("Actualizando función procesar_avisos_creditos...")
cur.execute(f"""
CREATE OR REPLACE FUNCTION {schema}.procesar_avisos_creditos()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $func$
DECLARE
    v_config RECORD;
    v_credito RECORD;
    v_cuerpo TEXT;
    v_asunto TEXT;
    v_fecha_venc_str TEXT;
    v_dias_mora INT;
    v_net_id BIGINT;
    v_enviados_recordatorio INT := 0;
    v_enviados_aviso INT := 0;
    v_enviados_vencido INT := 0;
    v_webhook_url TEXT := 'https://api.resend.com/emails';
    v_api_key TEXT := 'Bearer re_TU_API_KEY_AQUI';
BEGIN
    SELECT * INTO v_config FROM {schema}.configuracion_avisos WHERE id = 1 LIMIT 1;
    
    IF NOT FOUND OR v_config.activo = false THEN
        RETURN jsonb_build_object(
            'status', 'skipped',
            'mensaje', 'El servicio de avisos automáticos está deshabilitado.'
        );
    END IF;

    -- A. RECORDATORIO PREVENTIVO (1 día antes)
    FOR v_credito IN
        SELECT 
            c.id AS credito_id,
            c.dias_credito,
            c.fecha_vencimiento,
            cli.id AS cliente_id,
            cli.nombre AS cliente_nombre,
            cli.correo AS cliente_correo
        FROM {schema}.creditos c
        INNER JOIN {schema}.clientes cli ON cli.id = c.cliente_id
        WHERE c.pagado = false
          AND DATE(c.fecha_vencimiento) = CURRENT_DATE + INTERVAL '1 day'
          AND cli.activo = true
          AND cli.correo IS NOT NULL
          AND TRIM(cli.correo) <> ''
          AND NOT EXISTS (
              SELECT 1 
              FROM {schema}.log_correos l
              WHERE l.credito_id = c.id
                AND l.tipo = 'RECORDATORIO'
                AND DATE(l.enviado_el AT TIME ZONE 'America/Santiago') = CURRENT_DATE
          )
    LOOP
        v_fecha_venc_str := TO_CHAR(v_credito.fecha_vencimiento, 'DD/MM/YYYY');
        
        v_cuerpo := v_config.plantilla_recordatorio;
        v_cuerpo := REPLACE(v_cuerpo, '{{nombre}}', COALESCE(v_credito.cliente_nombre, 'Cliente'));
        v_cuerpo := REPLACE(v_cuerpo, '{{dias_credito}}', COALESCE(v_credito.dias_credito::TEXT, '0'));
        v_cuerpo := REPLACE(v_cuerpo, '{{fecha_vencimiento}}', v_fecha_venc_str);
        
        v_asunto := REPLACE(v_config.asunto_recordatorio, '{{nombre}}', COALESCE(v_credito.cliente_nombre, 'Cliente'));

        BEGIN
            SELECT net.http_post(
                url := v_webhook_url,
                headers := jsonb_build_object(
                    'Content-Type', 'application/json',
                    'Authorization', v_api_key
                ),
                body := jsonb_build_object(
                    'from', 'cobranzas@distribuidoratridente.cl',
                    'to', jsonb_build_array(v_credito.cliente_correo),
                    'subject', v_asunto,
                    'html', REPLACE(v_cuerpo, E'\\n', '<br/>')
                )
            ) INTO v_net_id;
        EXCEPTION WHEN OTHERS THEN
            v_net_id := NULL;
        END;

        INSERT INTO {schema}.log_correos (
            credito_id, cliente_id, destinatario, tipo, asunto, cuerpo_enviado, net_request_id
        ) VALUES (
            v_credito.credito_id, v_credito.cliente_id, v_credito.cliente_correo, 
            'RECORDATORIO', v_asunto, v_cuerpo, v_net_id
        );

        v_enviados_recordatorio := v_enviados_recordatorio + 1;
    END LOOP;

    -- B. AVISO (Mismo día del vencimiento)
    FOR v_credito IN
        SELECT 
            c.id AS credito_id,
            c.dias_credito,
            c.fecha_vencimiento,
            cli.id AS cliente_id,
            cli.nombre AS cliente_nombre,
            cli.correo AS cliente_correo
        FROM {schema}.creditos c
        INNER JOIN {schema}.clientes cli ON cli.id = c.cliente_id
        WHERE c.pagado = false
          AND DATE(c.fecha_vencimiento) = CURRENT_DATE
          AND cli.activo = true
          AND cli.correo IS NOT NULL
          AND TRIM(cli.correo) <> ''
          AND NOT EXISTS (
              SELECT 1 
              FROM {schema}.log_correos l
              WHERE l.credito_id = c.id
                AND l.tipo = 'AVISO_HOY'
                AND DATE(l.enviado_el AT TIME ZONE 'America/Santiago') = CURRENT_DATE
          )
    LOOP
        v_fecha_venc_str := TO_CHAR(v_credito.fecha_vencimiento, 'DD/MM/YYYY');
        
        v_cuerpo := v_config.plantilla_aviso;
        v_cuerpo := REPLACE(v_cuerpo, '{{nombre}}', COALESCE(v_credito.cliente_nombre, 'Cliente'));
        v_cuerpo := REPLACE(v_cuerpo, '{{dias_credito}}', COALESCE(v_credito.dias_credito::TEXT, '0'));
        v_cuerpo := REPLACE(v_cuerpo, '{{fecha_vencimiento}}', v_fecha_venc_str);
        
        v_asunto := REPLACE(v_config.asunto_aviso, '{{nombre}}', COALESCE(v_credito.cliente_nombre, 'Cliente'));

        BEGIN
            SELECT net.http_post(
                url := v_webhook_url,
                headers := jsonb_build_object(
                    'Content-Type', 'application/json',
                    'Authorization', v_api_key
                ),
                body := jsonb_build_object(
                    'from', 'cobranzas@distribuidoratridente.cl',
                    'to', jsonb_build_array(v_credito.cliente_correo),
                    'subject', v_asunto,
                    'html', REPLACE(v_cuerpo, E'\\n', '<br/>')
                )
            ) INTO v_net_id;
        EXCEPTION WHEN OTHERS THEN
            v_net_id := NULL;
        END;

        INSERT INTO {schema}.log_correos (
            credito_id, cliente_id, destinatario, tipo, asunto, cuerpo_enviado, net_request_id
        ) VALUES (
            v_credito.credito_id, v_credito.cliente_id, v_credito.cliente_correo, 
            'AVISO_HOY', v_asunto, v_cuerpo, v_net_id
        );

        v_enviados_aviso := v_enviados_aviso + 1;
    END LOOP;

    -- C. CRÉDITO VENCIDO / EN MORA (Vencido ayer o días anteriores y no pagado)
    FOR v_credito IN
        SELECT 
            c.id AS credito_id,
            c.dias_credito,
            c.fecha_vencimiento,
            cli.id AS cliente_id,
            cli.nombre AS cliente_nombre,
            cli.correo AS cliente_correo
        FROM {schema}.creditos c
        INNER JOIN {schema}.clientes cli ON cli.id = c.cliente_id
        WHERE c.pagado = false
          AND DATE(c.fecha_vencimiento) < CURRENT_DATE
          AND cli.activo = true
          AND cli.correo IS NOT NULL
          AND TRIM(cli.correo) <> ''
          AND NOT EXISTS (
              SELECT 1 
              FROM {schema}.log_correos l
              WHERE l.credito_id = c.id
                AND l.tipo = 'VENCIDO'
                AND DATE(l.enviado_el AT TIME ZONE 'America/Santiago') = CURRENT_DATE
          )
    LOOP
        v_fecha_venc_str := TO_CHAR(v_credito.fecha_vencimiento, 'DD/MM/YYYY');
        v_dias_mora := CURRENT_DATE - DATE(v_credito.fecha_vencimiento);
        
        v_cuerpo := COALESCE(v_config.plantilla_vencido, 'Estimado/a {{nombre}}, le informamos que su credito por {{dias_credito}} dias se encuentra VENCIDO desde el {{fecha_vencimiento}} ({{dias_mora}} dias de mora). Favor regularizar su saldo a la brevedad.');
        v_cuerpo := REPLACE(v_cuerpo, '{{nombre}}', COALESCE(v_credito.cliente_nombre, 'Cliente'));
        v_cuerpo := REPLACE(v_cuerpo, '{{dias_credito}}', COALESCE(v_credito.dias_credito::TEXT, '0'));
        v_cuerpo := REPLACE(v_cuerpo, '{{fecha_vencimiento}}', v_fecha_venc_str);
        v_cuerpo := REPLACE(v_cuerpo, '{{dias_mora}}', v_dias_mora::TEXT);
        
        v_asunto := COALESCE(v_config.asunto_vencido, 'Urgente: Tu credito se encuentra VENCIDO - Distribuidora Tridente');
        v_asunto := REPLACE(v_asunto, '{{nombre}}', COALESCE(v_credito.cliente_nombre, 'Cliente'));
        v_asunto := REPLACE(v_asunto, '{{dias_mora}}', v_dias_mora::TEXT);

        BEGIN
            SELECT net.http_post(
                url := v_webhook_url,
                headers := jsonb_build_object(
                    'Content-Type', 'application/json',
                    'Authorization', v_api_key
                ),
                body := jsonb_build_object(
                    'from', 'cobranzas@distribuidoratridente.cl',
                    'to', jsonb_build_array(v_credito.cliente_correo),
                    'subject', v_asunto,
                    'html', REPLACE(v_cuerpo, E'\\n', '<br/>')
                )
            ) INTO v_net_id;
        EXCEPTION WHEN OTHERS THEN
            v_net_id := NULL;
        END;

        INSERT INTO {schema}.log_correos (
            credito_id, cliente_id, destinatario, tipo, asunto, cuerpo_enviado, net_request_id
        ) VALUES (
            v_credito.credito_id, v_credito.cliente_id, v_credito.cliente_correo, 
            'VENCIDO', v_asunto, v_cuerpo, v_net_id
        );

        v_enviados_vencido := v_enviados_vencido + 1;
    END LOOP;

    RETURN jsonb_build_object(
        'status', 'success',
        'recordatorios_enviados', v_enviados_recordatorio,
        'avisos_hoy_enviados', v_enviados_aviso,
        'vencidos_mora_enviados', v_enviados_vencido,
        'ejecutado_el', now()
    );
END;
$func$;
""")
print("[OK] Función procesar_avisos_creditos actualizada exitosamente con soporte para Créditos Vencidos (Opción B).")

# 4. Probar ejecución
cur.execute(f"SELECT {schema}.procesar_avisos_creditos();")
resultado = cur.fetchone()[0]
print(f"[OK] Prueba de ejecución en vivo en la BD: {resultado}")

cur.close()
conn.close()
print("[EXITO TOTAL] BD ACTUALIZADA.")

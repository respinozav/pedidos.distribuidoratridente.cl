"""Crea tablas configuracion_avisos, log_correos, funcion procesar_avisos_creditos y cron job.

Revision ID: 20260902_0025
Revises: 20260902_0024
Create Date: 2026-09-02
"""

from alembic import op
from app.core.config import get_settings

revision = "20260902_0025"
down_revision = "20260902_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schema = get_settings().database_schema
    
    op.execute(
        f"""
        CREATE EXTENSION IF NOT EXISTS "pg_net";
        CREATE EXTENSION IF NOT EXISTS "pg_cron";
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";

        -- 1. Tabla de Configuración de Avisos
        CREATE TABLE IF NOT EXISTS {schema}.configuracion_avisos (
            id SERIAL PRIMARY KEY,
            hora_envio TIME NOT NULL DEFAULT '09:00:00',
            asunto_recordatorio VARCHAR(255) NOT NULL DEFAULT 'Recordatorio: Tu crédito vencerá mañana - Distribuidora Tridente',
            plantilla_recordatorio TEXT NOT NULL DEFAULT 'Hola {{nombre}}, le recordamos que su crédito por {{dias_credito}} días vencerá el {{fecha_vencimiento}}. Favor coordinar el pago.',
            asunto_aviso VARCHAR(255) NOT NULL DEFAULT 'Aviso: Tu crédito vence hoy - Distribuidora Tridente',
            plantilla_aviso TEXT NOT NULL DEFAULT 'Estimado/a {{nombre}}, le informamos que su crédito vence hoy {{fecha_vencimiento}}. Favor regularizar a la brevedad.',
            activo BOOLEAN NOT NULL DEFAULT true,
            actualizado_el TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        INSERT INTO {schema}.configuracion_avisos (id, hora_envio, activo)
        VALUES (1, '09:00:00', true)
        ON CONFLICT (id) DO NOTHING;

        -- 2. Tabla de Log de Correos de Cobranza
        CREATE TABLE IF NOT EXISTS {schema}.log_correos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            credito_id UUID NOT NULL,
            cliente_id UUID,
            destinatario VARCHAR(255) NOT NULL,
            tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('RECORDATORIO', 'AVISO_HOY')),
            asunto VARCHAR(255),
            cuerpo_enviado TEXT NOT NULL,
            estado VARCHAR(50) NOT NULL DEFAULT 'ENVIADO',
            net_request_id BIGINT,
            enviado_el TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_log_correos_credito_tipo_fecha 
        ON {schema}.log_correos (credito_id, tipo, CAST(enviado_el AT TIME ZONE 'America/Santiago' AS DATE));

        CREATE INDEX IF NOT EXISTS idx_log_correos_enviado_el 
        ON {schema}.log_correos (enviado_el DESC);

        -- 3. Función PL/pgSQL para procesar y despachar avisos
        CREATE OR REPLACE FUNCTION {schema}.procesar_avisos_creditos()
        RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            v_config RECORD;
            v_credito RECORD;
            v_cuerpo TEXT;
            v_asunto TEXT;
            v_fecha_venc_str TEXT;
            v_net_id BIGINT;
            v_enviados_recordatorio INT := 0;
            v_enviados_aviso INT := 0;
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

            -- A. RECORDATORIO (1 día antes)
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

                INSERT INTO {schema}.log_correos (
                    credito_id, cliente_id, destinatario, tipo, asunto, cuerpo_enviado, net_request_id
                ) VALUES (
                    v_credito.credito_id, v_credito.cliente_id, v_credito.cliente_correo, 
                    'RECORDATORIO', v_asunto, v_cuerpo, v_net_id
                );

                v_enviados_recordatorio := v_enviados_recordatorio + 1;
            END LOOP;

            -- B. AVISO (Mismo día)
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

                INSERT INTO {schema}.log_correos (
                    credito_id, cliente_id, destinatario, tipo, asunto, cuerpo_enviado, net_request_id
                ) VALUES (
                    v_credito.credito_id, v_credito.cliente_id, v_credito.cliente_correo, 
                    'AVISO_HOY', v_asunto, v_cuerpo, v_net_id
                );

                v_enviados_aviso := v_enviados_aviso + 1;
            END LOOP;

            RETURN jsonb_build_object(
                'status', 'success',
                'recordatorios_enviados', v_enviados_recordatorio,
                'avisos_hoy_enviados', v_enviados_aviso,
                'ejecutado_el', now()
            );
        END;
        $$;

        -- 4. Programar cron job diario si pg_cron está activo
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                PERFORM cron.unschedule('job-procesar-avisos-creditos');
                PERFORM cron.schedule(
                    'job-procesar-avisos-creditos',
                    '0 9 * * *',
                    'SELECT {schema}.procesar_avisos_creditos();'
                );
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- Ignorar si pg_cron no permite scheduling en el contexto actual
            NULL;
        END $$;
        """
    )


def downgrade() -> None:
    schema = get_settings().database_schema
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                PERFORM cron.unschedule('job-procesar-avisos-creditos');
            END IF;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;

        DROP FUNCTION IF EXISTS {schema}.procesar_avisos_creditos();
        DROP TABLE IF EXISTS {schema}.log_correos;
        DROP TABLE IF EXISTS {schema}.configuracion_avisos;
        """
    )

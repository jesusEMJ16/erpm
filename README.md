# BLACKERP (Base Limpia)

Proyecto nuevo en Python + PyQt5, creado desde cero para conservar el lenguaje visual de BLACKDB sin arrastrar logica de negocio.

## Objetivo de esta primera etapa

- Mantener diseno, colores, UI, comportamiento de ventanas y tablas.
- Separar la base visual en componentes reutilizables.
- Trabajar inicialmente con datos mock para empezar a implementar modulos reales despues.

## Estructura

- app/core: tema global, tokens y utilidades de ventana.
- app/ui/widgets: componentes visuales reutilizables.
- app/ui/pages: paginas base (dashboard, inventory, settings).
- app/ui: ventanas principales (login y shell).
- app/services: datos mock y servicios de arranque.

## Ejecutar

1. Crear/activar entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Lanzar la app:

```bash
python run_app.py
```

## Configuracion SQL Server

La conexion esta centralizada en `db/connection_manager.py`. El ERP mantiene compatibilidad con `.env`, pero Settings puede guardar una configuracion local en `tmp/database_settings.json`.

Prioridad de configuracion:

1. Defaults seguros del proyecto.
2. Variables de `.env`.
3. `tmp/database_settings.json` guardado desde Settings.

Ejemplo versionable: `config/database.example.json`.

Al iniciar, `run_app.py` ejecuta `initialize_database()`. El inicializador verifica tablas por `INFORMATION_SCHEMA.TABLES` y solo ejecuta los scripts faltantes en `db/schema`, respetando el orden de llaves foraneas.

## Siguientes pasos sugeridos

- Conectar `app/services` a una capa de repositorios real.
- Reemplazar datos mock de Inventory por una fuente persistente.
- Agregar pruebas de widgets y smoke tests de navegacion.

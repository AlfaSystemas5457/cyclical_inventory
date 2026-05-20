{
    "name": "Inventario Cíclico",
    "version": "1.0",
    "description": """
        Gestión de inventarios cíclicos programados.
        - Configuración de frecuencia y cantidad de productos por ciclo
        - Selección ordenada o aleatoria de productos
        - Asignación de productos por usuario o compartida
        - Seguimiento de productos ya inventariados
        - Opción de repetir productos en ciclos futuros
    """,
    "summary": "Inventario cíclico automatizado",
    "author": "DGV",
    "license": "LGPL-3",
    "category": "Inventory",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/cron_data.xml",
        "views/cyclical_inventory_views.xml",
        "views/cyclical_inventory_line_views.xml",
        "views/res_config_settings_views.xml",
        "views/stock_quant_views.xml",
        "views/menu_views.xml",
    ],
    "auto_install": False,
    "application": False,
}

# Inventario Cíclico

Módulo para Odoo 19.0 que gestiona inventarios cíclicos programados. Selecciona automáticamente productos para contar según una frecuencia configurable y asigna los conteos a los usuarios.

## Funcionalidades

- **Configuración en Ajustes de Inventario**: activar/desactivar, frecuencia (días), cantidad de productos por ciclo, método de conteo (ordenado/aleatorio), distribución (por usuario/compartido), usuarios asignados y responsable de inventario.
- **Ciclos**: se generan automáticamente mediante un cron diario o manualmente desde el formulario.
- **Líneas de producto**: cada ciclo contiene las líneas con los productos a inventariar, usuario asignado, cantidad teórica, cantidad contada y estado.
- **Conteo**: cada línea puede contarse abriendo el Physical Inventory de Odoo, marcarse manualmente como contada, o sincronizarse con los quants.
- **Discrepancias**: al marcar un producto como contado, si la cantidad difiere de la teórica, se crea una actividad tipo "To-Do" asignada al responsable de inventario.
- **Read-only**: los ciclos solo son editables en estado "Borrador". Una vez generadas las líneas, pasan a "En Progreso" y solo la cantidad contada es modificable.

## Flujo de uso

1. **Configurar**: Ajustes → Inventario → "Inventario Cíclico". Activar, definir frecuencia, cantidad de productos, método, distribución y usuarios.
2. **Generar ciclo**: Automático (cron diario) o manual (crear ciclo → "Generar Líneas"). El sistema selecciona productos con stock > 0 en ubicaciones internas.
3. **Contar**: Los usuarios cuentan los productos asignados. Pueden hacerlo mediante "Contar" (abre Physical Inventory), "Marcar Contado" manual, o editando la cantidad directamente en la lista.
4. **Revisar discrepancias**: Si la cantidad contada no coincide con la teórica, se crea una actividad para el responsable.
5. **Finalizar**: "Finalizar Ciclo" cierra el ciclo y registra la fecha de fin.

## Datos técnicos

### Modelos

| Modelo | Descripción |
|--------|-------------|
| `cyclical.inventory.cycle` | Ciclo de inventario con frecuencia, método, distribución y líneas |
| `cyclical.inventory.line` | Línea individual con producto, usuario, estado y cantidades |

### Dependencias

- `stock`
- `mail`

### Grupos de seguridad

- `stock.group_stock_manager`: acceso completo a ciclos y líneas
- `stock.group_stock_user`: acceso de lectura a ciclos, lectura/escritura a líneas

### Cron

- `ir_cron_generate_cyclical_cycles`: ejecución diaria, genera ciclos automáticamente según la configuración. Desactivado por defecto.

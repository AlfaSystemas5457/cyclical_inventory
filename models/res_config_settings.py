# -*- coding: utf-8 -*-

from odoo import api, fields, models
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cyclical_inventory_enabled = fields.Boolean(
        string="Inventario Cíclico",
        config_parameter="cyclical_inventory.cyclical_inventory_enabled",
        help="Activa la generación automática de ciclos de inventario cíclico.",
    )

    cyclical_inventory_frequency = fields.Integer(
        string="Frecuencia (días)",
        default=7,
        config_parameter="cyclical_inventory.cyclical_inventory_frequency",
        help="Cada cuántos días se genera un nuevo ciclo.",
    )

    cyclical_inventory_count = fields.Integer(
        string="Productos por Ciclo",
        default=20,
        config_parameter="cyclical_inventory.cyclical_inventory_count",
        help="Cantidad de productos a incluir en cada ciclo.",
    )

    cyclical_inventory_method = fields.Selection(
        [
            ("ordered", "Ordenado"),
            ("random", "Aleatorio"),
        ],
        string="Método de Conteo",
        default="ordered",
        config_parameter="cyclical_inventory.cyclical_inventory_method",
    )

    cyclical_inventory_distribution = fields.Selection(
        [
            ("per_user", "Por Usuario"),
            ("shared", "Compartido"),
        ],
        string="Distribución",
        default="shared",
        config_parameter="cyclical_inventory.cyclical_inventory_distribution",
        help="Por Usuario: cada usuario recibe N productos distintos. "
        "Compartido: todos los usuarios inventarian los mismos N productos.",
    )

    cyclical_inventory_responsible_id = fields.Many2one(
        "res.users",
        string="Responsable de Inventario",
        config_parameter="cyclical_inventory.cyclical_inventory_responsible_id",
        help="Usuario que recibirá notificaciones de actividades cuando haya discrepancias en los conteos.",
    )

    cyclical_inventory_user_ids = fields.Many2many(
        "res.users",
        string="Usuarios Asignados",
        help="Usuarios que pueden realizar los conteos.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()

        ICP = self.env["ir.config_parameter"].sudo()

        user_ids = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_user_ids", default="[]"
        )

        user_ids = literal_eval(user_ids)

        res.update(cyclical_inventory_user_ids=[(6, 0, user_ids)])

        return res

    def set_values(self):
        super().set_values()

        ICP = self.env["ir.config_parameter"].sudo()

        ICP.set_param(
            "cyclical_inventory.cyclical_inventory_user_ids",
            self.cyclical_inventory_user_ids.ids,
        )

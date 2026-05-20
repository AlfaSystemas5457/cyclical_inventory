# -*- coding: utf-8 -*-
from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    cyclical_inventory_line_id = fields.Many2one(
        "cyclical.inventory.line",
        string="Línea de Inventario Cíclico",
        compute="_compute_cyclical_inventory_line",
    )

    def _compute_cyclical_inventory_line(self):
        for r in self:
            line = self.env["cyclical.inventory.line"].search(
                [
                    ("product_id", "=", r.product_id.id),
                    ("state", "=", "pending"),
                    ("cycle_id.state", "in", ["draft", "in_progress"]),
                ],
                limit=1,
            )
            r.cyclical_inventory_line_id = line

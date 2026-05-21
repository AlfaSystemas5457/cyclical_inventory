from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    cyclical_counted = fields.Boolean(string="Contado en ciclo actual", default=False)

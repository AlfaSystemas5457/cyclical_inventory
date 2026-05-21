# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from ast import literal_eval
import random


class CyclicalInventoryCycle(models.Model):
    _name = "cyclical.inventory.cycle"
    _description = "Ciclo de Inventario Cíclico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc"

    name = fields.Char(
        string="Nombre", required=True, default=lambda self: _("Borrador")
    )
    date_from = fields.Date(
        string="Fecha Inicio", required=True, default=fields.Date.today
    )
    date_to = fields.Date(string="Fecha Fin")
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("in_progress", "En Progreso"),
            ("done", "Finalizado"),
        ],
        string="Estado",
        default="draft",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company
    )

    frequency = fields.Integer(string="Frecuencia", default=7)
    frequency_type = fields.Selection(
        [
            ("days", "Días"),
            ("weeks", "Semanas"),
            ("months", "Meses"),
            ("years", "Años"),
        ],
        string="Tipo de Frecuencia",
        default="days",
    )
    number_of_products = fields.Integer(string="Cantidad de Productos", default=20)
    counting_method = fields.Selection(
        [
            ("ordered", "Ordenado"),
            ("random", "Aleatorio"),
        ],
        string="Método de Conteo",
        default="ordered",
        required=True,
    )
    distribution = fields.Selection(
        [
            ("per_user", "Por Usuario"),
            ("shared", "Compartido"),
        ],
        string="Distribución",
        default="shared",
        required=True,
    )
    category_ids = fields.Many2many("product.category", string="Categorías")
    user_ids = fields.Many2many("res.users", string="Usuarios Asignados")
    line_ids = fields.One2many(
        "cyclical.inventory.line", "cycle_id", string="Productos a Inventariar"
    )

    product_count = fields.Integer(string="Total Productos", compute="_compute_counts")
    counted_count = fields.Integer(string="Contados", compute="_compute_counts")
    progress = fields.Float(
        string="Progreso", compute="_compute_counts", aggregator="avg"
    )

    @api.depends("line_ids", "line_ids.state")
    def _compute_counts(self):
        for r in self:
            lines = r.line_ids
            r.product_count = len(lines)
            r.counted_count = len(lines.filtered(lambda l: l.state == "counted"))
            r.progress = (
                (r.counted_count / r.product_count * 100) if r.product_count else 0
            )

    def action_generate_lines(self):
        self.ensure_one()
        if self.line_ids:
            raise ValidationError(
                _("Ya hay líneas generadas. Elimínelas primero si desea regenerar.")
            )

        domain = [
            ("location_id.usage", "=", "internal"),
            ("quantity", ">", 0),
        ]
        if self.category_ids:
            cat_ids = set()
            for cat in self.category_ids:
                cat_ids.update(
                    self.env["product.category"]
                    .search(
                        [
                            ("id", "child_of", cat.id),
                        ]
                    )
                    .ids
                )
            domain.append(("product_id.categ_id", "in", list(cat_ids)))

        quants = self.env["stock.quant"].search(domain)
        products = quants.mapped("product_id")
        product_ids = set(products.ids)
        products = self.env["product.product"].browse(product_ids)

        if not products:
            raise ValidationError(
                _("No hay productos disponibles para generar el ciclo.")
            )

        uncounted = products.filtered(lambda p: not p.cyclical_counted)

        if not uncounted:
            products.sudo().write({"cyclical_counted": False})
            uncounted = products

        pool = uncounted

        if self.counting_method == "random":
            selected = list(pool)
            random.shuffle(selected)
            selected = selected[: self.number_of_products]
        else:
            selected = pool.sorted(key=lambda p: p.display_name)[
                : self.number_of_products
            ]

        vals_list = []
        if self.distribution == "per_user":
            for user in self.user_ids:
                for product in selected:
                    vals_list.append(
                        {
                            "cycle_id": self.id,
                            "product_id": product.id,
                            "user_id": user.id,
                        }
                    )
        else:
            for product in selected:
                vals_list.append(
                    {
                        "cycle_id": self.id,
                        "product_id": product.id,
                    }
                )

        if vals_list:
            self.env["cyclical.inventory.line"].create(vals_list)

        self.state = "in_progress"

    def action_update_counted_status(self):
        for line in self.line_ids.filtered(lambda l: l.state == "pending"):
            line._update_counted_status()

    def action_done(self):
        self.write({"state": "done", "date_to": fields.Date.today()})

    def action_reset(self):
        self.write({"state": "draft"})

    def action_clear_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.state = "draft"

    def cron_generate_cycles(self):
        ICP = self.env["ir.config_parameter"].sudo()

        enabled = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_enabled",
            default="False",
        )
        if enabled != "True":
            return

        frequency = int(
            ICP.get_param(
                "cyclical_inventory.cyclical_inventory_frequency",
                default=7,
            )
        )
        frequency_type = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_frequency_type",
            default="days",
        )
        number_of_products = int(
            ICP.get_param(
                "cyclical_inventory.cyclical_inventory_count",
                default=20,
            )
        )
        counting_method = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_method",
            default="ordered",
        )
        distribution = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_distribution",
            default="shared",
        )
        user_ids = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_user_ids",
            default="[]",
        )

        by_category = ICP.get_param(
            "cyclical_inventory.cyclical_inventory_by_category",
            default="False",
        )
        user_ids = literal_eval(user_ids)
        last_cycle = self.search([], order="date_from desc", limit=1)
        today = fields.Date.today()

        if last_cycle:
            delta = relativedelta(**{frequency_type: frequency})
            next_date = last_cycle.date_from + delta

            if today < next_date:
                return

        cycle = self.create(
            {
                "name": _(f"Inventario Cíclico {today.strftime('%d/%m/%Y')}"),
                "date_from": today,
                "frequency": frequency,
                "frequency_type": frequency_type,
                "number_of_products": number_of_products,
                "counting_method": counting_method,
                "distribution": distribution,
                "user_ids": [(6, 0, user_ids)],
            }
        )

        if by_category != "True":
            cycle.action_generate_lines()

        if cycle.user_ids:
            for user in cycle.user_ids:
                cycle.activity_schedule(
                    activity_type_id=self.env.ref("mail.mail_activity_data_todo").id,
                    summary=_("Nuevo ciclo de inventario: %s", cycle.name),
                    note=_(
                        "Se ha generado un nuevo ciclo de inventario.\n"
                        "Productos a contar: %(products)s\n"
                        "Fecha: %(date)s\n"
                        "Método: %(method)s\n"
                        "Distribución: %(dist)s",
                        products=cycle.number_of_products,
                        date=cycle.date_from,
                        method=dict(cycle._fields['counting_method'].selection).get(cycle.counting_method),
                        dist=dict(cycle._fields['distribution'].selection).get(cycle.distribution),
                    ),
                    user_id=user.id,
                )


class CyclicalInventoryLine(models.Model):
    _name = "cyclical.inventory.line"
    _description = "Línea de Inventario Cíclico"
    _order = "cycle_id desc, id"

    cycle_id = fields.Many2one(
        "cyclical.inventory.cycle", string="Ciclo", required=True, ondelete="cascade"
    )
    product_id = fields.Many2one("product.product", string="Producto", required=True)
    user_id = fields.Many2one("res.users", string="Usuario Asignado")
    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("counted", "Contado"),
        ],
        string="Estado",
        default="pending",
        required=True,
    )
    counted_date = fields.Datetime(string="Fecha de Conteo")
    counted_by = fields.Many2one("res.users", string="Contado Por")
    inventory_quantity = fields.Float(string="Cantidad Contada")
    theoretical_quantity = fields.Float(
        string="Cantidad Teórica", compute="_compute_theoretical_quantity", store=True
    )

    @api.depends("product_id")
    def _compute_theoretical_quantity(self):
        for r in self:
            if r.product_id:
                quant = self.env["stock.quant"].search(
                    [
                        ("product_id", "=", r.product_id.id),
                        ("location_id.usage", "=", "internal"),
                    ],
                    limit=1,
                )
                r.theoretical_quantity = quant.quantity if quant else 0.0
            else:
                r.theoretical_quantity = 0.0

    def action_count(self):
        self.ensure_one()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id.usage", "=", "internal"),
            ],
            limit=1,
        )
        if not quant:
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.quant",
                "view_mode": "list",
                "context": {
                    "search_default_product_id": self.product_id.id,
                    "inventory_mode": True,
                },
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.quant",
            "view_mode": "form",
            "res_id": quant.id,
            "context": {"inventory_mode": True},
        }

    def _update_counted_status(self):
        self.ensure_one()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id.usage", "=", "internal"),
                ("inventory_quantity_set", "=", True),
            ],
            limit=1,
        )
        if quant:
            self.write(
                {
                    "state": "counted",
                    "counted_date": quant.inventory_date or fields.Datetime.now(),
                    "counted_by": (
                        quant.user_id.id if quant.user_id else self.env.user.id
                    ),
                    "inventory_quantity": quant.inventory_quantity,
                }
            )
            self.product_id.sudo().cyclical_counted = True
            if abs(self.inventory_quantity - self.theoretical_quantity) > 0.001:
                self._create_discrepancy_activity()

    def action_mark_counted(self):
        self.ensure_one()
        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("location_id.usage", "=", "internal"),
                ("inventory_quantity_set", "=", True),
            ],
            limit=1,
        )
        vals = {
            "state": "counted",
            "counted_date": fields.Datetime.now(),
            "counted_by": self.env.user.id,
        }
        if quant and not self.inventory_quantity:
            vals["inventory_quantity"] = quant.inventory_quantity
        self.write(vals)
        self.product_id.sudo().cyclical_counted = True
        if abs(self.inventory_quantity - self.theoretical_quantity) > 0.001:
            self._create_discrepancy_activity()

    def _create_discrepancy_activity(self):
        ICP = self.env["ir.config_parameter"].sudo()
        responsible_id = int(
            ICP.get_param(
                "cyclical_inventory.cyclical_inventory_responsible_id",
                default="0",
            )
        )
        if not responsible_id:
            return

        activity_type = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        if not activity_type:
            return

        existing = self.env["mail.activity"].search_count(
            [
                ("res_model", "=", "cyclical.inventory.cycle"),
                ("res_id", "=", self.cycle_id.id),
                ("user_id", "=", responsible_id),
                ("activity_type_id", "=", activity_type.id),
                ("summary", "ilike", self.product_id.display_name),
            ]
        )
        if existing:
            return

        body = _(
            "Discrepancia en %(product)s:\n"
            "- Cantidad teórica: %(theoretical)s\n"
            "- Cantidad contada: %(counted)s\n"
            "- Diferencia: %(diff)s",
            product=self.product_id.display_name,
            theoretical=self.theoretical_quantity,
            counted=self.inventory_quantity,
            diff=self.inventory_quantity - self.theoretical_quantity,
        )

        self.cycle_id.activity_schedule(
            activity_type_id=activity_type.id,
            summary=_(
                "Discrepancia en %s — teórico: %s, contado: %s",
                self.product_id.display_name,
                self.theoretical_quantity,
                self.inventory_quantity,
            ),
            note=body,
            user_id=responsible_id,
        )

    def action_mark_pending(self):
        self.ensure_one()
        self.product_id.sudo().cyclical_counted = False
        self.write(
            {
                "state": "pending",
                "counted_date": False,
                "counted_by": False,
                "inventory_quantity": 0.0,
            }
        )

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import datetime

class LoanInstallment(models.Model):
    _name = 'loan.installment'
    _description = "Loan Installment"

    name = fields.Char(string="Name",readonly="True",compute="_compute_name")
    installment_number = fields.Integer(string="Installment Number")
    date_from = fields.Date(string="Date From")
    date_to  = fields.Date(string="Date To")
    opening_balance_amount = fields.Float(string="Beginning Balance",digits=(16, 2))
    ending_balance_amount = fields.Float(string="Ending Balance",digits=(16, 2))
    principal_amount = fields.Float(string="Principal Amount",digits=(16, 2))
    interest_amount = fields.Float(string="Interest Amount",digits=(32, 2))
    emi_installment = fields.Float(string="EMI(Installment)",digits=(32, 2))
    state = fields.Selection([('unpaid','Unpaid'),('approve','Approved'),('paid','Paid')],default='unpaid',string="State")
    partner_id  = fields.Many2one('res.partner',string="Partner",required=True)
    loan_id = fields.Many2one('loan.request',string="Loan")
    loan_type_id = fields.Many2one('loan.type',string="Loan Type")
    currency_id = fields.Many2one('res.currency',string="Currency")
    interest_acouunting_id = fields.Many2one('account.move',string="Interest Accounting Entry",readonly=True)
    accounting_entry_id = fields.Many2one('account.move',string="Accounting Entry",readonly=True)
    pay_from_payroll = fields.Boolean(string="Payroll")
    installment_booked = fields.Boolean(string="Payroll")
    loan_partner_type = fields.Selection([('customer','Customer'),('vendor','Supplier')],string="Loan Partner Type")

    @api.depends('installment_number','loan_id')
    def _compute_name(self):
        for line in self :
            if line.loan_id and line.installment_number :
                line.name = line.loan_id.name + '/' + str(line.installment_number)
        return

    def approve_payment(self):
        self.write({'state':'approve'})

    def reset_draft(self):
        self.write({'state':'unpaid'})

    def book_interest(self):
        account_move = self.env['account.move']
        name_of = self.partner_id.name
        debit_line = [0,0,{'account_id' : self.loan_id.partner_account_id.id,
                            'partner_id' : self.loan_id.user_id.partner_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : self.interest_amount,
                            'credit' : 0.0
                            }]

        credit_line = [0,0,{'account_id' : self.loan_id.partner_account_id.id,
                            'partner_id' : self.loan_id.user_id.partner_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : 0.0,
                            'credit' : self.interest_amount
                            }]

        move_line = [debit_line,credit_line]

        jounral = account_move.create({'date': fields.datetime.now(),
                    'journal_id' :self.loan_id.interest_journal_id.id,
                    'ref' : str(self.installment_number) ,
                    'line_ids' : move_line})

        jounral.action_post()
        self.write({'interest_acouunting_id' :jounral.id })
        self.installment_booked = True
        return

    def action_payment(self):
        account_move = self.env['account.move']
        name_of = self.partner_id.name
        debit_line = [0,0,{'account_id' : self.loan_id.disburse_journal_id.default_account_id.id,
                            'partner_id' : self.loan_id.user_id.partner_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : self.emi_installment,
                            'credit' : 0.0
                            }]

        credit_line = [0,0,{'account_id' : self.loan_id.partner_account_id.id,
                            'partner_id' : self.loan_id.user_id.partner_id.id,
                            'name' : 'Loan Of ' + name_of,
                            'debit' : 0.0,
                            'credit' : self.emi_installment
                            }]

        move_line = [debit_line,credit_line]
        jounral = account_move.create({'date': fields.datetime.now(),
                    'journal_id' :self.loan_id.disburse_journal_id.id,
                    'ref' : str(self.installment_number) ,
                    'line_ids' : move_line})

        jounral.action_post()
        self.write({'accounting_entry_id' :jounral.id,'state':'paid' })

        return


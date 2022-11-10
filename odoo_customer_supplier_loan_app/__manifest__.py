# -*- coding: utf-8 -*-
{
    'name': 'Loan Management for Customer and Supplier',
    "author": "Edge Technologies",
    'version': '14.0.1.0',
    'summary': 'Customer Loan Management Supplier Loan Management Partner Loan Installments Vender Loan Management Vendor Credit Loan Interest for Loan Installment Customer Loan Portal Loan Processing Fee Approve Loan Request Customer Disburse Loan EMI for Customer EMI',
    'description': """
        customer loan management supplier loan management partner loan management for customer and supplier loan management for supplier and customer
        Customer and Supplier Loan Management manages following things. Apply Loans as Loan Requests and send Loan Requests to Approve
        Loan Installments calculates based on the configuration. Loan Accounting with journal entries and journal item.
        Option to Loans to Disburse after the approval based Loan Proof manged different Loan Types with Loan Policie
        Loan managed with Loan Proofs and Required Documents List.  
        different access as Loan User and Manager who can able to place create Loan Request.
        only Loan Manager can able to  Approve Loan Request. Create Disburse Accounting Journal Entry form loan
        calculate Interest Receivable from  Loan Entry. Managed Loan Installments.
        caculate Interest for loan Installment Entry. Pay loan by Installment which creates Accounting Journal Entry. Print Loan Report.
        Customer loans in Portal - My Account Page. Loan Processing Fees charges. odoo loan management. Manager can add loan proofs/required documents list for loan.Installment amount Journal Entries  Manager can Approve Loan Request
odoo loan management
vender loan management
credit loan management
vendor loan management
vendor credit loan
emi for customer
emi for supplier 
emi for vendor 
loan app
manage customer loan
manage customer credit
manage supplier loan 
loan supplier
loan vendor 
loan client

  

        
""",
    "license" : "OPL-1",
    'depends': ['sale_management','website','account','purchase','stock'],
    'data': [
            'security/loan_management_group.xml',
            'security/ir.model.access.csv',
            'views/loan_proof_view.xml',
            'views/loan_type_view.xml',
            'views/loan_policies_view.xml',
            'views/loan_request_view.xml',
            'views/loan_installment_view.xml',
            'views/partner_views.xml',
            'views/account_payment_view.xml',
            'report/report_views.xml',
            'report/print_loan_report.xml',
            'views/my_account_customer_loan_template.xml',
    ],
    'live_test_url':'https://youtu.be/1rDd1dxqemg',
    "images":['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
    'price': 45,
    'currency': "EUR",
    'category': 'Sales',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

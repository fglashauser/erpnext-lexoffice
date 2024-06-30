import frappe
#from frappe.utils.file_manager import save_file
from ..api.api import LexofficeClient
from frappe.utils.weasyprint import PrintFormatGenerator
from frappe.core.api.file import create_new_folder
from frappe.model.naming import _format_autoname
from frappe.realtime import publish_realtime
import os
from frappe import utils

def upload(doc, method):
    """
    Uploads the sales invoice to Lexoffice.
    Is called on submit of a sales invoice.
    """
    args = { 'doc': doc }
    frappe.enqueue(
        method=upload_job,
        timeout=120,
        **args
    )

def upload_job(doc):
    # Get settings
    settings = frappe.get_single('Lexoffice Settings')

    # Check if auto upload is enabled
    if not settings.au_sales_invoice:
        return
    
    # Setup api
    api = LexofficeClient(settings.get_password('api_key'))

    # ERPNext-Customer
    customer = frappe.get_doc('Customer', doc.customer)
    customer_name = customer.customer_name

    # Get or create customer
    contact_id = api.create_or_get_contact(
        roles={'customer':{}},
        company={'name': customer_name},
        person=None)
    
    # Generate PDF
    pdf_file = generate_pdf(doc)
    file_path = get_absolute_path(pdf_file.file_url) if pdf_file else None
    print(file_path)

    # Create voucher
    voucher_id = api.create_voucher(
        type='salesinvoice',
        voucher_number=doc.name,
        voucher_date=doc.posting_date,
        total_gross_amount=doc.grand_total,
        total_tax_amount=doc.total_taxes_and_charges,
        tax_type='net' if doc.total <= doc.grand_total else 'gross',
        use_collective_contact=False,
        contact_id=contact_id,
        voucher_items=[{
                'amount': doc.total,
                'taxAmount': doc.total_taxes_and_charges,
                'taxRatePercent': round(doc.total_taxes_and_charges / doc.total * 100, 1),
                'categoryId': '8f8664a1-fd86-11e1-a21f-0800200c9a66'    # Incomings
            }
        ],
        file_path=file_path)

    print(f'[Lexoffice] Created voucher: {voucher_id}')

def generate_pdf(doc):
    settings = frappe.get_single('Lexoffice Settings')
    lang = settings.lang

    if lang:
        frappe.local.lang = lang
        frappe.local.lang_full_dict = None
        frappe.local.jenv = None

    target_folder = create_folder('Sales Invoice', "Home")

    if frappe.db.get_value('Print Format', settings.print_format, 'print_format_builder_beta'):
        pdf_data = PrintFormatGenerator(settings.print_format, doc, settings.letterhead).render_pdf()
    else:
        pdf_data = frappe.get_print('Sales Invoice', doc.name, settings.print_format, as_pdf=True, letterhead=settings.letterhead)

    return save_and_attach(pdf_data, 'Sales Invoice', doc.name, target_folder)

def save_and_attach(content, to_doctype, to_name, folder, auto_name=None):
    """
    Save content to disk and create a File document.

    File document is linked to another document.
    """
    if auto_name:
        doc = frappe.get_doc(to_doctype, to_name)
        # based on type of format used set_name_form_naming_option return result.
        pdf_name = set_name_from_naming_options(auto_name, doc)
        file_name = "{pdf_name}.pdf".format(pdf_name=pdf_name.replace("/", "-"))
    else:
        file_name = "{to_name}.pdf".format(to_name=to_name.replace("/", "-"))

    file = frappe.new_doc("File")
    file.file_name = file_name
    file.content = content
    file.folder = folder
    file.is_private = 1
    file.attached_to_doctype = to_doctype
    file.attached_to_name = to_name
    file.save()
    return file
    

def set_name_from_naming_options(autoname, doc):
	"""
	Get a name based on the autoname field option
	"""
	_autoname = autoname.lower()

	if _autoname.startswith("format:"):
		return _format_autoname(autoname, doc)

	return doc.name

def create_folder(folder, parent):
	"""Make sure the folder exists and return it's name."""
	new_folder_name = "/".join([parent, folder])

	if not frappe.db.exists("File", new_folder_name):
		create_new_folder(folder, parent)

	return new_folder_name

def get_absolute_path(file_name):
	if(file_name.startswith('/files/')):
		file_path = f'{utils.get_bench_path()}/sites/{utils.get_site_base_path()[2:]}/public{file_name}'
	if(file_name.startswith('/private/')):
		file_path = f'{utils.get_bench_path()}/sites/{utils.get_site_base_path()[2:]}{file_name}'
	return file_path
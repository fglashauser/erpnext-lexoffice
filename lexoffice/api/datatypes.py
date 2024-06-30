import enum
from datetime import datetime
import uuid

class VoucherType(enum.Enum):
    SALES_INVOICE = "salesinvoice"
    SALES_CREDIT_NOTE = "salescreditnote"
    PURCHASE_INVOICE = "purchaseinvoice"
    PURCHASE_CREDIT_NOTE = "purchasecreditnote"
    INVOICE = "invoice"
    DOWN_PAYMENT_INVOICE = "downpaymentinvoice"
    CREDIT_NOTE = "creditnote"
    ORDER_CONFIRMATION = "orderconfirmation"
    QUOTATION = "quotation"
    DELIVERY_NOTE = "deliverynote"

class VoucherStatus(enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    PAIDOFF = "paidoff"
    VOIDED = "voided"
    TRANSFERRED = "transferred"
    SEPADEBIT = "sepadebit"
    OVERDUE = "overdue"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class Type(enum.Enum):
    SERVICE = "service"
    MATERIAL = "material"
    CUSTOM = "custom"
    TEXT = "text"
    UNDEFINED = "undefined"

class TaxType(enum.Enum):
    NET = "net"
    GROSS = "gross"

class Address:
    contact_id: uuid.uuid4
    name: str
    supplement: str
    street: str
    city: str
    zip: int
    countryCode: str

    def __init__(self, address: dict):
        try:
            self.contact_id = uuid.UUID(address.get('contactId'))
        except TypeError:
            self.contact_id = None
        self.name = address.get('name')
        self.supplement = address.get('supplement')
        self.street = address.get('street')
        self.city = address.get('city')
        try:
            self.zip = int(address.get('zip'))
        except (ValueError, TypeError):
            self.zip = 0
            pass
        self.countryCode = address.get('countryCode')

class UnitPrice:
    currency: str
    net_amount: float
    gross_amount: float
    tax_rate_percentage: int

    def __init__(self, unit_price: dict):
        self.currency = unit_price.get('currency')
        self.net_amount = unit_price.get('netAmount')
        self.gross_amount = unit_price.get('grossAmount')
        self.tax_rate_percentage = unit_price.get('taxRatePercentage')

class TotalPrice:
    currency: str
    total_net_amount: float
    total_gross_amount: float
    total_tax_amount: float
    total_discount_absolute: float
    total_discount_percentage: float

    def __init__(self, total_price: dict):
        self.currency = total_price.get('currency')
        self.total_net_amount = total_price.get('totalNetAmount')
        self.total_gross_amount = total_price.get('totalGrossAmount')
        self.total_tax_amount = total_price.get('totalTaxAmount')
        self.total_discount_absolute = total_price.get('totalDiscountAbsolute')
        self.total_discount_percentage = total_price.get('totalDiscountPercentage')

class LineItem:
    id: uuid.uuid4
    type: Type
    name: str
    description: str
    quantity: int
    unit_name: str
    unit_price: UnitPrice
    discount_percentage: float
    line_item_amount: float

    def __init__(self, line_item: dict):
        try:
            self.id = uuid.UUID(line_item.get('id'))
        except TypeError:
            self.id = None
        try:
            self.type = Type(line_item.get('type'))
        except ValueError:
            self.type = Type.UNDEFINED
        self.name = line_item.get('name')
        self.description = line_item.get('description')
        if self.type == Type.MATERIAL or self.type == Type.CUSTOM:
            self.quantity = line_item.get('quantity')
            self.unit_name = line_item.get('unitName')
            self.unit_price = UnitPrice(line_item.get('unitPrice'))
            self.discount_percentage = line_item.get('discountPercentage')
            self.line_item_amount = line_item.get('lineItemAmount')


class Invoice:
    id: uuid.uuid4
    organization_id: uuid.uuid4
    created_date: datetime
    updated_date: datetime
    version: int
    language: str
    archived: bool
    voucher_status: VoucherStatus
    voucher_number: str
    voucher_date: datetime
    due_date: datetime = None
    address: Address
    line_items: list[LineItem]
    total_price: TotalPrice

    def __init__(self, invoice: dict):
        try:
            self.id = uuid.UUID(invoice.get('id'))
        except TypeError:
            self.id = None
        try:
            self.organization_id = uuid.UUID(invoice.get('organizationId'))
        except TypeError:
            self.organization_id = None
        self.created_date = datetime.fromisoformat(invoice.get('createdDate'))
        self.updated_date = datetime.fromisoformat(invoice.get('updatedDate'))
        self.version = invoice.get('version')
        self.language = invoice.get('language')
        self.archived = invoice.get('archived')
        self.voucher_status = invoice.get('voucherStatus')
        self.voucher_number = invoice.get('voucherNumber')
        if 'dueDate' in invoice and invoice.get('dueDate') is not None:
            self.due_date = datetime.fromisoformat(invoice.get('dueDate'))
        self.voucher_date = datetime.fromisoformat(invoice.get('voucherDate'))
        self.address = Address(invoice.get('address'))
        self.line_items = []
        for item in invoice.get('lineItems'):
            self.line_items.append(LineItem(item))
        self.total_price = TotalPrice(invoice.get('totalPrice'))

class Voucher:
    id: uuid.uuid4
    voucher_type: VoucherType
    voucher_status: VoucherStatus
    voucher_number: str
    voucher_date: datetime
    created_date: datetime
    updated_date: datetime
    due_date: datetime = None
    contact_id: uuid.uuid4
    contact_name: str
    total_amount: float
    open_amount: float
    currency: str
    archived: bool

    def __init__(self, voucher: dict):
        try:
            self.id = uuid.UUID(voucher.get('id'))
        except TypeError:
            self.id = None
        self.voucher_type = VoucherType(voucher.get('voucherType'))
        self.voucher_status = VoucherStatus(voucher.get('voucherStatus'))
        self.voucher_number = voucher.get('voucherNumber')
        self.voucher_date = datetime.fromisoformat(voucher.get('voucherDate'))
        self.created_date = datetime.fromisoformat(voucher.get('createdDate'))
        self.updated_date = datetime.fromisoformat(voucher.get('updatedDate'))
        if 'dueDate' in voucher and voucher.get('dueDate') is not None:
            self.due_date = datetime.fromisoformat(voucher.get('dueDate'))
        self.contact_id = voucher.get('contactId')
        self.contact_name = voucher.get('contactName')
        self.total_amount = voucher.get('totalAmount')
        self.open_amount = voucher.get('openAmount')
        self.currency = voucher.get('currency')
        self.archived = voucher.get('archived')

class VoucherList:
    content: list[Voucher]
    first: bool
    last: bool
    total_pages: int
    total_elements: int
    number_of_elements: int
    size: int
    number: int
    sort: list

    def __init__(self, voucher_list: dict):
        self.content = []
        for voucher in voucher_list.get('content'):
            self.content.append(Voucher(voucher))
        self.first = voucher_list.get('first')
        self.last = voucher_list.get('last')
        self.total_pages = voucher_list.get('totalPages')
        self.total_elements = voucher_list.get('totalElements')
        self.number_of_elements = voucher_list.get('numberOfElements')
        self.size = voucher_list.get('size')
        self.number = voucher_list.get('number')
        self.sort = voucher_list.get('sort')

import uuid
import requests
from requests.exceptions import RequestException
from .datatypes import VoucherList, Invoice, VoucherType, VoucherStatus, TaxType
from .exceptions import LexofficeException
from urllib import parse
import pycurl
import json
import certifi

class LexofficeClient:

    def __init__(self, api_key):
        self.version = 1
        self.url = f'https://api.lexoffice.io/v{self.version}'
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }

    def ping(self) -> bool:
        """ Ping Lexoffice API and test the connection.

        :return: True if the /ping endpoint could be requested successfully.
        """
        response = requests.get(
            url=f'{self.url}/ping',
            headers=self.headers
        )
        if response.status_code == 200:
            print('Connected to lexoffice Public API')
            print('User:', response.json()['userEmail'])
            return True
        else:
            return False

    def get_voucherlist(self, voucher_type: VoucherType, status: list[VoucherStatus] = None, page: int = None, size: int = None) -> VoucherList:
        """ Fetch a voucherlist.

        :param voucher_type: type(s) of the vouchers to be fetched
        :param status: status(es) of the vouchers to be fetched
        :param page: Number of the page to be fetched (optional) - If not specified, the first page will be fetched
        :param size: Size of the page (max. number of vouchers to be fetched
        :return: VoucherList contatining the requested Vouchers
        """
        if status is None:
            status_str = ["any"]
        else:
            status_str = []
            for s in status:
                status_str.append(s.value)
        params = {
            'voucherType': voucher_type.value,
            'voucherStatus': ','.join(status_str),
            'page': page,
            'size': size
        }
        response = requests.get(
            url=f'{self.url}/voucherlist',
            headers=self.headers,
            params=params
        )
        content = response.json()
        if response.status_code != 200:
            if 'error' in content and 'message' in content:
                error = content['error']
                msg = content['message']
                raise RequestException(f'{error}: {msg}')
            else:
                msg = content['message']
                raise RequestException(f'Error while getting VoucherList from Lexoffice API: {msg}')
        return VoucherList(content)

    def get_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        """ Fetches an invoice with the specified ID from the /invoices endpoint.

        :param invoice_id: The UUID of the requested invoice
        :return: Invoice that was requested
        :raise RequestException if an error has occurred during the API call.
        """
        response = requests.get(
            url=f'{self.url}/invoices/{str(invoice_id)}',
            headers=self.headers
        )
        content = response.json()
        if response.status_code != 200:
            raise LexofficeException(response, 'Error while getting invoice from Lexoffice API')
        return Invoice(content)
    
    def upload_pdf(self, file_path: str) -> str:
        """ Upload a PDF file to lexoffice.

        :param file_path: Path to the PDF file to be uploaded
        :return: ID to the uploaded file
        """
        c = pycurl.Curl()
        c.setopt(c.URL, f'{self.url}/files')
        c.setopt(c.POST, 1)
        c.setopt(c.HTTPHEADER, [
            f'Authorization: Bearer {self.api_key}',
            "Accept: application/json",
            "Content-Type: multipart/form-data"
        ])

        with open(file_path, 'rb') as file:
            c.setopt(c.HTTPPOST, [
                ("file", (
                     c.FORM_FILE, file.name,
                     c.FORM_FILENAME, parse.quote(file.name)
                 )
                 ),
                ("type", "voucher")
            ])
            response = c.perform_rs()
            status_code = c.getinfo(c.RESPONSE_CODE)
            c.close()

        if status_code != 202:
            raise LexofficeException(response, 'Error while uploading PDF to Lexoffice API')

        content = json.loads(response)
        return content['id']

    def create_voucher(self,
                       type: VoucherType,
                       voucher_number: str,
                       voucher_date: str,
                       total_gross_amount: float,
                       total_tax_amount: float,
                       tax_type: TaxType,
                       use_collective_contact: bool,
                       contact_id: str,
                       voucher_items: list[dict],
                       file_path: str = None) -> str:
        # Create Voucher
        response = requests.post(
            url=f'{self.url}/vouchers',
            headers=self.headers,
            json={
                'type': type,
                'voucherNumber': voucher_number,
                'voucherDate': voucher_date,
                'totalGrossAmount': total_gross_amount,
                'totalTaxAmount': total_tax_amount,
                'taxType': tax_type,
                'useCollectiveContact': use_collective_contact,
                'contactId': contact_id,
                'voucherItems': voucher_items
            }
        )

        # Check voucher creation status
        if response.status_code != 200:
            raise LexofficeException(response, 'Error while creating voucher in Lexoffice API')
        
        # Get ID of created voucher
        content = response.json()
        id = content['id']

        # Upload PDF if file_path is given
        if file_path:
            c = pycurl.Curl()
            c.setopt(c.URL, f'{self.url}/vouchers/{id}/files')
            c.setopt(c.POST, 1)
            c.setopt(c.HTTPHEADER, [
                f'Authorization: Bearer {self.api_key}',
                "Accept: application/json",
                "Content-Type: multipart/form-data"
            ])

            c.setopt(pycurl.CAINFO, certifi.where())

            with open(file_path, 'rb') as file:
                c.setopt(c.HTTPPOST, [
                    ("file", (
                        c.FORM_FILE, file.name,
                        c.FORM_FILENAME, parse.quote(file.name)
                    ))
                ])
                response = c.perform_rs()
                status_code = c.getinfo(c.RESPONSE_CODE)
                c.close()

        # Check PDF upload status
        if status_code != 202:
            raise LexofficeException(response, 'Error while uploading PDF to Lexoffice API')

        return id
    
    def create_or_get_contact(self,
                              roles: dict, 
                              company: dict | None, 
                              person: dict | None, 
                              email: str = None, 
                              version: int = 0) -> str:
        self.headers['Content-Type'] = 'application/json'

        # Get name of contact
        if company:
            name = company['name']
        elif person:
            name = f'{person["firstName"]}{person["lastName"]}'
        else:
            raise ValueError('Either company or person must be given')

        # Get contact by name
        response = requests.get(
            url=f'{self.url}/contacts',
            headers=self.headers,
            params={
                'name': name,
                'customer': 'customer' in roles,
                'vendor': 'vendor' in roles
            }
        )
        if response.status_code != 200:
            raise LexofficeException(response, 'Error while getting contacts in Lexoffice API')
        contacts = response.json()

        # Check if contact already exists
        if len(contacts['content']) > 0:
            return contacts['content'][0]['id']
        
        # Create new contact if it does not exist
        response = requests.post(
            url=f'{self.url}/contacts',
            headers=self.headers,
            json={
                'roles': roles,
                'company': company,
                'person': person,
                'email': email,
                'version': version
            }
        )
        if response.status_code != 200:
            raise LexofficeException(response, 'Error while creating or contact in Lexoffice API')
        
        return response.json()['id']
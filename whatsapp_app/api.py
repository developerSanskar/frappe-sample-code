import datetime
import json


import frappe
from frappe.utils import now


@frappe.whitelist(allow_guest=True)
def get_lead_data(column_name='*', lead_name=None):
    if lead_name:
        return frappe.db.sql(f"select {column_name} from `tabLead` where lead_name='{lead_name}'")
    else:
        return frappe.db.sql(f"select {column_name} from `tabLead`")


@frappe.whitelist(allow_guest=True)
def set_data(first_name, mobile):
    doc = frappe.new_doc('Lead')
    doc.title = first_name
    doc.first_name = first_name
    doc.phone = mobile
    doc.insert()
    return frappe.db.get_value("Lead", {'first_name': first_name}, ['name', 'lead_name', 'first_name', 'last_name', 'phone'], as_dict=1)

# when whatsapp message sent or received set log in doctype
def data(**kwargs):
    wa_data = frappe.local.form_dict
    se_mo = wa_data["waId"][-10:]
    f_data = frappe.db.get_value("wati call message log", f"{se_mo}", "data")
    if f_data is not None:
        raw_data = json.loads(f_data)
        raw_data['data'].append(wa_data)
        data = json.dumps(raw_data)
        frappe.db.set_value('wati call message log', f'{se_mo}', {'data': f'{data}', "read": 0, "time": now()})
    else:
        data = {"data": []}
        data['data'].append(wa_data)
        data = json.dumps(data)
        doc = frappe.get_doc({"doctype": "wati call message log", "phone": f"{se_mo}", "data": f"{data}", "read": 0, "time": now()})
        doc.insert()
        frappe.db.commit()
        # frappe.db.set_value("wati call message log", f'{se_mo}', "read", 0)
    return 'success'

# add in activity after message received from wati webhooks
def comment(**kwargs):
    wa_data = frappe.local.form_dict
    se_mo = wa_data["waId"][-10:]
    message = wa_data["text"]
    l_name, lead_name = frappe.db.get_value('Lead', filters={"whatsapp_no": se_mo}, fieldname=["name", "lead_name"])
    s_name, supplier_name = frappe.db.get_value('Supplier', filters={"whatsapp_no": se_mo}, fieldname=["name", "supplier_name"])
    o_name, opportunity_name = frappe.db.get_value('Opportunity', filters={"whatsapp": se_mo}, fieldname=["name", "title"])

    content = f"<div class='card'><b style='color:orange' class='px-2 pt-2'><i class='fa fa-whatsapp' aria-hidden='true'> Whatsapp Message Received: </i></b> <span class='px-2 pb-2'>{message}</span></div>"

    if l_name:
        set_comment('Lead', l_name, lead_name, content)
        set_notification_log('Lead', l_name, lead_name, message)
    if s_name is not None:
        set_comment('Supplier', s_name, supplier_name, content)
        set_notification_log('Supplier', s_name, supplier_name, message)
    if o_name is not None:
        set_comment('Opportunity', o_name, opportunity_name, content)
        set_notification_log('Opportunity', o_name, opportunity_name, message)
    return "Success"


# set comment when new whatsapp message received
def set_comment(doctype, r_name, owner, content):
    activity = frappe.get_doc(
        {"doctype": "Comment", "comment_type": "Info",
         "reference_doctype": doctype, "reference_name": r_name,
         "content": content})
    activity.insert(ignore_permissions=True)
    frappe.db.commit()

    comment = frappe.get_last_doc('Comment')
    frappe.db.set_value('Comment', f'{comment.name}', {"owner": owner})
    frappe.db.commit()


# notification when new whatsapp message received.
def set_notification_log(doctype, doctype_name, name, content):

    name1 = frappe.db.get_value("Notification Log", filters={"document_type": doctype, "document_name": doctype_name, "type": "Alert", "read": 0}, fieldname=["name"])
    subject = frappe.db.get_value("Notification Log", filters={"document_type": doctype, "document_name": doctype_name, "type": "Alert", "read": 0}, fieldname=["subject"])
    if name1 is not None:
        frappe.db.set_value("Notification Log", name1, "subject", f"{subject}<br>{content}")
    else:
        data = frappe.get_doc({
            "doctype": "Notification Log",
            "subject": f"New <b style='color:green'><i class='fa fa-whatsapp' aria-hidden='true'></i> Whatsapp</b> Message From <b style='color:green'>{name}</b><br>{content}",
            "for_user": "nilesh@sanskartechnolab.com",
            "type": "Alert",
            "document_type": doctype,
            "document_name": doctype_name
        })
        data.insert(ignore_permissions=True)
        frappe.db.commit()


# this api call from wati webhooks
@frappe.whitelist(allow_guest=True)
def wati_webhooks():
    data1 = frappe.call(data, **frappe.form_dict)
    frappe.call(comment, **frappe.form_dict)
    # frappe.call(notification_log, **frappe.form_dict)
    return data1

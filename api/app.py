import firebase_admin.firestore
from flask import Flask, jsonify, request, render_template, make_response, redirect
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from hashlib import sha256
from google.cloud import firestore_v1
import json
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import storage
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import aggregation
from urllib.parse import urlparse
from datetime import datetime
from mailersend import emails
import random
import string


key = "mlsn.bf979daa1ed7b3207d586f0865acb90eb71a1de8adc030104328ef659686d0ff"
mailer = emails.NewEmail(key) 

mail_from = {
    "name": "Klide Services",
    "email": "services@Klide.tech",
}
reply_to = {
    "name": "Klide Services",
    "email": "services@klide.tech",
}


try:
    storage_client = storage.Client.from_service_account_json('api/firestore.json')
    cred = credentials.Certificate('api/firestore.json')
except:
    storage_client = storage.Client.from_service_account_json('firestore.json')
    cred = credentials.Certificate('firestore.json')

bucket = storage_client.bucket('klide-1bb92.appspot.com')
app = Flask(__name__)

firebase_admin.initialize_app(cred)
db = firestore.client()
receipt_ref = db.collection("receipt_preview")

def is_valid_host():
    valid_hosts = [
        "klide-merchant.vercel.app",
        "klide.tech",
        "staging.klide.tech",
        "127.0.0.1:8000",
        "klide-merchant-six.vercel.app",
        "klide-merchant-nine.vercel.app"
    ]
    return request.headers.get('Host') in valid_hosts

def is_authenticated():
    return request.cookies.get('merchant_id') is not None and request.cookies.get('device_id') is not None

def render_admin_page(template_name):
    device_type = request.cookies.get('device_type')
    if device_type == "admin":
        return render_template(template_name)
    else:
        redirect_url = "/transactions"
        return render_template('user_redirect_html.html', redirect_url=redirect_url)

########### WebPage Routeing ###############

@app.route("/")
def index():
    return render_template("public/index.html")

@app.route("/updates")
def updates():
    return render_template("public/updates.html")

@app.route("/features")
def features():
    return render_template("public/features.html")

@app.route("/timeline")
def timeline():
    return render_template("public/timeline.html")

@app.route("/dashboard")
def display_dashboard():
    return render_template("dashboard.html")

@app.route("/privacy")
def privacy():
    return render_template("public/privacy.html")

@app.route("/terms")
def terms():
    return render_template("public/terms.html")

#waitlist Signup
@app.route("/api/waitlist/add",methods=["POST"])
def waitlist_signup():
    print("Request Received")
    waitlist_db = db.collection("waitlist_db")
    data = request.json
    email = data["email"].lower()
    name = data["name"].lower()
    query = waitlist_db.where(filter=FieldFilter("uid", "==", "beta-launch-waitlist")).where(filter=FieldFilter("emails","array_contains",email)).limit(1).stream()
    for document in query :
        print("User already in waitlist")
        response = jsonify({"status": "failed", "message": "Email already in waitlist"})  
        response.set_cookie('waitlist_signup', 'true')
        return response
    try:
        mail_body = {}
        recipients = [{"name": name.title(),"email": email}]
        recipients_2 = [{"name": "Joel Klide","email": "joeljobyp@gmail.com"}]
        personalization = [{"email": email,"data": {"name": name.title()}}]
        #Sending joined waitlist message to the user 
        mailer.set_mail_from(mail_from, mail_body)
        mailer.set_mail_to(recipients, mail_body)
        mailer.set_subject("You Have Been Added To The Waitlist",mail_body)
        mailer.set_template("0p7kx4xx90849yjr", mail_body)
        mailer.set_personalization(personalization,mail_body)

        mailer.set_mail_to(recipients_2, mail_body)
        mailer.send(mail_body)
        new_entry = [{"name":name,"email":email}]
        waitlist_db.document("beta-launch-waitlist").update({"entries":firestore.ArrayUnion(new_entry)})
        new_email = [str(email)]
        waitlist_db.document("beta-launch-waitlist").update({"emails":firestore.ArrayUnion(new_email)})
        response = jsonify({"status": "success", "message": "success"})  
        response.set_cookie('waitlist_signup', 'true')
        return response
    except Exception as e:
        return {"status":"failed","message":str(e)}

#route to login #TEMP
@app.route("/")
def login():
    return redirect('/account/login')

#for checkout 
@app.route('/checkout')
def checkout():
    return render_template("/billing/checkout_page.html")

#users end live bill
@app.route('/user/new/bill')
def user_new_bill():
    return render_template('/public/new_receipt.html')

#Redirect to Admin dashboard
@app.route("/admin/dashboard")
def display_admin_page():
    if not is_valid_host() or not is_authenticated():
        return redirect("/account/login")
    return render_admin_page("/admin/dashboard.html")

@app.route("/admin/transactions")
def display_admin_transactions_page():
    if not is_valid_host() or not is_authenticated():
        return redirect("/account/login")
    return render_admin_page("/admin/transactions.html")

@app.route("/admin/devices")
def display_admin_devices_page():
    if not is_valid_host() or not is_authenticated():
        return redirect("/account/login")
    return render_admin_page("/admin/devices.html")

@app.route("/admin/customers")
def display_admin_customers_page():
    if not is_valid_host() or not is_authenticated():
        return redirect("/account/login")
    return render_admin_page("/admin/customers.html")

@app.route("/admin/products")
def display_admin_products_page():
    if not is_valid_host() or not is_authenticated():
        return redirect("/account/login")
    return render_admin_page("/admin/products.html")

@app.route("/admin/settings")
def display_admin_settings_page():
    if not is_valid_host() or not is_authenticated():
        return redirect("/account/login")
    return render_admin_page("/admin/settings.html")
            
#direct To transactions            
@app.route("/transactions", methods=['GET', 'POST'])
def display_transactions_page():
    if request.method == 'POST':
        host = urlparse(request.headers.get('Host')).hostname
        referer = urlparse(request.headers.get('Referer')).hostname
        return jsonify({'host': host, 'referer': referer})
    return render_template("/billing/transactions.html")
#@app.route("")

#login page including api for login 
@app.route('/account/login', methods=['GET', 'POST'])
def merchant_account_login():
    if request.method == 'POST':
        data = request.json
        merchant_id = sha256(data['merchant_id'].encode()).hexdigest()
        device_id = sha256(data['device_id'].encode()).hexdigest()
        password = sha256(data['password'].encode()).hexdigest()
        
        print(merchant_id, device_id, password)
        
        device_data = db.collection('merchants').document(merchant_id).collection('devices').document(device_id).get()
        device_type = device_data.to_dict().get('device_type')


        if not device_data.exists:
            return jsonify({'status': 'error', 'message': 'Invalid Merchant ID'})
        
        password_db = device_data.to_dict().get('password')
        act_device_id = device_data.to_dict().get('act_device_id')
        
        if password_db == password:
            #HOLA
            merchant_data = db.collection('merchants').document(merchant_id).get().to_dict()
            #Checking if the setup us compleated else redirectig to setup page
            if device_type == "admin":
                account_setup_status = merchant_data.get("setup")
                secret_key = merchant_data.get("secret_key")
                if account_setup_status == "False":
                    setup_link =  f"/account/setup/{merchant_id}/{secret_key}"
                    print("Returing setiup link",setup_link)
                    resp = make_response(setup_link)
                    return resp

            merchant_name = merchant_data.get("merchant_name")
            print(merchant_data)
            resp = make_response("Login successful")
            act_merchant_id = merchant_data.get("act_merchant_id")
            resp.set_cookie('merchant_id', merchant_id)
            resp.set_cookie('device_id', device_id)
            resp.set_cookie('setup_completed', 'false')
            employees=["rrt","ffgg","fgff"]
            receipt_ref = str(act_merchant_id)+"-"+act_device_id
        
            if merchant_data:
                resp.set_cookie("receipt_ref",receipt_ref)
                resp.set_cookie('merchant_name', merchant_data.get('merchant_name', ''))
                resp.set_cookie('merchant_number', merchant_data.get('merchant_number', ''))
                resp.set_cookie('merchant_email', merchant_data.get('merchant_email', ''))
                resp.set_cookie('store_name',merchant_data.get('store_name',''))
                resp.set_cookie('store_number', merchant_data.get('store_number', ''))
                resp.set_cookie('store_open_from', merchant_data.get('store_open_from', ''))
                resp.set_cookie('store_open_to', merchant_data.get('store_open_to', ''))
                resp.set_cookie('store_location', merchant_data.get('store_location', ''))
                resp.set_cookie('employees', json.dumps(merchant_data.get('employees', '')))
                resp.set_cookie('setup_completed', 'true')
                resp.set_cookie('device_type', device_type)
                resp.set_cookie('admin_name', merchant_name)
                return resp
        
        else:
            return jsonify({'status': 'error', 'message': 'Invalid Password'})
        if device_type == "admin":
            return redirect("/admin/dashboard")
        
    return render_template('/public/login.html')



########### ADMIN API's ###############
##Password Reset API
@app.route("/account/reset/password",methods=["POST"])
def reset_password():
    try:
        data = request.json
        merchant_id = data["merchant_id"]
        device_id = data["device_id"]
        new_password = sha256(data["new_password"].encode()).hexdigest()
        device_data = db.collection('merchants').document(merchant_id).collection('devices').document(device_id)
        device_data.set({"password":new_password},merge=True)
        return {"status":"success","message":"Password Reset Successful"}
    except Exception as e:
        return {"status":"failed","message":str(e)}
#@app.route()

#Get total earnings for the specified query
@app.route("/get/earnings", methods=["POST"])
def get_earnings():
    if is_valid_host():
        if not is_authenticated():
            return {"response": "Invalid Request"}
        else:
            merchant_id = request.cookies.get('merchant_id')
            data = request.json
            receipt_type = data["type"]
            if receipt_type == "today":
                sum_today_TPV = 0
                today_date = data["date"]
                collection_ref = db.collection("receipt_preview")  
                query = collection_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("date", "==", today_date))
                aggregate_query = aggregation.AggregationQuery(query)
                aggregate_query.sum("total_purchase_value", alias="sum")
                results = aggregate_query.get()
                for result in results:
                    sum_today_TPV = result[0].value
                return {"today_purchase_value": sum_today_TPV}
    else:
        return {"response": "Invalid Host"}
            

#ADMIN API to get full access to all receipts(by requested query) generated by all the devices under the merchant            
@app.route("/get/receipt/admin", methods=["POST"])
def admin_view_receipt_with_id():
    if is_valid_host():
        if not is_authenticated():
            return "Invalid Request"
        else:
            data = request.json
            receipt_type = data["type"]
            query = data["query"]
            receipt_data = []

            if receipt_type == "recent":
                merchant_id = request.cookies.get('merchant_id')
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).order_by("date", direction=firestore.Query.DESCENDING).limit(10).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            if receipt_type == "customer_number":
                merchant_id = request.cookies.get('merchant_id')
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("customer_number", "==", query)).order_by("date", direction=firestore.Query.DESCENDING).limit(10).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            if receipt_type == "date":
                merchant_id = request.cookies.get('merchant_id')
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("date", "==", query)).order_by("date", direction=firestore.Query.DESCENDING).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            if receipt_type == "receipt_id":
                merchant_id = request.cookies.get('merchant_id')
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("id", "==", query)).limit(1).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            if receipt_type == "date_range":
                merchant_id = request.cookies.get('merchant_id')
                start_date = query["start_date"]
                end_date = query["end_date"]
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("date", ">=", start_date)).where(filter=FieldFilter("date", "<=", end_date)).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            if receipt_type == "customer_number_with_date":
                merchant_id = request.cookies.get('merchant_id')
                customer_number = query["customer_number"]
                date = query["date"]
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("customer_number", "==", customer_number)).where(filter=FieldFilter("date", "==", date)).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            if receipt_type == "customer_number_with_date_range":
                merchant_id = request.cookies.get('merchant_id')
                customer_number = query["customer_number"]
                start_date = query["start_date"]
                end_date = query["end_date"]
                query_ref = receipt_ref.where(filter=FieldFilter("merchant_id", "==", merchant_id)).where(filter=FieldFilter("customer_number", "==", customer_number)).where(filter=FieldFilter("date", ">=", start_date)).where(filter=FieldFilter("date", "<=", end_date)).stream()
                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data
    else:
        return "Invalid Request"

    return "Invalid Request"
            


################ E-Bill API's #########################


# to edit/rewrite an ebill the function rewrites the blob with the received inputs from POST Request
@app.route("/edit/receipt", methods=["POST"])
def edit_receipt_with_id():
    if is_valid_host():
        if not is_authenticated():
            return "Invalid Request"
        else:
            merchant_id = request.cookies.get('merchant_id')
            device_id = request.cookies.get('device_id')

            data = request.json
            receipt_id = data["id"]
            act_merchant_id = receipt_id.split("-")[0]
            act_device_id = receipt_id.split("-")[1]
            blob = bucket.blob(f"{act_merchant_id}/{act_device_id}/receipts/{receipt_id}")

            receipt_data = data["data"]
            gst_values = set()
            for item in receipt_data:
                gst_values.add(int(item["gst"]))

            tax_components = dict()
            total_purchase_value = 0
            for gst_bracket in gst_values:
                taxable_values_SP = 0
                tax_value_SP = 0
                for item in receipt_data:
                    item_gst_bracket = int(item["gst"])
                    if item_gst_bracket == gst_bracket:
                        taxable_values_SP += float(item["product_price_excl_gst"])
                        total_purchase_value += float(item["product_price_excl_gst"]) + float(item["gst_value"])
                        tax_value_SP += float(item["gst_value"])
                tax_components.update({str(gst_bracket): {"Total_Taxable_value": taxable_values_SP, "tax_value": tax_value_SP}})

            final_receipt = {
                "id": receipt_id,
                "store_name": data["store_name"],
                "store_location": data["store_location"],
                "customer_number": data["customer_number"],
                "date": data["date"],
                "time": data["time"],
                "data": receipt_data,
                "total_purchase_value": total_purchase_value,
                "payment_methods": data["payment_methods"],
                "tax_brackets": tax_components,
                "prev_receipts": data["prev_receipts"]
            }
        
            try:
                blob.upload_from_string(str(final_receipt))
                receipt_preview = {
                    "merchant_id": merchant_id,
                    "device_id": device_id,
                    "customer_number": data["customer_number"],
                    "id": receipt_id,
                    "store_name": data["store_name"],
                    "date": data["date"],
                    "time": data["time"],
                    "total_purchase_value": total_purchase_value
                }
                db.collection("receipt_preview").document(receipt_id).set(receipt_preview)
                return {"status": "Success"}

            except Exception as e:
                print("An error occurred")
                print(final_receipt)
                print("TOTAL PURCHASE VALUE:", total_purchase_value)
                print("Error:", str(e))
    else:
        return "Invalid Request"

#to create new receipt and receipt preview with new bill contents provided by the POST request
@app.route("/receipt/create", methods=["POST"])
def Createreceipt():
    if is_valid_host():
        if not is_authenticated() or request.cookies.get('receipt_ref') is None:
            return {"status": "FAILED: Failed to create an E-bill", "reason": "Could not find Merchant ID, Device ID, or receipt_ref on the device"}
        else:
            data = request.json
            # Fetching merchant_id, device_id, receipt_ref from user device
            merchant_id = request.cookies.get('merchant_id')
            device_id = request.cookies.get('device_id')
            receipt_ref = request.cookies.get('receipt_ref')
            
            # Getting the act values from receipt ref to generate a new receipt ID
            act_merchant_id = receipt_ref.split("-")[0]
            act_device_id = receipt_ref.split("-")[1]
            
            # Reading the data of the device to get the recent receipt id and then add one
            device_doc = db.collection("merchants").document(str(merchant_id)).collection("devices").document(device_id).get().to_dict()
            recent_receipt = device_doc["recent_receipt_id"]
            
            # Adding 1 to the last receipt id to get a new receipt id
            new_receipt_id = f"{receipt_ref}-{(int(recent_receipt.split('-')[2]) + 1):06d}"

            store_name = data["store_name"]
            store_location = data["store_location"]
            store_contact = data["store_contact_info"]
            date = data["date"]
            time = firestore.SERVER_TIMESTAMP
            receipt_data = data["receipt_data"]
            receipt_total = data["receipt_total"]
            payment_methods = data["payment_summary"]
            gst_summary = data["gst_summary"]
            customer_number = data["customer_number"]
            tax_analysis_summary = data["tax_analysis_summary"]

            receipt_preview_data = {
                "id": new_receipt_id,
                "customer_number": customer_number,
                "date": date,
                "timestamp": time,
                "device_id": device_id,
                "merchant_id": merchant_id,
                "store_name": store_name,
                "total_purchase_value": receipt_total,
                "Tax_summary": tax_analysis_summary,
                "payment_methods": payment_methods
            }

            final_receipt = {
                "id": new_receipt_id,
                "store_name": store_name,
                "store_location": store_location,
                "store_contact": store_contact,
                "date": date,
                "timestamp": str(time),
                "receipt_data": receipt_data,
                "receipt_total": receipt_total,
                "tax_analysis_summary": tax_analysis_summary,
                "gst_summary": gst_summary,
                "payment_methods": payment_methods,
                "customer_number": customer_number
            }

            blob = bucket.blob(f"{act_merchant_id}/{act_device_id}/receipts/{new_receipt_id}")
            
            try:
                blob.upload_from_string(json.dumps(final_receipt, ensure_ascii=False))
                db.collection("receipt_preview").document(new_receipt_id).set(receipt_preview_data)
                db.collection("merchants").document(merchant_id).collection("devices").document(device_id).set({"recent_receipt_id": new_receipt_id}, merge=True)
                return {"status": "Success"}
            except Exception as e:
                print("An error occurred:", str(e))
                return {"status": "FAILED: Failed to create an E-bill"}
    else:
        return {"status": "FAILED: Invalid Host"}

'''
@app.route("/receipt/create",methods=["POST"])
def Createreceipt():
    data = request.json
    merchant_id = data["merchantid"]
    device_id = data["deviceid"]
    device_doc = db.collection("merchants").document(str(merchant_id)).collection("devices").document(device_id).get().to_dict()
    recent_receipt = device_doc["recent_receipt_id"]
    new_receipt_id = f"{data['receipt_ref']}-{(int(recent_receipt.split('-')[2])+1):06d}"

    act_merchant_id = data["receipt_ref"].split("-")[0]
    act_device_id = data["receipt_ref"].split("-")[1]

    blob = bucket.blob(f"{act_merchant_id}/{act_device_id}/receipts/{new_receipt_id}")

    print(f"NEW RECEIPT ID : {new_receipt_id}")
    receipt_data = data["data"]
    gst_values = set()
    for item in receipt_data:
        gst_values.add(int(item["gst"]))

    tax_components=dict()
    total_purchase_value = 0
    for gst_bracket in gst_values:
        taxable_values_SP = 0
        tax_value_SP = 0
        for item in receipt_data:
            item_gst_bracket = int(item["gst"])
            if item_gst_bracket == gst_bracket:
                taxable_values_SP += float(item["product_price_excl_gst"])
                total_purchase_value += float(item["product_price_excl_gst"])+float(item["gst_value"])
                tax_value_SP += float(item["gst_value"])
        tax_components.update({str(gst_bracket):{"Total_Taxable_value":taxable_values_SP,"tax_value":tax_value_SP}})

    final_receipt = {"id":new_receipt_id,"store_name":data["store_name"],"store_location":data["store_location"],"customer_number":data["customer_number"],"date":data["date"],"time":data["time"],"data":receipt_data,"total_purchase_value":total_purchase_value,"payment_methods":data["payment_methods"],"tax_brackets":tax_components}
    try:
        blob.upload_from_string(str(final_receipt))
        db.collection("merchants").document(merchant_id).collection("devices").document(device_id).set({"recent_receipt_id":new_receipt_id},merge=True)
        receipt_preview = {"merchant_id":merchant_id,"device_id":device_id,"customer_number":data["customer_number"],"id":new_receipt_id,"store_name":data["store_name"],"date":data["date"],"time":data["time"],"total_purchase_value":total_purchase_value}
        db.collection("receipt_preview").document(new_receipt_id).set(receipt_preview)

    except:
        print("An error occurred")
        return {"status":"FAILED : Failed to create a E-bill"}
    
    print("Final Receipt" ,final_receipt)
    print("TOTLA PURCAHSE VALUE : ",total_purchase_value)
    return {"status":"Success"}
    '''        
        


################################### Cashier/device API's ###########################################



#TO GET ALL THE receipts generated by a particular device(using query provided by device)
@app.route("/get/receipts/cashier", methods=["POST"])
def get_receipts_cashier():
    if is_valid_host():
        if not is_authenticated():
            return "Invalid Request"
        else:
            data = request.json
            receipt_data = []
            type = data["type"]
            query = data["query"]

            merchant_id = request.cookies.get('merchant_id')
            device_id = request.cookies.get('device_id')

            if type == "recent":
                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("device_id", "==", device_id)
                ).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            elif type == "customer_number":
                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("customer_number", "==", query)
                ).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            elif type == "date":
                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("device_id", "==", device_id)
                ).where(
                    filter=FieldFilter("date", "==", query)
                ).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            elif type == "receipt_id":
                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("id", "==", query)
                ).limit(1).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            elif type == "date_range":
                start_date = query["start_date"]
                start_date_timestamp = datetime(
                    int(start_date.split("-")[2]),
                    int(start_date.split("-")[1]),
                    int(start_date.split("-")[0])
                )

                end_date = query["end_date"]
                end_date_timestamp = datetime(
                    int(end_date.split("-")[2]),
                    int(end_date.split("-")[1]),
                    int(end_date.split("-")[0])
                )

                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("device_id", "==", device_id)
                ).where(
                    filter=FieldFilter("timestamp", ">=", start_date_timestamp)
                ).where(
                    filter=FieldFilter("timestamp", "<=", end_date_timestamp)
                ).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            elif type == "customer_number_with_date":
                customer_number = query["customer_number"]
                date = query["date"]

                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("customer_number", "==", customer_number)
                ).where(
                    filter=FieldFilter("date", "==", date)
                ).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

            elif type == "customer_number_with_date_range":
                customer_number = query["customer_number"]

                start_date = query["start_date"]
                start_date_timestamp = datetime(
                    int(start_date.split("-")[2]),
                    int(start_date.split("-")[1]),
                    int(start_date.split("-")[0])
                )

                end_date = query["end_date"]
                end_date_timestamp = datetime(
                    int(end_date.split("-")[2]),
                    int(end_date.split("-")[1]),
                    int(end_date.split("-")[0])
                )

                query_ref = receipt_ref.where(
                    filter=FieldFilter("merchant_id", "==", merchant_id)
                ).where(
                    filter=FieldFilter("customer_number", "==", customer_number)
                ).where(
                    filter=FieldFilter("timestamp", ">=", start_date_timestamp)
                ).where(
                    filter=FieldFilter("timestamp", "<=", end_date_timestamp)
                ).stream()

                for doc in query_ref:
                    receipt_data.append(doc.to_dict())
                return receipt_data

    else:
        return 'Invalid Request'
    
    return 'Invalid Request'


################# TEMPS #############
@app.route("/transactions/receipt/<receipt_id>")
def get_receipt_data(receipt_id):
    act_merchant_id = receipt_id.split("-")[0]
    act_device_id = receipt_id.split("-")[1]
    if request.cookies.get('merchant_id') == sha256(act_merchant_id.encode()).hexdigest() and request.cookies.get('device_id') == sha256(act_device_id.encode()).hexdigest():
        blob = bucket.blob(f"{act_merchant_id}/{act_device_id}/receipts/{receipt_id}")
        receipt_data = blob.download_as_string().decode('utf-8')
        receipt_data = json.loads(receipt_data)
        return render_template("/billing/receipt.html", receipt_data=receipt_data)
    else:
        return "Invalid Request"
    
@app.route("/merchant/new/bill")
def credirect_to_test_new_receipt():
    return render_template("/billing/checkout_page.html")
    
    







    
######################################## USER/SETUP/OTHERS ##############################
########### TO SETUP NEW MERCHANT(create a new account for the merchant)  ####################
@app.route('/api/v1/create/new/merchant/account', methods=['POST'])
def createNewMerchantAccount():
    data = request.json
    merchant_name = data['merchant_name']
    merchant_email = data["merchant_email"]
    #Fetching the latest Merchant Id created 
    try:
        latest_merchant_id_collection = db.collection("merchants").order_by("act_merchant_id",direction=firestore.Query.DESCENDING).limit(1).stream()
        for doc in latest_merchant_id_collection:
            document = doc.to_dict()
            latest_merchant_id = document["act_merchant_id"]
        new_merchant_id = int(latest_merchant_id)+1
        #Generating a new Merchant Secret key
        characters = string.ascii_letters + string.digits 
        secret_key = ''.join(random.choice(characters) for i in range(10))
        print("Random String",secret_key)

        new_merchant_data = {"merchant_name":merchant_name,"merchant_email":merchant_email,"act_merchant_id":int(new_merchant_id),"secret_key":secret_key,"setup":"False","devices":2}
        encrypted_merchant_id = sha256(str(new_merchant_id).encode()).hexdigest()

        db.collection("merchants").document(encrypted_merchant_id).set(new_merchant_data, merge=True)
        #creating an Admin account for the merchant
        random_key = str(random.randint(100000, 999999))
        recent_receipt_ref_admin = str(random.randint(1000, 9999))
        act_admin_account_id = "admin-"+str(random_key)
        encrypted_admin_account_id = sha256(act_admin_account_id.encode()).hexdigest()
        act_password = str(random.randint(100000, 999999))
        password = sha256(act_password.encode()).hexdigest()
        recent_receipt_id = str(new_merchant_data['act_merchant_id'])+"-"+recent_receipt_ref_admin+"-"+"000000"
        #HOLA2
        #initalising the barcodes collection for the merchant
        barcode_db = db.collection("merchants").document(encrypted_merchant_id).collection("barcodes").document("barcodes")
        initial_barcode_data = str({"id": "0000001", "name": "Test Sample Item", "price": "2", "HSN": "1525343423222", "category": "Chips", "taxes": {"IGST": "18", "SGST": "18", "cess": "10"}}).replace("'",'"')
        data = [initial_barcode_data]
        barcode_db.set({"barcodes":data})
        db.collection("merchants").document(encrypted_merchant_id).collection("devices").document(encrypted_admin_account_id).set({"password": password,"act_device_id":act_admin_account_id,"recent_receipt_id":recent_receipt_id,"device_type":"admin","setup_status":"False"})
        
    except Exception as e:
        return {"status":"failed","message":str(e),"error_cause":"Failed to create new merchant account"}
    #send setup link to the merchant email through mail
    setup_link = f"http://klide.tech/account/setup/{encrypted_merchant_id}/{secret_key}"
    mail_body = {}
    merchant_email = document["merchant_email"]
    merchant_name = document["merchant_name"]
    #print("DOCUMENT DATA",document)
    try:
        recipients = [{"name": merchant_name.title(),"email":merchant_email }]
        recipients_2 = [{"name": "Joel Klide","email": "joeljobyp@gmail.com"}]
        personalization = [{"email": merchant_email,"data": {"name": merchant_name.title(),"setup_link":setup_link}}]
        #Sending joined waitlist message to the user 
        mailer.set_mail_from(mail_from, mail_body)
        mailer.set_mail_to(recipients, mail_body)
        mailer.set_subject("Your Account Is Ready For Setup",mail_body)
        mailer.set_template("pq3enl6vee7g2vwr", mail_body)
        mailer.set_personalization(personalization,mail_body)
        mailer.set_mail_to(recipients_2, mail_body)
        mailer.send(mail_body)
        print("ADMIN PASSWORD : ",act_password)
    except Exception as e:
        return {"status":"failed","message":str(e),"error_cause":"Failed to send mail"}


    return {"status":"success"}


#Account Setup Page
@app.route('/account/setup/<merchant_id>/<secret_key>')
def setup_merchant_account(merchant_id,secret_key):
    try:
        merchant_data = db.collection("merchants").document(merchant_id).get().to_dict()
        merchant_account_setup_status = merchant_data["setup"]
        if merchant_account_setup_status == "False" and merchant_data["secret_key"] == secret_key:
            allowed_devices_count = merchant_data["devices"]
            return render_template('/account/new.html', devices = allowed_devices_count, merchant_name=str(merchant_data["merchant_name"]),merchant_email=str(merchant_data["merchant_email"]),merchant_id=merchant_id)
        else:
            return render_template("user_redirect_html.html",redirect_url="/account/login")
    except Exception as e:
        print("An error occurred",str(e))
        return render_template("user_redirect_html.html",redirect_url="/account/login")




#Fields to be manually added to start setting up accounts 
#act_merchant_id -- inside merchant id document
#number of devices 
#admin account inside devices document 
#things to put in the admin account -- act_device_id,password,device_type

@app.route('/account/new', methods=['GET', 'POST'])
def account_new():
    try:
        cookies = request.cookies
        data = request.json
        merchant_id = data['merchant_id']
        #merchant_id = cookies.get('merchant_id')
        print("Merchant ID",merchant_id)
        merchant_details = db.collection("merchants").document(merchant_id).get()
        merchant_details = merchant_details.to_dict()
        if request.method == 'POST':
            data = request.json
            print(data)
            merchant_id = data['merchant_id']
            merchant_name = data['merchant_name']
            merchant_number = data['merchant_number']
            merchant_email = data['merchant_email']
            store_name = data['store_name']
            store_number = data['store_number']
            open_from = data['open_from']
            open_to = data['open_to']
            location = data['location']
            devices = list(data['devices'])
            employees = data['employees']
            
            print(merchant_id, merchant_name, merchant_number, merchant_email, store_name, store_number, open_from, open_to, location, devices, employees)
            print("in devices",type(devices),devices[0])
            for device_no in range(0,len(devices)):
                device = devices[device_no]
                device_id = sha256(device['device_id'].encode()).hexdigest()
                password = sha256(device['password'].encode()).hexdigest()
                print("Device ID",merchant_details)
                recent_receipt_id = str(merchant_details["act_merchant_id"])+"-"+device['device_id']+"-"+"000000"
                print("Device Added")
                db.collection("merchants").document(merchant_id).collection("devices").document(device_id).set({"password": password,"act_device_id":device['device_id'],"recent_receipt_id":recent_receipt_id,"device_type":"non_admin"})
                



            merchant_info = {
                "merchant_number":merchant_number,
                "store_name":store_name,
                "store_number":store_number,
                "store_open_from":open_from,
                "store_open_to":open_to,
                "store_location":location,
                "employees":employees,
                "setup":"True"
            }
            
            db.collection("merchants").document(merchant_id).set(merchant_info, merge=True)
            devices = int(merchant_details['devices'])
            return {"status":"success","message":"Account Setup Successful"}
    except Exception as e:
        print("An error occurred",str(e))
        return {"status":"failed","message":str(e)}


@app.route('/view/<receipt_id>')
def view(receipt_id):
    act_merchant_id = receipt_id.split("-")[0]
    act_device_id = receipt_id.split("-")[1]
    if request.cookies.get('merchant_id') == sha256(act_merchant_id.encode()).hexdigest() and request.cookies.get('device_id') == sha256(act_device_id.encode()).hexdigest():
        blob = bucket.blob(f"{act_merchant_id}/{act_device_id}/receipts/{receipt_id}")
        receipt_data = blob.download_as_string().decode('utf-8')
        data = json.dumps(receipt_data,ensure_ascii=False)
        print("retunred",receipt_data)
        return render_template('/public/view_receipt.html',receipt_data=receipt_data)
    else:
        return "Invalid Request"
    



############################### Barcode DataBase Api's #############################

#TO get all the Barcode data
@app.route("/get/barcodedatabase", methods=["POST"])
def get_barcodedata():
    if is_valid_host():
        data = request.json
        merchantid = data.get("merchantid")

        if not merchantid:
            return {"message": "ERROR: Merchant ID is required"}

        doc = db.collection("merchants").document(str(merchantid)).collection("barcodes").document("barcodes").get()

        if doc.exists:
            barcode_data = doc.to_dict()
            print("Successfully retrieved Barcode Data:", barcode_data)
            return barcode_data.get("barcodes", [])
        else:
            return {"message": "ERROR: Invalid Request; the specified document does not exist"}
    else:
        return {"message": "Request Source Unspecified"}
    
#to add new Item to barcode database
@app.route("/create/barcodedatabase/item", methods=["POST"])
def create_new_barcodedatabase_item():
    if is_valid_host():
        if not is_authenticated():
            return {"message": "Invalid Request"}
        else:
            data = request.json
            merchant_id = request.cookies.get('merchant_id')
            device_type = request.cookies.get("device_type")
            new_product_data = [data["product_data"]]

            if device_type == "admin":
                db_ref = db.collection("merchants").document(str(merchant_id)).collection("barcodes").document("barcodes")
                
                try:
                    db_ref.update({"barcodes": firestore.ArrayUnion(new_product_data)})
                    return {"message": "success"}
                except Exception as e:
                    print("An error occurred:", str(e))
                    return {"message": "Failed to update barcode database"}
            else:
                return {"message": "Unauthorized access"}
    else:
        return {"message": "Invalid Host"}
            
@app.route("/test",methods=["GET"])
def apply():
    k = "/account/login"
    return render_template('user_redirect_html.html',redirect_url=k)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
